declare const SETTINGS_VERSION = 1;
type ThemeId = "default" | "contrast-dark" | "contrast-light" | "monochrome" | "saturation-low" | "saturation-high" | "protanopia" | "deuteranopia" | "tritanopia" | "invert";
declare const THEME_IDS: readonly ThemeId[];
type ProfileId = "low-vision" | "blind-screen-reader" | "motor-impairment" | "protanopia" | "deuteranopia" | "tritanopia" | "epilepsy-safe" | "adhd-focus" | "dyslexia" | "older-users";
interface CustomColors {
    background?: string;
    heading?: string;
    text?: string;
    link?: string;
}
interface HighlightSettings {
    links: boolean;
    headings: boolean;
    focus: boolean;
    hover: boolean;
}
interface TtsSettings {
    enabled: boolean;
    rate: number;
    pitch: number;
    voiceURI: string | null;
    highlight: boolean;
}
interface ToolbarSettings {
    position: "left" | "right";
    hidden: boolean;
}
interface A11ySettings {
    version: number;
    profile: ProfileId | null;
    theme: ThemeId;
    customColors: CustomColors | null;
    fontScale: number;
    lineHeight: number;
    letterSpacing: number;
    wordSpacing: number;
    fontFamily: "default" | "readable" | "dyslexic";
    contentWidth: "default" | "narrow";
    cursor: "default" | "large-white" | "large-black";
    highlight: HighlightSettings;
    motion: "default" | "reduced" | "off";
    muteMedia: boolean;
    enlargeTargets: boolean;
    readingGuide: "off" | "ruler" | "mask";
    readFocus: boolean;
    magnifier: "off" | "text-hover" | "lens";
    tts: TtsSettings;
    voiceCommands: boolean;
    virtualKeyboard: boolean;
    toolbar: ToolbarSettings;
}
type SettableKey = Exclude<keyof A11ySettings, "version" | "profile">;
declare const DEFAULT_SETTINGS: Readonly<A11ySettings>;
declare const SETTING_LIMITS: Readonly<{
    fontScale: {
        min: number;
        max: number;
    };
    lineHeight: {
        min: number;
        max: number;
    };
    letterSpacing: {
        min: number;
        max: number;
    };
    wordSpacing: {
        min: number;
        max: number;
    };
    rate: {
        min: number;
        max: number;
    };
    pitch: {
        min: number;
        max: number;
    };
}>;
declare const PROFILE_PATCHES: Readonly<Record<ProfileId, Partial<A11ySettings>>>;
declare const PROFILE_IDS: ProfileId[];
declare function migrate(stored: Record<string, unknown>): Record<string, unknown> | null;
declare function sanitiseSettings(input: unknown): A11ySettings;

interface StorageAdapter {
    read(): Promise<Partial<A11ySettings> | null>;
    write(settings: A11ySettings): Promise<void>;
    clear(): Promise<void>;
}
type RemoteSyncAdapter = StorageAdapter;
declare function createLocalStorageAdapter(key?: string): StorageAdapter;
declare function createNoopStorageAdapter(): StorageAdapter;

type SpeechStatus = "idle" | "speaking" | "paused";
type SpeechSource = "page" | "selection" | "element" | "focus" | "text";
interface SpeechVoice {
    uri: string;
    name: string;
    lang: string;
    isDefault: boolean;
}
interface SpeechState {
    supported: boolean;
    highlightSupported: boolean;
    status: SpeechStatus;
    source: SpeechSource | null;
    voices: readonly SpeechVoice[];
    hasSelection: boolean;
}
interface TextSlice {
    node: Text;
    start: number;
    end: number;
    nodeOffset: number;
}
interface TextBlock {
    element: Element;
    text: string;
    slices: TextSlice[];
}
interface SpeechChunk {
    block: TextBlock;
    start: number;
    end: number;
    text: string;
}
declare const READING_HIGHLIGHT = "unijobs-a11y-reading";
declare const WORD_HIGHLIGHT = "unijobs-a11y-word";
declare function collectBlocks(root: Element): TextBlock[];
declare function blockFromRange(range: Range): TextBlock | null;
declare function rangeFor(block: TextBlock, start: number, end: number): Range | null;
declare function chunkBlocks(blocks: readonly TextBlock[], locale: string): SpeechChunk[];
declare function describeControl(el: HTMLElement): string;
interface SpeechControllerOptions {
    getSettings: () => Readonly<TtsSettings>;
    document?: Document;
}
type Listener = () => void;
declare class SpeechController {
    #private;
    constructor({ getSettings, document: doc }: SpeechControllerOptions);
    get state(): SpeechState;
    subscribe(listener: Listener): () => void;
    connect(): void;
    disconnect(): void;
    setReadOnInteraction(enabled: boolean): void;
    speakPage(root?: Element | null): boolean;
    speakElement(element: Element, source?: SpeechSource): boolean;
    speakSelection(): boolean;
    speakText(text: string, source?: SpeechSource): boolean;
    pause(): void;
    resume(): void;
    stop(): void;
}

type Announce = (message: string, politeness?: "polite" | "assertive") => void;
interface A11yTelemetryEvent {
    type: "set" | "patch" | "applyProfile" | "clearProfile" | "resetKeys" | "reset";
    key?: SettableKey;
    keys?: readonly SettableKey[];
    profile?: ProfileId;
}
interface A11yEngineOptions {
    root?: HTMLElement;
    storage?: StorageAdapter;
    remote?: RemoteSyncAdapter | null;
    announce?: Announce;
    telemetry?: (event: A11yTelemetryEvent) => void;
    persistDebounceMs?: number;
}
declare class A11yEngine {
    #private;
    readonly speech: SpeechController;
    constructor(options?: A11yEngineOptions);
    get settings(): Readonly<A11ySettings>;
    init(): Promise<void>;
    set<K extends SettableKey>(key: K, value: A11ySettings[K]): void;
    patch(partial: Partial<Pick<A11ySettings, SettableKey>>): void;
    applyProfile(id: ProfileId): void;
    clearProfile(): void;
    resetKeys(keys: readonly SettableKey[]): void;
    reset(): void;
    subscribe(listener: (settings: Readonly<A11ySettings>) => void): () => void;
    announce(message: string, politeness?: "polite" | "assertive"): void;
    destroy(): void;
}

export { type A11yEngineOptions as A, describeControl as B, type CustomColors as C, DEFAULT_SETTINGS as D, migrate as E, rangeFor as F, sanitiseSettings as G, type HighlightSettings as H, type ProfileId as P, READING_HIGHLIGHT as R, type SettableKey as S, THEME_IDS as T, WORD_HIGHLIGHT as W, A11yEngine as a, type A11ySettings as b, type SpeechState as c, type A11yTelemetryEvent as d, type Announce as e, PROFILE_IDS as f, PROFILE_PATCHES as g, type RemoteSyncAdapter as h, SETTINGS_VERSION as i, SETTING_LIMITS as j, type SpeechChunk as k, SpeechController as l, type SpeechControllerOptions as m, type SpeechSource as n, type SpeechStatus as o, type SpeechVoice as p, type StorageAdapter as q, type TextBlock as r, type ThemeId as s, type ToolbarSettings as t, type TtsSettings as u, blockFromRange as v, chunkBlocks as w, collectBlocks as x, createLocalStorageAdapter as y, createNoopStorageAdapter as z };
