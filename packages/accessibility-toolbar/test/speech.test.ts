import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS, type TtsSettings } from "../src/core/settings";
import {
  SpeechController,
  blockFromRange,
  chunkBlocks,
  collectBlocks,
  describeControl,
  rangeFor,
} from "../src/core/speech";

function mount(markup: string): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = markup;
  document.body.appendChild(root);
  return root;
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

afterEach(() => {
  document.body.innerHTML = "";
  document.getSelection()?.removeAllRanges();
});

describe("collectBlocks", () => {
  it("keeps a heading and its paragraph apart, and inline markup inside one block", () => {
    const root = mount("<h2>Research Fellow</h2><p>Apply <strong>by Friday</strong> please.</p>");

    expect(collectBlocks(root).map((block) => block.text)).toEqual([
      "Research Fellow",
      "Apply by Friday please.",
    ]);
  });

  it("skips hidden, aria-hidden and script content", () => {
    const root = mount(
      "<p>Visible.</p><p hidden>Hidden.</p><p aria-hidden='true'>Decorative.</p><script>var x = 1;</script>",
    );

    expect(collectBlocks(root).map((block) => block.text)).toEqual(["Visible."]);
  });

  it("never reads the toolbar's own controls as page content", () => {
    const root = mount("<p>Page.</p><div id='unijobs-a11y-toolbar'><p>Toolbar.</p></div>");

    expect(collectBlocks(root).map((block) => block.text)).toEqual(["Page."]);
  });
});

describe("chunkBlocks", () => {
  it("splits sentences, each chunk an exact slice of its block's text", () => {
    const root = mount("<p>First sentence.  Second one!  Third?</p>");
    const chunks = chunkBlocks(collectBlocks(root), "en");

    expect(chunks.map((chunk) => chunk.text)).toEqual(["First sentence.", "Second one!", "Third?"]);
    for (const chunk of chunks) expect(chunk.block.text.slice(chunk.start, chunk.end)).toBe(chunk.text);
  });

  it("never produces a chunk longer than 200 characters", () => {
    const root = mount(`<p>${"word ".repeat(150)}</p>`);
    const chunks = chunkBlocks(collectBlocks(root), "en");

    expect(chunks.length).toBeGreaterThan(1);
    for (const chunk of chunks) expect(chunk.text.length).toBeLessThanOrEqual(200);
  });
});

describe("rangeFor", () => {
  it("maps block offsets back across several text nodes", () => {
    const root = mount("<p>Apply <strong>by Friday</strong> please.</p>");
    const [block] = collectBlocks(root);

    expect(rangeFor(block!, 6, 21)?.toString()).toBe("by Friday pleas");
  });
});

describe("blockFromRange", () => {
  it("reads a selection spanning two paragraphs with a space between them", () => {
    const root = mount("<p>One two.</p><p>Three four.</p>");
    const [first, second] = Array.from(root.querySelectorAll("p"), (p) => p.firstChild as Text);
    const range = document.createRange();
    range.setStart(first!, 4);
    range.setEnd(second!, 5);

    const block = blockFromRange(range);

    expect(block?.text).toBe("two. Three");
    expect(rangeFor(block!, 5, 10)?.toString()).toBe("Three");
  });
});

describe("describeControl", () => {
  it("names a pressed toggle button the way a screen reader would", () => {
    const root = mount("<button aria-pressed='true'>Save job</button>");

    expect(describeControl(root.querySelector("button")!)).toBe("Save job, button, pressed");
  });

  it("uses a checkbox's label and says whether it is checked", () => {
    const root = mount("<label for='remote'>Remote only</label><input id='remote' type='checkbox' checked>");

    expect(describeControl(root.querySelector("input")!)).toBe("Remote only, checkbox, checked");
  });
});

class FakeUtterance {
  text: string;
  rate = 1;
  pitch = 1;
  lang = "";
  voice: unknown = null;
  onstart: (() => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  onboundary: ((event: { name: string; charIndex: number; charLength?: number }) => void) | null = null;

  constructor(text: string) {
    this.text = text;
  }
}

function defineGlobal(name: string, value: unknown): void {
  for (const target of new Set<object>([window, globalThis])) {
    Object.defineProperty(target, name, { value, configurable: true, writable: true });
  }
}

function removeGlobal(name: string): void {
  for (const target of new Set<object>([window, globalThis])) Reflect.deleteProperty(target, name);
}

describe("SpeechController", () => {
  let spoken: FakeUtterance[];
  let synth: {
    speak: ReturnType<typeof vi.fn>;
    cancel: ReturnType<typeof vi.fn>;
    pause: ReturnType<typeof vi.fn>;
    resume: ReturnType<typeof vi.fn>;
    getVoices: () => unknown[];
    addEventListener: ReturnType<typeof vi.fn>;
    removeEventListener: ReturnType<typeof vi.fn>;
  };
  let tts: TtsSettings;
  let controller: SpeechController;

  beforeEach(() => {
    spoken = [];
    synth = {
      speak: vi.fn((utterance: FakeUtterance) => {
        spoken.push(utterance);
      }),
      cancel: vi.fn(),
      pause: vi.fn(),
      resume: vi.fn(),
      getVoices: () => [],
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    defineGlobal("speechSynthesis", synth);
    defineGlobal("SpeechSynthesisUtterance", FakeUtterance);
    tts = { ...DEFAULT_SETTINGS.tts };
    controller = new SpeechController({ getSettings: () => tts });
    controller.connect();
  });

  afterEach(() => {
    controller.disconnect();
    removeGlobal("speechSynthesis");
    removeGlobal("SpeechSynthesisUtterance");
  });

  it("says it is unsupported, and reads nothing, when the browser has no speech synthesis", () => {
    removeGlobal("speechSynthesis");
    const unsupported = new SpeechController({ getSettings: () => tts });
    mount("<main><p>Hello.</p></main>");

    expect(unsupported.state.supported).toBe(false);
    expect(unsupported.speakPage()).toBe(false);
  });

  it("reads a page one sentence at a time, in order, then goes idle", async () => {
    mount("<main><h1>Jobs</h1><p>First sentence. Second sentence.</p></main>");

    controller.speakPage();
    await flush();
    expect(controller.state.status).toBe("speaking");
    expect(spoken.map((u) => u.text)).toEqual(["Jobs"]);

    spoken[0]!.onend?.();
    spoken[1]!.onend?.();
    spoken[2]!.onend?.();

    expect(spoken.map((u) => u.text)).toEqual(["Jobs", "First sentence.", "Second sentence."]);
    expect(controller.state.status).toBe("idle");
  });

  it("stop() cancels and ignores a late end event from the reading it stopped", async () => {
    mount("<main><p>One. Two.</p></main>");
    controller.speakPage();
    await flush();

    controller.stop();
    spoken[0]!.onend?.();

    expect(synth.cancel).toHaveBeenCalled();
    expect(controller.state.status).toBe("idle");
    expect(spoken).toHaveLength(1);
  });

  it("tracks pause and resume", async () => {
    mount("<main><p>One.</p></main>");
    controller.speakPage();
    await flush();

    controller.pause();
    expect(controller.state.status).toBe("paused");
    controller.resume();
    expect(controller.state.status).toBe("speaking");
  });

  it("uses the reading speed at the time each sentence starts", async () => {
    mount("<main><p>One. Two.</p></main>");
    controller.speakPage();
    await flush();
    tts = { ...tts, rate: 1.6 };

    spoken[0]!.onend?.();

    expect(spoken[0]!.rate).toBe(1);
    expect(spoken[1]!.rate).toBe(1.6);
  });

  it("reads a clicked paragraph when click-to-read is on, but not a clicked button", async () => {
    const root = mount("<p>Hello there.</p><button>Save</button>");
    controller.setReadOnInteraction(true);

    root.querySelector("button")!.dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true }));
    await flush();
    expect(spoken).toHaveLength(0);

    root.querySelector("p")!.dispatchEvent(new MouseEvent("click", { bubbles: true, composed: true }));
    await flush();
    expect(spoken.map((u) => u.text)).toEqual(["Hello there."]);
  });

  it("still reads the selection after pressing the toolbar collapsed it", async () => {
    const root = mount("<p>Pick these words please.</p><div id='unijobs-a11y-toolbar'></div>");
    const text = root.querySelector("p")!.firstChild as Text;
    const range = document.createRange();
    range.setStart(text, 5);
    range.setEnd(text, 16);
    const selection = document.getSelection()!;
    selection.addRange(range);
    document.dispatchEvent(new Event("selectionchange"));
    expect(controller.state.hasSelection).toBe(true);

    root.querySelector("#unijobs-a11y-toolbar")!.dispatchEvent(new Event("pointerdown", { bubbles: true, composed: true }));
    selection.removeAllRanges();
    document.dispatchEvent(new Event("selectionchange"));

    expect(controller.state.hasSelection).toBe(true);
    expect(controller.speakSelection()).toBe(true);
    await flush();
    expect(spoken.map((u) => u.text)).toEqual(["these words"]);
  });
});
