import { TOOLBAR_HOST_ID } from "./constants";
import { SETTING_LIMITS, type TtsSettings } from "./settings";

export type SpeechStatus = "idle" | "speaking" | "paused";
export type SpeechSource = "page" | "selection" | "element" | "focus" | "text";

export interface SpeechVoice {
  uri: string;
  name: string;
  lang: string;
  isDefault: boolean;
}

export interface SpeechState {
  supported: boolean;
  highlightSupported: boolean;
  status: SpeechStatus;
  source: SpeechSource | null;
  voices: readonly SpeechVoice[];
  hasSelection: boolean;
}

export interface TextSlice {
  node: Text;
  start: number;
  end: number;
  nodeOffset: number;
}

export interface TextBlock {
  element: Element;
  text: string;
  slices: TextSlice[];
}

export interface SpeechChunk {
  block: TextBlock;
  start: number;
  end: number;
  text: string;
}

export const READING_HIGHLIGHT = "unijobs-a11y-reading";
export const WORD_HIGHLIGHT = "unijobs-a11y-word";

const MAX_CHUNK_LENGTH = 200;
const FOCUS_READ_DELAY_MS = 150;
const EXCLUDED_SELECTOR =
  "script, style, noscript, template, svg, [aria-hidden='true'], [hidden], [inert]";
const INTERACTIVE_SELECTOR = [
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
  "[contenteditable='true']",
].join(", ");

const PHRASING_TAGS = new Set([
  "A", "ABBR", "B", "BDI", "BDO", "BR", "CITE", "CODE", "DATA", "DFN", "EM", "I", "KBD", "LABEL",
  "MARK", "Q", "S", "SAMP", "SMALL", "SPAN", "STRONG", "SUB", "SUP", "TIME", "U", "VAR", "WBR",
]);

function hasNoUserAgentStylesheet(doc: Document): boolean {
  return /jsdom/i.test(doc.defaultView?.navigator.userAgent ?? "");
}

function isInline(el: Element, cache: Map<Element, boolean>): boolean {
  let inline = cache.get(el);
  if (inline === undefined) {
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

export function blockElementFor(
  el: Element,
  boundary: Element,
  cache: Map<Element, boolean> = new Map(),
): Element {
  let current = el;
  while (current !== boundary && current.parentElement && isInline(current, cache)) {
    current = current.parentElement;
  }
  return current;
}

type VisibilityCheckable = Element & {
  checkVisibility?: (options?: Record<string, boolean>) => boolean;
};

function isHidden(el: Element, cache: Map<Element, boolean>): boolean {
  const cached = cache.get(el);
  if (cached !== undefined) return cached;

  let hidden = el.closest(EXCLUDED_SELECTOR) !== null || el.closest(`#${TOOLBAR_HOST_ID}`) !== null;
  if (!hidden) {
    const checkable = el as VisibilityCheckable;
    if (typeof checkable.checkVisibility === "function") {
      hidden = !checkable.checkVisibility({ visibilityProperty: true, checkVisibilityCSS: true });
    } else {
      for (let node: Element | null = el; node; node = node.parentElement) {
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

function appendSlice(block: TextBlock, node: Text, from: number, to: number): void {
  const part = node.data.slice(from, to);
  if (!part) return;
  block.slices.push({
    node,
    start: block.text.length,
    end: block.text.length + part.length,
    nodeOffset: from,
  });
  block.text += part;
}

export function collectBlocks(root: Element): TextBlock[] {
  const doc = root.ownerDocument;
  const displayCache = new Map<Element, boolean>();
  const hiddenCache = new Map<Element, boolean>();
  const blocks: TextBlock[] = [];
  let current = null as TextBlock | null;

  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node as Text;
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

export function blockFromRange(range: Range): TextBlock | null {
  const container = range.commonAncestorContainer;
  if (container.nodeType === Node.TEXT_NODE) {
    const text = container as Text;
    const block: TextBlock = { element: text.parentElement ?? text.ownerDocument.body, text: "", slices: [] };
    appendSlice(block, text, range.startOffset, range.endOffset);
    return block.text.trim() ? block : null;
  }

  const rootEl = container as Element;
  const block: TextBlock = { element: rootEl, text: "", slices: [] };
  const displayCache = new Map<Element, boolean>();
  const hiddenCache = new Map<Element, boolean>();
  let previousBlock: Element | null = null;

  const walker = rootEl.ownerDocument.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!range.intersectsNode(node)) continue;
    const text = node as Text;
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

export function rangeFor(block: TextBlock, start: number, end: number): Range | null {
  const first = block.slices.find((slice) => start < slice.end);
  let last: TextSlice | undefined;
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

function sentenceBounds(text: string, locale: string): Array<[number, number]> {
  if (typeof Intl !== "undefined" && typeof Intl.Segmenter === "function") {
    try {
      const segmenter = new Intl.Segmenter(locale, { granularity: "sentence" });
      return Array.from(segmenter.segment(text), (s): [number, number] => [s.index, s.index + s.segment.length]);
    } catch {
      // An invalid `lang` attribute throws; fall through to the regex.
    }
  }
  const bounds: Array<[number, number]> = [];
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

function splitLong(text: string, start: number, end: number): Array<[number, number]> {
  const parts: Array<[number, number]> = [];
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

export function chunkBlocks(blocks: readonly TextBlock[], locale: string): SpeechChunk[] {
  const chunks: SpeechChunk[] = [];
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

function localeFor(el: Element): string {
  return el.closest("[lang]")?.getAttribute("lang") || el.ownerDocument.documentElement.lang || "en";
}

function textOf(el: Element | null | undefined): string {
  return el?.textContent?.replace(/\s+/g, " ").trim() ?? "";
}

function accessibleName(el: HTMLElement): string {
  const doc = el.ownerDocument;
  const labelledBy = el.getAttribute("aria-labelledby");
  if (labelledBy) {
    const name = labelledBy
      .split(/\s+/)
      .map((id) => textOf(doc.getElementById(id)))
      .filter(Boolean)
      .join(" ");
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

function roleName(el: HTMLElement): string {
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

export function describeControl(el: HTMLElement): string {
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
  if ((el as HTMLButtonElement).disabled || el.getAttribute("aria-disabled") === "true") {
    parts.push("unavailable");
  }

  return parts.filter(Boolean).join(", ");
}

type HighlightGlobals = typeof globalThis & {
  Highlight?: new (...ranges: Range[]) => unknown;
  CSS?: { highlights?: { set(name: string, highlight: unknown): unknown; delete(name: string): boolean } };
};

function highlightRegistry() {
  const g = globalThis as HighlightGlobals;
  return typeof g.Highlight === "function" && g.CSS?.highlights
    ? { registry: g.CSS.highlights, Highlight: g.Highlight }
    : null;
}

function composedPathHitsToolbar(event: Event): boolean {
  return event.composedPath().some((target) => target instanceof Element && target.id === TOOLBAR_HOST_ID);
}

export interface SpeechControllerOptions {
  getSettings: () => Readonly<TtsSettings>;
  document?: Document;
}

type Listener = () => void;

export class SpeechController {
  readonly #doc: Document;
  readonly #getSettings: () => Readonly<TtsSettings>;
  readonly #listeners = new Set<Listener>();
  #state: SpeechState;
  #queue: SpeechChunk[] = [];
  #index = 0;
  #run = 0;
  #selection: Range | null = null;
  #pointerInToolbar = false;
  #connected = false;
  #readOnInteraction = false;
  #focusTimer: ReturnType<typeof setTimeout> | undefined;

  constructor({ getSettings, document: doc = document }: SpeechControllerOptions) {
    this.#doc = doc;
    this.#getSettings = getSettings;
    const win = doc.defaultView;
    this.#state = {
      supported: Boolean(win && "speechSynthesis" in win && "SpeechSynthesisUtterance" in win),
      highlightSupported: highlightRegistry() !== null,
      status: "idle",
      source: null,
      voices: [],
      hasSelection: false,
    };
  }

  get state(): SpeechState {
    return this.#state;
  }

  subscribe(listener: Listener): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  connect(): void {
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

  disconnect(): void {
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

  setReadOnInteraction(enabled: boolean): void {
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

  speakPage(root?: Element | null): boolean {
    const target = root ?? this.#doc.querySelector("main") ?? this.#doc.body;
    return this.#start(collectBlocks(target), "page");
  }

  speakElement(element: Element, source: SpeechSource = "element"): boolean {
    return this.#start(collectBlocks(element), source);
  }

  speakSelection(): boolean {
    const block = this.#selection ? blockFromRange(this.#selection) : null;
    return block ? this.#start([block], "selection") : false;
  }

  speakText(text: string, source: SpeechSource = "text"): boolean {
    const trimmed = text.replace(/\s+/g, " ").trim();
    if (!trimmed) return false;
    return this.#start([{ element: this.#doc.documentElement, text: trimmed, slices: [] }], source);
  }

  pause(): void {
    const synth = this.#synth();
    if (!synth || this.#state.status !== "speaking") return;
    synth.pause();
    this.#setState({ status: "paused" });
  }

  resume(): void {
    const synth = this.#synth();
    if (!synth || this.#state.status !== "paused") return;
    synth.resume();
    this.#setState({ status: "speaking" });
  }

  stop(): void {
    this.#run += 1;
    this.#queue = [];
    this.#index = 0;
    this.#clearHighlights();
    if (this.#state.status !== "idle" || this.#state.source !== null) {
      this.#synth()?.cancel();
      this.#setState({ status: "idle", source: null });
    }
  }

  #synth(): SpeechSynthesis | null {
    return this.#state.supported ? (this.#doc.defaultView?.speechSynthesis ?? null) : null;
  }

  #setState(partial: Partial<SpeechState>): void {
    this.#state = { ...this.#state, ...partial };
    for (const listener of this.#listeners) listener();
  }

  #start(blocks: TextBlock[], source: SpeechSource): boolean {
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

  #speakNext(run: number): void {
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
    const voice = settings.voiceURI
      ? synth.getVoices().find((candidate) => candidate.voiceURI === settings.voiceURI)
      : undefined;
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

  #highlightChunk(chunk: SpeechChunk, enabled: boolean): void {
    const range = rangeFor(chunk.block, chunk.start, chunk.end);
    if (range) this.#reveal(range);
    const api = highlightRegistry();
    if (!api) return;
    api.registry.delete(WORD_HIGHLIGHT);
    if (enabled && range) api.registry.set(READING_HIGHLIGHT, new api.Highlight(range));
    else api.registry.delete(READING_HIGHLIGHT);
  }

  #highlightWord(chunk: SpeechChunk, charIndex: number, charLength?: number): void {
    const api = highlightRegistry();
    if (!api) return;
    let length = charLength ?? 0;
    if (!length) length = /^\S+/.exec(chunk.text.slice(charIndex))?.[0].length ?? 0;
    if (!length) return;
    const start = chunk.start + charIndex;
    const range = rangeFor(chunk.block, start, Math.min(chunk.end, start + length));
    if (range) api.registry.set(WORD_HIGHLIGHT, new api.Highlight(range));
  }

  #clearHighlights(): void {
    const api = highlightRegistry();
    api?.registry.delete(READING_HIGHLIGHT);
    api?.registry.delete(WORD_HIGHLIGHT);
  }

  #reveal(range: Range): void {
    const view = this.#doc.defaultView;
    if (!view || typeof range.getBoundingClientRect !== "function") return;
    const rect = range.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;
    if (rect.top >= 0 && rect.bottom <= view.innerHeight) return;
    const reduceMotion =
      view.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true ||
      this.#doc.documentElement.dataset.a11yMotion !== undefined;
    view.scrollBy({ top: rect.top - view.innerHeight / 3, behavior: reduceMotion ? "auto" : "smooth" });
  }

  #loadVoices = (): void => {
    const synth = this.#synth();
    if (!synth) return;
    const voices = synth.getVoices().map((voice) => ({
      uri: voice.voiceURI,
      name: voice.name,
      lang: voice.lang,
      isDefault: voice.default,
    }));
    const unchanged =
      voices.length === this.#state.voices.length &&
      voices.every((voice, i) => voice.uri === this.#state.voices[i]?.uri);
    if (!unchanged) this.#setState({ voices });
  };

  #onPageHide = (): void => this.stop();

  #onPointerDown = (event: Event): void => {
    this.#pointerInToolbar = composedPathHitsToolbar(event);
  };

  #onSelectionChange = (): void => {
    const selection = this.#doc.getSelection();
    const hasText =
      selection !== null && !selection.isCollapsed && selection.rangeCount > 0 && selection.toString().trim() !== "";
    if (hasText) {
      this.#selection = selection.getRangeAt(0).cloneRange();
      if (!this.#state.hasSelection) this.#setState({ hasSelection: true });
    } else if (!this.#pointerInToolbar && this.#state.hasSelection) {
      this.#selection = null;
      this.#setState({ hasSelection: false });
    }
  };

  #onClick = (event: MouseEvent): void => {
    if (event.defaultPrevented || event.button !== 0 || composedPathHitsToolbar(event)) return;
    const target = event.composedPath().find((item): item is Element => item instanceof Element);
    if (!target || target.closest(INTERACTIVE_SELECTOR)) return;
    const selection = this.#doc.getSelection();
    if (selection && !selection.isCollapsed) return;
    this.speakElement(blockElementFor(target, this.#doc.body), "element");
  };

  #onFocusIn = (event: FocusEvent): void => {
    const target = event.target;
    if (!(target instanceof HTMLElement) || target.id === TOOLBAR_HOST_ID) return;
    if (!target.matches(INTERACTIVE_SELECTOR)) return;
    try {
      if (!target.matches(":focus-visible")) return;
    } catch {
      // `:focus-visible` unsupported - read it anyway.
    }
    clearTimeout(this.#focusTimer);
    this.#focusTimer = setTimeout(() => {
      const description = describeControl(target);
      if (description) this.speakText(description, "focus");
    }, FOCUS_READ_DELAY_MS);
  };
}
