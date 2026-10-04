export const SETTINGS_VERSION = 1;

export type ThemeId =
  | "default"
  | "contrast-dark"
  | "contrast-light"
  | "monochrome"
  | "saturation-low"
  | "saturation-high"
  | "protanopia"
  | "deuteranopia"
  | "tritanopia"
  | "invert";

export const THEME_IDS: readonly ThemeId[] = [
  "default",
  "contrast-dark",
  "contrast-light",
  "monochrome",
  "saturation-low",
  "saturation-high",
  "protanopia",
  "deuteranopia",
  "tritanopia",
  "invert",
];

export type ProfileId =
  | "low-vision"
  | "blind-screen-reader"
  | "motor-impairment"
  | "protanopia"
  | "deuteranopia"
  | "tritanopia"
  | "epilepsy-safe"
  | "adhd-focus"
  | "dyslexia"
  | "older-users";

export interface CustomColors {
  background?: string;
  heading?: string;
  text?: string;
  link?: string;
}

export interface HighlightSettings {
  links: boolean;
  headings: boolean;
  focus: boolean;
  hover: boolean;
}

export interface TtsSettings {
  enabled: boolean;
  rate: number;
  pitch: number;
  voiceURI: string | null;
  highlight: boolean;
}

export interface ToolbarSettings {
  position: "left" | "right";
  hidden: boolean;
}

export interface A11ySettings {
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

export type SettableKey = Exclude<keyof A11ySettings, "version" | "profile">;

export const DEFAULT_SETTINGS: Readonly<A11ySettings> = Object.freeze({
  version: SETTINGS_VERSION,
  profile: null,
  theme: "default",
  customColors: null,
  fontScale: 1,
  lineHeight: 1.5,
  letterSpacing: 0,
  wordSpacing: 0,
  fontFamily: "default",
  contentWidth: "default",
  cursor: "default",
  highlight: Object.freeze({ links: false, headings: false, focus: false, hover: false }),
  motion: "default",
  muteMedia: false,
  enlargeTargets: false,
  readingGuide: "off",
  readFocus: false,
  magnifier: "off",
  tts: Object.freeze({ enabled: false, rate: 1, pitch: 1, voiceURI: null, highlight: true }),
  voiceCommands: false,
  virtualKeyboard: false,
  toolbar: Object.freeze({ position: "right", hidden: false }),
});

export const SETTING_LIMITS = Object.freeze({
  fontScale: { min: 1, max: 2 },
  lineHeight: { min: 1.5, max: 2.5 },
  letterSpacing: { min: 0, max: 0.3 },
  wordSpacing: { min: 0, max: 0.6 },
  rate: { min: 0.5, max: 2 },
  pitch: { min: 0, max: 2 },
});

const LINKS_ONLY: HighlightSettings = { links: true, headings: false, focus: false, hover: false };

export const PROFILE_PATCHES: Readonly<Record<ProfileId, Partial<A11ySettings>>> = Object.freeze({
  "low-vision": {
    fontScale: 1.5,
    lineHeight: 1.8,
    theme: "contrast-dark",
    highlight: { ...LINKS_ONLY, focus: true },
    cursor: "large-white",
    enlargeTargets: true,
  },
  "blind-screen-reader": { motion: "off", muteMedia: true },
  "motor-impairment": { enlargeTargets: true, cursor: "large-black", highlight: { ...LINKS_ONLY, focus: true, links: false } },
  protanopia: { theme: "protanopia", highlight: LINKS_ONLY },
  deuteranopia: { theme: "deuteranopia", highlight: LINKS_ONLY },
  tritanopia: { theme: "tritanopia", highlight: LINKS_ONLY },
  "epilepsy-safe": { motion: "off", theme: "saturation-low", muteMedia: true },
  "adhd-focus": { motion: "reduced", contentWidth: "narrow", highlight: { ...LINKS_ONLY, links: false, focus: true } },
  dyslexia: {
    fontFamily: "dyslexic",
    letterSpacing: 0.08,
    wordSpacing: 0.16,
    lineHeight: 1.8,
    contentWidth: "narrow",
  },
  "older-users": {
    fontScale: 1.3,
    lineHeight: 1.7,
    enlargeTargets: true,
    highlight: LINKS_ONLY,
    motion: "reduced",
  },
});

export const PROFILE_IDS = Object.keys(PROFILE_PATCHES) as ProfileId[];

export const migrations: Record<number, (input: Record<string, unknown>) => Record<string, unknown>> = {};

export function migrate(stored: Record<string, unknown>): Record<string, unknown> | null {
  let version = typeof stored.version === "number" ? stored.version : 0;
  let payload = stored;

  if (version > SETTINGS_VERSION) return null;

  while (version < SETTINGS_VERSION) {
    const step = migrations[version];
    if (!step) return version === 0 ? payload : null;
    payload = step(payload);
    version += 1;
  }

  return payload;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function clamp(value: unknown, limits: { min: number; max: number }, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(limits.max, Math.max(limits.min, value));
}

function oneOf<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value)
    ? (value as T)
    : fallback;
}

function flag(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function colour(value: unknown): string | undefined {
  return typeof value === "string" && /^#[0-9a-f]{3,8}$/i.test(value) ? value : undefined;
}

export function sanitiseSettings(input: unknown): A11ySettings {
  const raw = asRecord(input);
  const d = DEFAULT_SETTINGS;
  const highlight = asRecord(raw.highlight);
  const tts = asRecord(raw.tts);
  const toolbar = asRecord(raw.toolbar);
  const colours = asRecord(raw.customColors);
  const customColors: CustomColors = {};
  for (const key of ["background", "heading", "text", "link"] as const) {
    const value = colour(colours[key]);
    if (value) customColors[key] = value;
  }

  return {
    version: SETTINGS_VERSION,
    profile: oneOf<ProfileId | "none">(raw.profile, PROFILE_IDS, "none") === "none" ? null : (raw.profile as ProfileId),
    theme: oneOf(raw.theme, THEME_IDS, d.theme),
    customColors: Object.keys(customColors).length > 0 ? customColors : null,
    fontScale: clamp(raw.fontScale, SETTING_LIMITS.fontScale, d.fontScale),
    lineHeight: clamp(raw.lineHeight, SETTING_LIMITS.lineHeight, d.lineHeight),
    letterSpacing: clamp(raw.letterSpacing, SETTING_LIMITS.letterSpacing, d.letterSpacing),
    wordSpacing: clamp(raw.wordSpacing, SETTING_LIMITS.wordSpacing, d.wordSpacing),
    fontFamily: oneOf(raw.fontFamily, ["default", "readable", "dyslexic"] as const, d.fontFamily),
    contentWidth: oneOf(raw.contentWidth, ["default", "narrow"] as const, d.contentWidth),
    cursor: oneOf(raw.cursor, ["default", "large-white", "large-black"] as const, d.cursor),
    highlight: {
      links: flag(highlight.links, d.highlight.links),
      headings: flag(highlight.headings, d.highlight.headings),
      focus: flag(highlight.focus, d.highlight.focus),
      hover: flag(highlight.hover, d.highlight.hover),
    },
    motion: oneOf(raw.motion, ["default", "reduced", "off"] as const, d.motion),
    muteMedia: flag(raw.muteMedia, d.muteMedia),
    enlargeTargets: flag(raw.enlargeTargets, d.enlargeTargets),
    readingGuide: oneOf(raw.readingGuide, ["off", "ruler", "mask"] as const, d.readingGuide),
    readFocus: flag(raw.readFocus, d.readFocus),
    magnifier: oneOf(raw.magnifier, ["off", "text-hover", "lens"] as const, d.magnifier),
    tts: {
      enabled: flag(tts.enabled, d.tts.enabled),
      rate: clamp(tts.rate, SETTING_LIMITS.rate, d.tts.rate),
      pitch: clamp(tts.pitch, SETTING_LIMITS.pitch, d.tts.pitch),
      voiceURI: typeof tts.voiceURI === "string" ? tts.voiceURI : null,
      highlight: flag(tts.highlight, d.tts.highlight),
    },
    voiceCommands: flag(raw.voiceCommands, d.voiceCommands),
    virtualKeyboard: flag(raw.virtualKeyboard, d.virtualKeyboard),
    toolbar: {
      position: oneOf(toolbar.position, ["left", "right"] as const, d.toolbar.position),
      hidden: flag(toolbar.hidden, d.toolbar.hidden),
    },
  };
}
