import { ensureDaltonizeFilters } from "./daltonize";
import { DEFAULT_SETTINGS, type A11ySettings } from "./settings";

const MANAGED_DATA_ATTRS = [
  "a11yTheme",
  "a11yFont",
  "a11yMotion",
  "a11yContentWidth",
  "a11yCursor",
  "a11yTextScale",
  "a11yLineHeight",
  "a11yLetterSpacing",
  "a11yWordSpacing",
  "a11yHighlightLinks",
  "a11yHighlightHeadings",
  "a11yHighlightFocus",
  "a11yHighlightHover",
  "a11yEnlargeTargets",
  "a11yMuteMedia",
  "a11yCustomColors",
  "a11yReadOnClick",
] as const;

type ManagedAttr = (typeof MANAGED_DATA_ATTRS)[number];

const MANAGED_CSS_PROPS = [
  "--a11y-font-scale",
  "--a11y-line-height",
  "--a11y-letter-spacing",
  "--a11y-word-spacing",
  "--a11y-custom-bg",
  "--a11y-custom-heading",
  "--a11y-custom-text",
  "--a11y-custom-link",
] as const;

type ManagedProp = (typeof MANAGED_CSS_PROPS)[number];

export interface ApplyTargets {
  root: HTMLElement;
}

function attr(root: HTMLElement, name: ManagedAttr, value: string | null): void {
  if (value === null) delete root.dataset[name];
  else root.dataset[name] = value;
}

function prop(root: HTMLElement, name: ManagedProp, value: string | null): void {
  if (value === null) root.style.removeProperty(name);
  else root.style.setProperty(name, value);
}

const DALTONISATION_THEMES = new Set(["protanopia", "deuteranopia", "tritanopia"]);

export function applySettings(settings: A11ySettings, { root }: ApplyTargets): void {
  const d = DEFAULT_SETTINGS;

  attr(root, "a11yTheme", settings.theme !== d.theme ? settings.theme : null);
  attr(root, "a11yFont", settings.fontFamily !== d.fontFamily ? settings.fontFamily : null);
  attr(root, "a11yMotion", settings.motion !== d.motion ? settings.motion : null);
  attr(root, "a11yContentWidth", settings.contentWidth !== d.contentWidth ? settings.contentWidth : null);
  attr(root, "a11yCursor", settings.cursor !== d.cursor ? settings.cursor : null);

  const scaled = settings.fontScale !== d.fontScale;
  attr(root, "a11yTextScale", scaled ? "true" : null);
  prop(root, "--a11y-font-scale", scaled ? String(settings.fontScale) : null);

  const lineHeight = settings.lineHeight !== d.lineHeight;
  attr(root, "a11yLineHeight", lineHeight ? "true" : null);
  prop(root, "--a11y-line-height", lineHeight ? String(settings.lineHeight) : null);

  const letterSpacing = settings.letterSpacing !== d.letterSpacing;
  attr(root, "a11yLetterSpacing", letterSpacing ? "true" : null);
  prop(root, "--a11y-letter-spacing", letterSpacing ? `${settings.letterSpacing}em` : null);

  const wordSpacing = settings.wordSpacing !== d.wordSpacing;
  attr(root, "a11yWordSpacing", wordSpacing ? "true" : null);
  prop(root, "--a11y-word-spacing", wordSpacing ? `${settings.wordSpacing}em` : null);

  attr(root, "a11yHighlightLinks", settings.highlight.links ? "true" : null);
  attr(root, "a11yHighlightHeadings", settings.highlight.headings ? "true" : null);
  attr(root, "a11yHighlightFocus", settings.highlight.focus ? "true" : null);
  attr(root, "a11yHighlightHover", settings.highlight.hover ? "true" : null);
  attr(root, "a11yEnlargeTargets", settings.enlargeTargets ? "true" : null);
  attr(root, "a11yMuteMedia", settings.muteMedia ? "true" : null);
  attr(root, "a11yReadOnClick", settings.tts.enabled ? "true" : null);

  const colours = settings.customColors;
  attr(root, "a11yCustomColors", colours && Object.values(colours).some(Boolean) ? "true" : null);
  prop(root, "--a11y-custom-bg", colours?.background ?? null);
  prop(root, "--a11y-custom-heading", colours?.heading ?? null);
  prop(root, "--a11y-custom-text", colours?.text ?? null);
  prop(root, "--a11y-custom-link", colours?.link ?? null);

  if (DALTONISATION_THEMES.has(settings.theme)) {
    ensureDaltonizeFilters(root.ownerDocument.body);
  }
}

export function clearSettings({ root }: ApplyTargets): void {
  for (const name of MANAGED_DATA_ATTRS) delete root.dataset[name];
  for (const name of MANAGED_CSS_PROPS) root.style.removeProperty(name);
  if (root.getAttribute("style") === "") root.removeAttribute("style");
}
