import { applySettings, clearSettings } from "./apply";
import { removeDaltonizeFilters } from "./daltonize";
import { createMuteMediaController, type MuteMediaController } from "./muteMedia";
import {
  DEFAULT_SETTINGS,
  PROFILE_PATCHES,
  migrate,
  sanitiseSettings,
  type A11ySettings,
  type ProfileId,
  type SettableKey,
} from "./settings";
import { SpeechController } from "./speech";
import { createLocalStorageAdapter, type RemoteSyncAdapter, type StorageAdapter } from "./storage";

export type Announce = (message: string, politeness?: "polite" | "assertive") => void;

export interface A11yTelemetryEvent {
  type: "set" | "patch" | "applyProfile" | "clearProfile" | "resetKeys" | "reset";
  key?: SettableKey;
  keys?: readonly SettableKey[];
  profile?: ProfileId;
}

export interface A11yEngineOptions {
  root?: HTMLElement;
  storage?: StorageAdapter;
  remote?: RemoteSyncAdapter | null;
  announce?: Announce;
  telemetry?: (event: A11yTelemetryEvent) => void;
  persistDebounceMs?: number;
}

const DEFAULT_PERSIST_DEBOUNCE_MS = 400;

function cloneSettings(settings: Readonly<A11ySettings>): A11ySettings {
  return {
    ...settings,
    customColors: settings.customColors ? { ...settings.customColors } : null,
    highlight: { ...settings.highlight },
    tts: { ...settings.tts },
    toolbar: { ...settings.toolbar },
  };
}

function mergeSettings(base: Readonly<A11ySettings>, patch: Partial<A11ySettings>): A11ySettings {
  const defined = Object.fromEntries(
    Object.entries(patch).filter(([, value]) => value !== undefined),
  ) as Partial<A11ySettings>;
  return cloneSettings({ ...base, ...defined });
}

function revertKeys(settings: Readonly<A11ySettings>, keys: readonly (keyof A11ySettings)[]): A11ySettings {
  const defaults = cloneSettings(DEFAULT_SETTINGS);
  const reverted = Object.fromEntries(keys.map((key) => [key, defaults[key]])) as Partial<A11ySettings>;
  return mergeSettings(settings, reverted);
}

export class A11yEngine {
  readonly speech: SpeechController;
  #settings: A11ySettings = cloneSettings(DEFAULT_SETTINGS);
  readonly #listeners = new Set<(settings: Readonly<A11ySettings>) => void>();
  readonly #root: HTMLElement;
  readonly #storage: StorageAdapter;
  readonly #remote: RemoteSyncAdapter | null;
  readonly #announce: Announce | null;
  readonly #telemetry: ((event: A11yTelemetryEvent) => void) | null;
  readonly #persistDebounceMs: number;
  readonly #muteMedia: MuteMediaController;
  #persistTimer: ReturnType<typeof setTimeout> | null = null;
  #profileBase: A11ySettings | null = null;

  constructor(options: A11yEngineOptions = {}) {
    this.#root = options.root ?? document.documentElement;
    this.#storage = options.storage ?? createLocalStorageAdapter();
    this.#remote = options.remote ?? null;
    this.#announce = options.announce ?? null;
    this.#telemetry = options.telemetry ?? null;
    this.#persistDebounceMs = options.persistDebounceMs ?? DEFAULT_PERSIST_DEBOUNCE_MS;
    this.#muteMedia = createMuteMediaController(this.#root.ownerDocument.body);
    this.speech = new SpeechController({
      getSettings: () => this.#settings.tts,
      document: this.#root.ownerDocument,
    });
  }

  get settings(): Readonly<A11ySettings> {
    return this.#settings;
  }

  async init(): Promise<void> {
    this.speech.connect();
    let stored: unknown = null;
    try {
      stored = await (this.#remote ?? this.#storage).read();
    } catch {
      stored = null;
    }

    if (stored !== null && typeof stored === "object") {
      const migrated = migrate(stored as Record<string, unknown>);
      if (migrated) this.#settings = sanitiseSettings(migrated);
    }

    this.#applyAndNotify();
  }

  set<K extends SettableKey>(key: K, value: A11ySettings[K]): void {
    this.#profileBase = null;
    this.#telemetry?.({ type: "set", key });
    this.#commit(mergeSettings(this.#settings, { [key]: value, profile: null } as Partial<A11ySettings>));
  }

  patch(partial: Partial<Pick<A11ySettings, SettableKey>>): void {
    this.#profileBase = null;
    this.#telemetry?.({ type: "patch" });
    this.#commit(mergeSettings(this.#settings, { ...partial, profile: null }));
  }

  applyProfile(id: ProfileId): void {
    if (this.#settings.profile === id) {
      this.clearProfile();
      return;
    }
    const base = this.#profileBase ?? { ...cloneSettings(this.#settings), profile: null };
    this.#profileBase = base;
    this.#telemetry?.({ type: "applyProfile", profile: id });
    this.#commit(mergeSettings(base, { ...PROFILE_PATCHES[id], profile: id }));
  }

  clearProfile(): void {
    const active = this.#settings.profile;
    if (!active) return;
    const next = this.#profileBase
      ? cloneSettings(this.#profileBase)
      : revertKeys(this.#settings, Object.keys(PROFILE_PATCHES[active]) as (keyof A11ySettings)[]);
    this.#profileBase = null;
    this.#telemetry?.({ type: "clearProfile", profile: active });
    this.#commit({ ...next, profile: null });
  }

  resetKeys(keys: readonly SettableKey[]): void {
    this.#profileBase = null;
    this.#telemetry?.({ type: "resetKeys", keys });
    this.#commit({ ...revertKeys(this.#settings, keys), profile: null });
  }

  reset(): void {
    this.#profileBase = null;
    this.#cancelPersist();
    this.#settings = cloneSettings(DEFAULT_SETTINGS);
    this.#telemetry?.({ type: "reset" });
    this.#applyAndNotify();
    void this.#storage.clear();
    void this.#remote?.clear();
  }

  subscribe(listener: (settings: Readonly<A11ySettings>) => void): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  announce(message: string, politeness: "polite" | "assertive" = "polite"): void {
    this.#announce?.(message, politeness);
  }

  destroy(): void {
    this.#cancelPersist();
    this.#muteMedia.stop();
    this.speech.disconnect();
    clearSettings({ root: this.#root });
    removeDaltonizeFilters(this.#root.ownerDocument.body);
  }

  #commit(next: A11ySettings): void {
    this.#settings = next;
    this.#applyAndNotify();
    this.#schedulePersist();
  }

  #applyAndNotify(): void {
    applySettings(this.#settings, { root: this.#root });
    if (this.#settings.muteMedia) this.#muteMedia.start();
    else this.#muteMedia.stop();
    this.speech.setReadOnInteraction(this.#settings.tts.enabled);
    for (const listener of this.#listeners) listener(this.#settings);
  }

  #cancelPersist(): void {
    if (this.#persistTimer) clearTimeout(this.#persistTimer);
    this.#persistTimer = null;
  }

  #schedulePersist(): void {
    this.#cancelPersist();
    const snapshot = this.#settings;
    this.#persistTimer = setTimeout(() => {
      this.#persistTimer = null;
      void this.#storage.write(snapshot);
      void this.#remote?.write(snapshot);
    }, this.#persistDebounceMs);
  }
}
