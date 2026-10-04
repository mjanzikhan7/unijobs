export { TOOLBAR_HOST_ID } from "./constants";
export {
  DEFAULT_SETTINGS,
  PROFILE_IDS,
  PROFILE_PATCHES,
  SETTINGS_VERSION,
  SETTING_LIMITS,
  THEME_IDS,
  migrate,
  sanitiseSettings,
  type A11ySettings,
  type CustomColors,
  type HighlightSettings,
  type ProfileId,
  type SettableKey,
  type ThemeId,
  type ToolbarSettings,
  type TtsSettings,
} from "./settings";
export {
  createLocalStorageAdapter,
  createNoopStorageAdapter,
  type RemoteSyncAdapter,
  type StorageAdapter,
} from "./storage";
export { applySettings, clearSettings, type ApplyTargets } from "./apply";
export { DALTONIZE_FILTER_IDS, ensureDaltonizeFilters, removeDaltonizeFilters } from "./daltonize";
export { createMuteMediaController, type MuteMediaController } from "./muteMedia";
export {
  READING_HIGHLIGHT,
  WORD_HIGHLIGHT,
  SpeechController,
  blockFromRange,
  chunkBlocks,
  collectBlocks,
  describeControl,
  rangeFor,
  type SpeechChunk,
  type SpeechControllerOptions,
  type SpeechSource,
  type SpeechState,
  type SpeechStatus,
  type SpeechVoice,
  type TextBlock,
} from "./speech";
export {
  A11yEngine,
  type A11yEngineOptions,
  type A11yTelemetryEvent,
  type Announce,
} from "./engine";
