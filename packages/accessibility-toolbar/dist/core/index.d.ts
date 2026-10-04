import { b as A11ySettings } from '../engine-CSWYEqYM.js';
export { a as A11yEngine, A as A11yEngineOptions, d as A11yTelemetryEvent, e as Announce, C as CustomColors, D as DEFAULT_SETTINGS, H as HighlightSettings, f as PROFILE_IDS, g as PROFILE_PATCHES, P as ProfileId, R as READING_HIGHLIGHT, h as RemoteSyncAdapter, i as SETTINGS_VERSION, j as SETTING_LIMITS, S as SettableKey, k as SpeechChunk, l as SpeechController, m as SpeechControllerOptions, n as SpeechSource, c as SpeechState, o as SpeechStatus, p as SpeechVoice, q as StorageAdapter, T as THEME_IDS, r as TextBlock, s as ThemeId, t as ToolbarSettings, u as TtsSettings, W as WORD_HIGHLIGHT, v as blockFromRange, w as chunkBlocks, x as collectBlocks, y as createLocalStorageAdapter, z as createNoopStorageAdapter, B as describeControl, E as migrate, F as rangeFor, G as sanitiseSettings } from '../engine-CSWYEqYM.js';

declare const TOOLBAR_HOST_ID = "unijobs-a11y-toolbar";

interface ApplyTargets {
    root: HTMLElement;
}
declare function applySettings(settings: A11ySettings, { root }: ApplyTargets): void;
declare function clearSettings({ root }: ApplyTargets): void;

declare const DALTONIZE_FILTER_IDS: {
    readonly protanopia: "unijobs-a11y-daltonize-protanopia";
    readonly deuteranopia: "unijobs-a11y-daltonize-deuteranopia";
    readonly tritanopia: "unijobs-a11y-daltonize-tritanopia";
};
declare function ensureDaltonizeFilters(mountPoint: HTMLElement): void;
declare function removeDaltonizeFilters(mountPoint: HTMLElement): void;

interface MuteMediaController {
    start(): void;
    stop(): void;
}
declare function createMuteMediaController(scope?: Element): MuteMediaController;

export { A11ySettings, type ApplyTargets, DALTONIZE_FILTER_IDS, type MuteMediaController, TOOLBAR_HOST_ID, applySettings, clearSettings, createMuteMediaController, ensureDaltonizeFilters, removeDaltonizeFilters };
