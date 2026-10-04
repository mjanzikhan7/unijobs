// src/core/constants.ts
var TOOLBAR_HOST_ID = "unijobs-a11y-toolbar";

// src/core/settings.ts
var SETTINGS_VERSION = 1;
var THEME_IDS = [
  "default",
  "contrast-dark",
  "contrast-light",
  "monochrome",
  "saturation-low",
  "saturation-high",
  "protanopia",
  "deuteranopia",
  "tritanopia",
  "invert"
];
var DEFAULT_SETTINGS = Object.freeze({
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
  toolbar: Object.freeze({ position: "right", hidden: false })
});
var SETTING_LIMITS = Object.freeze({
  fontScale: { min: 1, max: 2 },
  lineHeight: { min: 1.5, max: 2.5 },
  letterSpacing: { min: 0, max: 0.3 },
  wordSpacing: { min: 0, max: 0.6 },
  rate: { min: 0.5, max: 2 },
  pitch: { min: 0, max: 2 }
});
var LINKS_ONLY = { links: true, headings: false, focus: false, hover: false };
var PROFILE_PATCHES = Object.freeze({
  "low-vision": {
    fontScale: 1.5,
    lineHeight: 1.8,
    theme: "contrast-dark",
    highlight: { ...LINKS_ONLY, focus: true },
    cursor: "large-white",
    enlargeTargets: true
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
    contentWidth: "narrow"
  },
  "older-users": {
    fontScale: 1.3,
    lineHeight: 1.7,
    enlargeTargets: true,
    highlight: LINKS_ONLY,
    motion: "reduced"
  }
});
var PROFILE_IDS = Object.keys(PROFILE_PATCHES);
var migrations = {};
function migrate(stored) {
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
function asRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value : {};
}
function clamp(value, limits, fallback) {
  if (typeof value !== "number" || !Number.isFinite(value)) return fallback;
  return Math.min(limits.max, Math.max(limits.min, value));
}
function oneOf(value, allowed, fallback) {
  return typeof value === "string" && allowed.includes(value) ? value : fallback;
}
function flag(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}
function colour(value) {
  return typeof value === "string" && /^#[0-9a-f]{3,8}$/i.test(value) ? value : void 0;
}
function sanitiseSettings(input) {
  const raw = asRecord(input);
  const d = DEFAULT_SETTINGS;
  const highlight = asRecord(raw.highlight);
  const tts = asRecord(raw.tts);
  const toolbar = asRecord(raw.toolbar);
  const colours = asRecord(raw.customColors);
  const customColors = {};
  for (const key of ["background", "heading", "text", "link"]) {
    const value = colour(colours[key]);
    if (value) customColors[key] = value;
  }
  return {
    version: SETTINGS_VERSION,
    profile: oneOf(raw.profile, PROFILE_IDS, "none") === "none" ? null : raw.profile,
    theme: oneOf(raw.theme, THEME_IDS, d.theme),
    customColors: Object.keys(customColors).length > 0 ? customColors : null,
    fontScale: clamp(raw.fontScale, SETTING_LIMITS.fontScale, d.fontScale),
    lineHeight: clamp(raw.lineHeight, SETTING_LIMITS.lineHeight, d.lineHeight),
    letterSpacing: clamp(raw.letterSpacing, SETTING_LIMITS.letterSpacing, d.letterSpacing),
    wordSpacing: clamp(raw.wordSpacing, SETTING_LIMITS.wordSpacing, d.wordSpacing),
    fontFamily: oneOf(raw.fontFamily, ["default", "readable", "dyslexic"], d.fontFamily),
    contentWidth: oneOf(raw.contentWidth, ["default", "narrow"], d.contentWidth),
    cursor: oneOf(raw.cursor, ["default", "large-white", "large-black"], d.cursor),
    highlight: {
      links: flag(highlight.links, d.highlight.links),
      headings: flag(highlight.headings, d.highlight.headings),
      focus: flag(highlight.focus, d.highlight.focus),
      hover: flag(highlight.hover, d.highlight.hover)
    },
    motion: oneOf(raw.motion, ["default", "reduced", "off"], d.motion),
    muteMedia: flag(raw.muteMedia, d.muteMedia),
    enlargeTargets: flag(raw.enlargeTargets, d.enlargeTargets),
    readingGuide: oneOf(raw.readingGuide, ["off", "ruler", "mask"], d.readingGuide),
    readFocus: flag(raw.readFocus, d.readFocus),
    magnifier: oneOf(raw.magnifier, ["off", "text-hover", "lens"], d.magnifier),
    tts: {
      enabled: flag(tts.enabled, d.tts.enabled),
      rate: clamp(tts.rate, SETTING_LIMITS.rate, d.tts.rate),
      pitch: clamp(tts.pitch, SETTING_LIMITS.pitch, d.tts.pitch),
      voiceURI: typeof tts.voiceURI === "string" ? tts.voiceURI : null,
      highlight: flag(tts.highlight, d.tts.highlight)
    },
    voiceCommands: flag(raw.voiceCommands, d.voiceCommands),
    virtualKeyboard: flag(raw.virtualKeyboard, d.virtualKeyboard),
    toolbar: {
      position: oneOf(toolbar.position, ["left", "right"], d.toolbar.position),
      hidden: flag(toolbar.hidden, d.toolbar.hidden)
    }
  };
}

// src/core/storage.ts
var STORAGE_KEY = "unijobs.a11y";
function createLocalStorageAdapter(key = STORAGE_KEY) {
  return {
    async read() {
      try {
        const raw = window.localStorage.getItem(key);
        if (!raw) return null;
        return JSON.parse(raw);
      } catch {
        return null;
      }
    },
    async write(settings) {
      try {
        window.localStorage.setItem(key, JSON.stringify(settings));
      } catch {
      }
    },
    async clear() {
      try {
        window.localStorage.removeItem(key);
      } catch {
      }
    }
  };
}
function createNoopStorageAdapter() {
  return {
    async read() {
      return null;
    },
    async write() {
    },
    async clear() {
    }
  };
}

// src/core/daltonize.ts
var DALTONIZE_FILTER_IDS = {
  protanopia: "unijobs-a11y-daltonize-protanopia",
  deuteranopia: "unijobs-a11y-daltonize-deuteranopia",
  tritanopia: "unijobs-a11y-daltonize-tritanopia"
};
var MATRICES = {
  protanopia: "0.856 0.182 -0.038 0 0  0.029 0.905 0.066 0 0  -0.002 -0.001 1.003 0 0  0 0 0 1 0",
  deuteranopia: "0.8 0.258 -0.058 0 0  0.19 0.83 -0.02 0 0  0.017 0.017 0.966 0 0  0 0 0 1 0",
  tritanopia: "0.885 0.098 0.017 0 0  0.026 0.908 0.065 0 0  0.028 0.972 -0.001 0 0  0 0 0 1 0"
};
var CONTAINER_ID = "unijobs-a11y-daltonize-defs";
function ensureDaltonizeFilters(mountPoint) {
  if (mountPoint.ownerDocument.getElementById(CONTAINER_ID)) return;
  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("id", CONTAINER_ID);
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.style.position = "absolute";
  svg.style.width = "0";
  svg.style.height = "0";
  svg.style.overflow = "hidden";
  const defs = document.createElementNS(svgNs, "defs");
  for (const key of Object.keys(MATRICES)) {
    const filter = document.createElementNS(svgNs, "filter");
    filter.setAttribute("id", DALTONIZE_FILTER_IDS[key]);
    filter.setAttribute("color-interpolation-filters", "sRGB");
    const matrix = document.createElementNS(svgNs, "feColorMatrix");
    matrix.setAttribute("type", "matrix");
    matrix.setAttribute("values", MATRICES[key]);
    filter.appendChild(matrix);
    defs.appendChild(filter);
  }
  svg.appendChild(defs);
  mountPoint.appendChild(svg);
}
function removeDaltonizeFilters(mountPoint) {
  mountPoint.ownerDocument.getElementById(CONTAINER_ID)?.remove();
}

// src/core/apply.ts
var MANAGED_DATA_ATTRS = [
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
  "a11yReadOnClick"
];
var MANAGED_CSS_PROPS = [
  "--a11y-font-scale",
  "--a11y-line-height",
  "--a11y-letter-spacing",
  "--a11y-word-spacing",
  "--a11y-custom-bg",
  "--a11y-custom-heading",
  "--a11y-custom-text",
  "--a11y-custom-link"
];
function attr(root, name, value) {
  if (value === null) delete root.dataset[name];
  else root.dataset[name] = value;
}
function prop(root, name, value) {
  if (value === null) root.style.removeProperty(name);
  else root.style.setProperty(name, value);
}
var DALTONISATION_THEMES = /* @__PURE__ */ new Set(["protanopia", "deuteranopia", "tritanopia"]);
function applySettings(settings, { root }) {
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
function clearSettings({ root }) {
  for (const name of MANAGED_DATA_ATTRS) delete root.dataset[name];
  for (const name of MANAGED_CSS_PROPS) root.style.removeProperty(name);
  if (root.getAttribute("style") === "") root.removeAttribute("style");
}

// src/core/muteMedia.ts
function createMuteMediaController(scope = document.body) {
  let observer = null;
  function muteAll() {
    for (const el of scope.querySelectorAll("video, audio")) {
      el.muted = true;
    }
  }
  return {
    start() {
      if (observer) return;
      muteAll();
      observer = new MutationObserver(muteAll);
      observer.observe(scope, { childList: true, subtree: true });
    },
    stop() {
      observer?.disconnect();
      observer = null;
    }
  };
}

// src/core/speech.ts
var READING_HIGHLIGHT = "unijobs-a11y-reading";
var WORD_HIGHLIGHT = "unijobs-a11y-word";
var MAX_CHUNK_LENGTH = 200;
var FOCUS_READ_DELAY_MS = 150;
var EXCLUDED_SELECTOR = "script, style, noscript, template, svg, [aria-hidden='true'], [hidden], [inert]";
var INTERACTIVE_SELECTOR = [
  "a[href]",
  "button",
  "input",
  "select",
  "textarea",
  "summary",
  "[role='button']",
  "[role='link']",
  "[role='checkbox']",
  "[role='radio']",
  "[role='switch']",
  "[role='tab']",
  "[role='menuitem']",
  "[role='option']",
  "[contenteditable='true']"
].join(", ");
var PHRASING_TAGS = /* @__PURE__ */ new Set([
  "A",
  "ABBR",
  "B",
  "BDI",
  "BDO",
  "BR",
  "CITE",
  "CODE",
  "DATA",
  "DFN",
  "EM",
  "I",
  "KBD",
  "LABEL",
  "MARK",
  "Q",
  "S",
  "SAMP",
  "SMALL",
  "SPAN",
  "STRONG",
  "SUB",
  "SUP",
  "TIME",
  "U",
  "VAR",
  "WBR"
]);
function hasNoUserAgentStylesheet(doc) {
  return /jsdom/i.test(doc.defaultView?.navigator.userAgent ?? "");
}
function isInline(el, cache) {
  let inline = cache.get(el);
  if (inline === void 0) {
    if (hasNoUserAgentStylesheet(el.ownerDocument)) {
      inline = PHRASING_TAGS.has(el.tagName);
    } else {
      const display = el.ownerDocument.defaultView?.getComputedStyle(el).display ?? "block";
      inline = display === "inline" || display === "contents";
    }
    cache.set(el, inline);
  }
  return inline;
}
function blockElementFor(el, boundary, cache = /* @__PURE__ */ new Map()) {
  let current = el;
  while (current !== boundary && current.parentElement && isInline(current, cache)) {
    current = current.parentElement;
  }
  return current;
}
function isHidden(el, cache) {
  const cached = cache.get(el);
  if (cached !== void 0) return cached;
  let hidden = el.closest(EXCLUDED_SELECTOR) !== null || el.closest(`#${TOOLBAR_HOST_ID}`) !== null;
  if (!hidden) {
    const checkable = el;
    if (typeof checkable.checkVisibility === "function") {
      hidden = !checkable.checkVisibility({ visibilityProperty: true, checkVisibilityCSS: true });
    } else {
      for (let node = el; node; node = node.parentElement) {
        const style = node.ownerDocument.defaultView?.getComputedStyle(node);
        if (style && (style.display === "none" || style.visibility === "hidden")) {
          hidden = true;
          break;
        }
      }
    }
  }
  cache.set(el, hidden);
  return hidden;
}
function appendSlice(block, node, from, to) {
  const part = node.data.slice(from, to);
  if (!part) return;
  block.slices.push({
    node,
    start: block.text.length,
    end: block.text.length + part.length,
    nodeOffset: from
  });
  block.text += part;
}
function collectBlocks(root) {
  const doc = root.ownerDocument;
  const displayCache = /* @__PURE__ */ new Map();
  const hiddenCache = /* @__PURE__ */ new Map();
  const blocks = [];
  let current = null;
  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node;
    const parent = text.parentElement;
    if (!parent || isHidden(parent, hiddenCache)) continue;
    const element = blockElementFor(parent, root, displayCache);
    const blank = text.data.trim() === "";
    if (blank && current?.element !== element) continue;
    if (!current || current.element !== element) {
      current = { element, text: "", slices: [] };
      blocks.push(current);
    }
    appendSlice(current, text, 0, text.data.length);
  }
  return blocks.filter((block) => block.text.trim() !== "");
}
function blockFromRange(range) {
  const container = range.commonAncestorContainer;
  if (container.nodeType === Node.TEXT_NODE) {
    const text = container;
    const block2 = { element: text.parentElement ?? text.ownerDocument.body, text: "", slices: [] };
    appendSlice(block2, text, range.startOffset, range.endOffset);
    return block2.text.trim() ? block2 : null;
  }
  const rootEl = container;
  const block = { element: rootEl, text: "", slices: [] };
  const displayCache = /* @__PURE__ */ new Map();
  const hiddenCache = /* @__PURE__ */ new Map();
  let previousBlock = null;
  const walker = rootEl.ownerDocument.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!range.intersectsNode(node)) continue;
    const text = node;
    const parent = text.parentElement;
    if (!parent || isHidden(parent, hiddenCache)) continue;
    const owner = blockElementFor(parent, rootEl, displayCache);
    if (previousBlock && owner !== previousBlock && block.text && !/\s$/.test(block.text)) {
      block.text += " ";
    }
    previousBlock = owner;
    const from = text === range.startContainer ? range.startOffset : 0;
    const to = text === range.endContainer ? range.endOffset : text.data.length;
    appendSlice(block, text, from, to);
  }
  return block.text.trim() ? block : null;
}
function rangeFor(block, start, end) {
  const first = block.slices.find((slice) => start < slice.end);
  let last;
  for (const slice of block.slices) if (end > slice.start) last = slice;
  if (!first || !last) return null;
  const range = block.element.ownerDocument.createRange();
  try {
    range.setStart(first.node, first.nodeOffset + Math.max(0, start - first.start));
    range.setEnd(last.node, last.nodeOffset + Math.min(last.end, end) - last.start);
  } catch {
    return null;
  }
  return range;
}
function sentenceBounds(text, locale) {
  if (typeof Intl !== "undefined" && typeof Intl.Segmenter === "function") {
    try {
      const segmenter = new Intl.Segmenter(locale, { granularity: "sentence" });
      return Array.from(segmenter.segment(text), (s) => [s.index, s.index + s.segment.length]);
    } catch {
    }
  }
  const bounds = [];
  const pattern = /[^.!?]+(?:[.!?]+["')\]’”]*|$)\s*/g;
  for (let match = pattern.exec(text); match !== null; match = pattern.exec(text)) {
    if (match[0] === "") {
      pattern.lastIndex += 1;
      continue;
    }
    bounds.push([match.index, match.index + match[0].length]);
  }
  return bounds.length > 0 ? bounds : [[0, text.length]];
}
function splitLong(text, start, end) {
  const parts = [];
  let from = start;
  while (end - from > MAX_CHUNK_LENGTH) {
    let cut = text.lastIndexOf(" ", from + MAX_CHUNK_LENGTH);
    if (cut <= from) cut = from + MAX_CHUNK_LENGTH;
    parts.push([from, cut]);
    from = cut;
  }
  parts.push([from, end]);
  return parts;
}
function chunkBlocks(blocks, locale) {
  const chunks = [];
  for (const block of blocks) {
    for (const [sentenceStart, sentenceEnd] of sentenceBounds(block.text, locale)) {
      for (const [partStart, partEnd] of splitLong(block.text, sentenceStart, sentenceEnd)) {
        let start = partStart;
        let end = partEnd;
        while (start < end && /\s/.test(block.text.charAt(start))) start += 1;
        while (end > start && /\s/.test(block.text.charAt(end - 1))) end -= 1;
        if (end > start) chunks.push({ block, start, end, text: block.text.slice(start, end) });
      }
    }
  }
  return chunks;
}
function localeFor(el) {
  return el.closest("[lang]")?.getAttribute("lang") || el.ownerDocument.documentElement.lang || "en";
}
function textOf(el) {
  return el?.textContent?.replace(/\s+/g, " ").trim() ?? "";
}
function accessibleName(el) {
  const doc = el.ownerDocument;
  const labelledBy = el.getAttribute("aria-labelledby");
  if (labelledBy) {
    const name = labelledBy.split(/\s+/).map((id) => textOf(doc.getElementById(id))).filter(Boolean).join(" ");
    if (name) return name;
  }
  const ariaLabel = el.getAttribute("aria-label")?.trim();
  if (ariaLabel) return ariaLabel;
  if (el instanceof HTMLInputElement || el instanceof HTMLSelectElement || el instanceof HTMLTextAreaElement) {
    const labels = Array.from(el.labels ?? [], (label) => textOf(label)).filter(Boolean).join(" ");
    if (labels) return labels;
    if ("placeholder" in el && el.placeholder) return el.placeholder;
  }
  const text = textOf(el);
  if (text) return text;
  const alt = el.querySelector("img[alt]")?.getAttribute("alt")?.trim();
  if (alt) return alt;
  return el.getAttribute("title")?.trim() ?? "";
}
function roleName(el) {
  const role = el.getAttribute("role");
  if (role) return role === "menuitem" ? "menu item" : role;
  if (el instanceof HTMLInputElement) {
    switch (el.type) {
      case "checkbox":
        return "checkbox";
      case "radio":
        return "radio button";
      case "range":
        return "slider";
      case "search":
        return "search field";
      case "button":
      case "submit":
      case "reset":
        return "button";
      default:
        return "text field";
    }
  }
  switch (el.tagName) {
    case "A":
      return "link";
    case "BUTTON":
    case "SUMMARY":
      return "button";
    case "SELECT":
      return "drop-down list";
    case "TEXTAREA":
      return "text area";
    default:
      return "";
  }
}
function describeControl(el) {
  const parts = [accessibleName(el), roleName(el)];
  if (el.getAttribute("aria-pressed") === "true") parts.push("pressed");
  const expanded = el.getAttribute("aria-expanded");
  if (expanded === "true") parts.push("expanded");
  if (expanded === "false") parts.push("collapsed");
  if (el.getAttribute("aria-current") === "page") parts.push("current page");
  if (el instanceof HTMLInputElement && (el.type === "checkbox" || el.type === "radio")) {
    parts.push(el.checked ? "checked" : "not checked");
  } else if (el.getAttribute("aria-checked") === "true") {
    parts.push("checked");
  }
  if (el instanceof HTMLInputElement && el.type === "range") {
    parts.push(el.getAttribute("aria-valuetext") ?? el.value);
  }
  if (el.disabled || el.getAttribute("aria-disabled") === "true") {
    parts.push("unavailable");
  }
  return parts.filter(Boolean).join(", ");
}
function highlightRegistry() {
  const g = globalThis;
  return typeof g.Highlight === "function" && g.CSS?.highlights ? { registry: g.CSS.highlights, Highlight: g.Highlight } : null;
}
function composedPathHitsToolbar(event) {
  return event.composedPath().some((target) => target instanceof Element && target.id === TOOLBAR_HOST_ID);
}
var SpeechController = class {
  #doc;
  #getSettings;
  #listeners = /* @__PURE__ */ new Set();
  #state;
  #queue = [];
  #index = 0;
  #run = 0;
  #selection = null;
  #pointerInToolbar = false;
  #connected = false;
  #readOnInteraction = false;
  #focusTimer;
  constructor({ getSettings, document: doc = document }) {
    this.#doc = doc;
    this.#getSettings = getSettings;
    const win = doc.defaultView;
    this.#state = {
      supported: Boolean(win && "speechSynthesis" in win && "SpeechSynthesisUtterance" in win),
      highlightSupported: highlightRegistry() !== null,
      status: "idle",
      source: null,
      voices: [],
      hasSelection: false
    };
  }
  get state() {
    return this.#state;
  }
  subscribe(listener) {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }
  connect() {
    if (this.#connected) return;
    this.#connected = true;
    this.#doc.addEventListener("selectionchange", this.#onSelectionChange);
    this.#doc.addEventListener("pointerdown", this.#onPointerDown, true);
    this.#doc.defaultView?.addEventListener("pagehide", this.#onPageHide);
    const synth = this.#synth();
    if (synth) {
      if (typeof synth.addEventListener === "function") synth.addEventListener("voiceschanged", this.#loadVoices);
      else synth.onvoiceschanged = this.#loadVoices;
      this.#loadVoices();
    }
  }
  disconnect() {
    if (!this.#connected) return;
    this.stop();
    this.setReadOnInteraction(false);
    this.#doc.removeEventListener("selectionchange", this.#onSelectionChange);
    this.#doc.removeEventListener("pointerdown", this.#onPointerDown, true);
    this.#doc.defaultView?.removeEventListener("pagehide", this.#onPageHide);
    const synth = this.#synth();
    if (synth && typeof synth.removeEventListener === "function") {
      synth.removeEventListener("voiceschanged", this.#loadVoices);
    }
    this.#connected = false;
  }
  setReadOnInteraction(enabled) {
    if (enabled === this.#readOnInteraction) return;
    this.#readOnInteraction = enabled;
    if (enabled) {
      this.#doc.addEventListener("click", this.#onClick, true);
      this.#doc.addEventListener("focusin", this.#onFocusIn, true);
    } else {
      this.#doc.removeEventListener("click", this.#onClick, true);
      this.#doc.removeEventListener("focusin", this.#onFocusIn, true);
      clearTimeout(this.#focusTimer);
    }
  }
  speakPage(root) {
    const target = root ?? this.#doc.querySelector("main") ?? this.#doc.body;
    return this.#start(collectBlocks(target), "page");
  }
  speakElement(element, source = "element") {
    return this.#start(collectBlocks(element), source);
  }
  speakSelection() {
    const block = this.#selection ? blockFromRange(this.#selection) : null;
    return block ? this.#start([block], "selection") : false;
  }
  speakText(text, source = "text") {
    const trimmed = text.replace(/\s+/g, " ").trim();
    if (!trimmed) return false;
    return this.#start([{ element: this.#doc.documentElement, text: trimmed, slices: [] }], source);
  }
  pause() {
    const synth = this.#synth();
    if (!synth || this.#state.status !== "speaking") return;
    synth.pause();
    this.#setState({ status: "paused" });
  }
  resume() {
    const synth = this.#synth();
    if (!synth || this.#state.status !== "paused") return;
    synth.resume();
    this.#setState({ status: "speaking" });
  }
  stop() {
    this.#run += 1;
    this.#queue = [];
    this.#index = 0;
    this.#clearHighlights();
    if (this.#state.status !== "idle" || this.#state.source !== null) {
      this.#synth()?.cancel();
      this.#setState({ status: "idle", source: null });
    }
  }
  #synth() {
    return this.#state.supported ? this.#doc.defaultView?.speechSynthesis ?? null : null;
  }
  #setState(partial) {
    this.#state = { ...this.#state, ...partial };
    for (const listener of this.#listeners) listener();
  }
  #start(blocks, source) {
    const first = blocks[0];
    if (!this.#synth() || !first) return false;
    const chunks = chunkBlocks(blocks, localeFor(first.element));
    if (chunks.length === 0) return false;
    this.stop();
    this.#synth()?.cancel();
    const run = this.#run;
    this.#queue = chunks;
    this.#index = 0;
    this.#setState({ status: "speaking", source });
    setTimeout(() => this.#speakNext(run), 0);
    return true;
  }
  #speakNext(run) {
    if (run !== this.#run) return;
    const synth = this.#synth();
    const chunk = this.#queue[this.#index];
    if (!synth || !chunk) {
      this.#clearHighlights();
      this.#queue = [];
      this.#setState({ status: "idle", source: null });
      return;
    }
    const settings = this.#getSettings();
    const utterance = new SpeechSynthesisUtterance(chunk.text);
    utterance.rate = Math.min(SETTING_LIMITS.rate.max, Math.max(SETTING_LIMITS.rate.min, settings.rate));
    utterance.pitch = Math.min(SETTING_LIMITS.pitch.max, Math.max(SETTING_LIMITS.pitch.min, settings.pitch));
    utterance.lang = localeFor(chunk.block.element);
    const voice = settings.voiceURI ? synth.getVoices().find((candidate) => candidate.voiceURI === settings.voiceURI) : void 0;
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    }
    utterance.onstart = () => {
      if (run === this.#run) this.#highlightChunk(chunk, settings.highlight);
    };
    utterance.onboundary = (event) => {
      if (run === this.#run && settings.highlight && event.name === "word") {
        this.#highlightWord(chunk, event.charIndex, event.charLength);
      }
    };
    utterance.onend = () => {
      if (run !== this.#run) return;
      this.#index += 1;
      this.#speakNext(run);
    };
    utterance.onerror = (event) => {
      if (run !== this.#run || event.error === "interrupted" || event.error === "canceled") return;
      this.#index += 1;
      this.#speakNext(run);
    };
    synth.speak(utterance);
  }
  #highlightChunk(chunk, enabled) {
    const range = rangeFor(chunk.block, chunk.start, chunk.end);
    if (range) this.#reveal(range);
    const api = highlightRegistry();
    if (!api) return;
    api.registry.delete(WORD_HIGHLIGHT);
    if (enabled && range) api.registry.set(READING_HIGHLIGHT, new api.Highlight(range));
    else api.registry.delete(READING_HIGHLIGHT);
  }
  #highlightWord(chunk, charIndex, charLength) {
    const api = highlightRegistry();
    if (!api) return;
    let length = charLength ?? 0;
    if (!length) length = /^\S+/.exec(chunk.text.slice(charIndex))?.[0].length ?? 0;
    if (!length) return;
    const start = chunk.start + charIndex;
    const range = rangeFor(chunk.block, start, Math.min(chunk.end, start + length));
    if (range) api.registry.set(WORD_HIGHLIGHT, new api.Highlight(range));
  }
  #clearHighlights() {
    const api = highlightRegistry();
    api?.registry.delete(READING_HIGHLIGHT);
    api?.registry.delete(WORD_HIGHLIGHT);
  }
  #reveal(range) {
    const view = this.#doc.defaultView;
    if (!view || typeof range.getBoundingClientRect !== "function") return;
    const rect = range.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;
    if (rect.top >= 0 && rect.bottom <= view.innerHeight) return;
    const reduceMotion = view.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true || this.#doc.documentElement.dataset.a11yMotion !== void 0;
    view.scrollBy({ top: rect.top - view.innerHeight / 3, behavior: reduceMotion ? "auto" : "smooth" });
  }
  #loadVoices = () => {
    const synth = this.#synth();
    if (!synth) return;
    const voices = synth.getVoices().map((voice) => ({
      uri: voice.voiceURI,
      name: voice.name,
      lang: voice.lang,
      isDefault: voice.default
    }));
    const unchanged = voices.length === this.#state.voices.length && voices.every((voice, i) => voice.uri === this.#state.voices[i]?.uri);
    if (!unchanged) this.#setState({ voices });
  };
  #onPageHide = () => this.stop();
  #onPointerDown = (event) => {
    this.#pointerInToolbar = composedPathHitsToolbar(event);
  };
  #onSelectionChange = () => {
    const selection = this.#doc.getSelection();
    const hasText = selection !== null && !selection.isCollapsed && selection.rangeCount > 0 && selection.toString().trim() !== "";
    if (hasText) {
      this.#selection = selection.getRangeAt(0).cloneRange();
      if (!this.#state.hasSelection) this.#setState({ hasSelection: true });
    } else if (!this.#pointerInToolbar && this.#state.hasSelection) {
      this.#selection = null;
      this.#setState({ hasSelection: false });
    }
  };
  #onClick = (event) => {
    if (event.defaultPrevented || event.button !== 0 || composedPathHitsToolbar(event)) return;
    const target = event.composedPath().find((item) => item instanceof Element);
    if (!target || target.closest(INTERACTIVE_SELECTOR)) return;
    const selection = this.#doc.getSelection();
    if (selection && !selection.isCollapsed) return;
    this.speakElement(blockElementFor(target, this.#doc.body), "element");
  };
  #onFocusIn = (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || target.id === TOOLBAR_HOST_ID) return;
    if (!target.matches(INTERACTIVE_SELECTOR)) return;
    try {
      if (!target.matches(":focus-visible")) return;
    } catch {
    }
    clearTimeout(this.#focusTimer);
    this.#focusTimer = setTimeout(() => {
      const description = describeControl(target);
      if (description) this.speakText(description, "focus");
    }, FOCUS_READ_DELAY_MS);
  };
};

// src/core/engine.ts
var DEFAULT_PERSIST_DEBOUNCE_MS = 400;
function cloneSettings(settings) {
  return {
    ...settings,
    customColors: settings.customColors ? { ...settings.customColors } : null,
    highlight: { ...settings.highlight },
    tts: { ...settings.tts },
    toolbar: { ...settings.toolbar }
  };
}
function mergeSettings(base, patch) {
  const defined = Object.fromEntries(
    Object.entries(patch).filter(([, value]) => value !== void 0)
  );
  return cloneSettings({ ...base, ...defined });
}
function revertKeys(settings, keys) {
  const defaults = cloneSettings(DEFAULT_SETTINGS);
  const reverted = Object.fromEntries(keys.map((key) => [key, defaults[key]]));
  return mergeSettings(settings, reverted);
}
var A11yEngine = class {
  speech;
  #settings = cloneSettings(DEFAULT_SETTINGS);
  #listeners = /* @__PURE__ */ new Set();
  #root;
  #storage;
  #remote;
  #announce;
  #telemetry;
  #persistDebounceMs;
  #muteMedia;
  #persistTimer = null;
  #profileBase = null;
  constructor(options = {}) {
    this.#root = options.root ?? document.documentElement;
    this.#storage = options.storage ?? createLocalStorageAdapter();
    this.#remote = options.remote ?? null;
    this.#announce = options.announce ?? null;
    this.#telemetry = options.telemetry ?? null;
    this.#persistDebounceMs = options.persistDebounceMs ?? DEFAULT_PERSIST_DEBOUNCE_MS;
    this.#muteMedia = createMuteMediaController(this.#root.ownerDocument.body);
    this.speech = new SpeechController({
      getSettings: () => this.#settings.tts,
      document: this.#root.ownerDocument
    });
  }
  get settings() {
    return this.#settings;
  }
  async init() {
    this.speech.connect();
    let stored = null;
    try {
      stored = await (this.#remote ?? this.#storage).read();
    } catch {
      stored = null;
    }
    if (stored !== null && typeof stored === "object") {
      const migrated = migrate(stored);
      if (migrated) this.#settings = sanitiseSettings(migrated);
    }
    this.#applyAndNotify();
  }
  set(key, value) {
    this.#profileBase = null;
    this.#telemetry?.({ type: "set", key });
    this.#commit(mergeSettings(this.#settings, { [key]: value, profile: null }));
  }
  patch(partial) {
    this.#profileBase = null;
    this.#telemetry?.({ type: "patch" });
    this.#commit(mergeSettings(this.#settings, { ...partial, profile: null }));
  }
  applyProfile(id) {
    if (this.#settings.profile === id) {
      this.clearProfile();
      return;
    }
    const base = this.#profileBase ?? { ...cloneSettings(this.#settings), profile: null };
    this.#profileBase = base;
    this.#telemetry?.({ type: "applyProfile", profile: id });
    this.#commit(mergeSettings(base, { ...PROFILE_PATCHES[id], profile: id }));
  }
  clearProfile() {
    const active = this.#settings.profile;
    if (!active) return;
    const next = this.#profileBase ? cloneSettings(this.#profileBase) : revertKeys(this.#settings, Object.keys(PROFILE_PATCHES[active]));
    this.#profileBase = null;
    this.#telemetry?.({ type: "clearProfile", profile: active });
    this.#commit({ ...next, profile: null });
  }
  resetKeys(keys) {
    this.#profileBase = null;
    this.#telemetry?.({ type: "resetKeys", keys });
    this.#commit({ ...revertKeys(this.#settings, keys), profile: null });
  }
  reset() {
    this.#profileBase = null;
    this.#cancelPersist();
    this.#settings = cloneSettings(DEFAULT_SETTINGS);
    this.#telemetry?.({ type: "reset" });
    this.#applyAndNotify();
    void this.#storage.clear();
    void this.#remote?.clear();
  }
  subscribe(listener) {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }
  announce(message, politeness = "polite") {
    this.#announce?.(message, politeness);
  }
  destroy() {
    this.#cancelPersist();
    this.#muteMedia.stop();
    this.speech.disconnect();
    clearSettings({ root: this.#root });
    removeDaltonizeFilters(this.#root.ownerDocument.body);
  }
  #commit(next) {
    this.#settings = next;
    this.#applyAndNotify();
    this.#schedulePersist();
  }
  #applyAndNotify() {
    applySettings(this.#settings, { root: this.#root });
    if (this.#settings.muteMedia) this.#muteMedia.start();
    else this.#muteMedia.stop();
    this.speech.setReadOnInteraction(this.#settings.tts.enabled);
    for (const listener of this.#listeners) listener(this.#settings);
  }
  #cancelPersist() {
    if (this.#persistTimer) clearTimeout(this.#persistTimer);
    this.#persistTimer = null;
  }
  #schedulePersist() {
    this.#cancelPersist();
    const snapshot = this.#settings;
    this.#persistTimer = setTimeout(() => {
      this.#persistTimer = null;
      void this.#storage.write(snapshot);
      void this.#remote?.write(snapshot);
    }, this.#persistDebounceMs);
  }
};

export { A11yEngine, DALTONIZE_FILTER_IDS, DEFAULT_SETTINGS, PROFILE_IDS, PROFILE_PATCHES, READING_HIGHLIGHT, SETTINGS_VERSION, SETTING_LIMITS, SpeechController, THEME_IDS, TOOLBAR_HOST_ID, WORD_HIGHLIGHT, applySettings, blockFromRange, chunkBlocks, clearSettings, collectBlocks, createLocalStorageAdapter, createMuteMediaController, createNoopStorageAdapter, describeControl, ensureDaltonizeFilters, migrate, rangeFor, removeDaltonizeFilters, sanitiseSettings };
//# sourceMappingURL=chunk-S7H7F2SZ.js.map
//# sourceMappingURL=chunk-S7H7F2SZ.js.map