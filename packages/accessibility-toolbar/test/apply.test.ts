import { beforeEach, describe, expect, it } from "vitest";

import { applySettings, clearSettings } from "../src/core/apply";
import { DEFAULT_SETTINGS, type A11ySettings } from "../src/core/settings";

function settings(overrides: Partial<A11ySettings>): A11ySettings {
  return { ...DEFAULT_SETTINGS, ...overrides } as A11ySettings;
}

describe("applySettings / clearSettings", () => {
  let root: HTMLElement;

  beforeEach(() => {
    root = document.createElement("div");
    document.getElementById("unijobs-a11y-daltonize-defs")?.remove();
  });

  it("writes nothing at all for default settings", () => {
    applySettings(settings({}), { root });

    expect(Object.keys(root.dataset)).toEqual([]);
    expect(root.getAttribute("style") ?? "").toBe("");
  });

  it("only marks spacing that differs from the default, in em", () => {
    applySettings(settings({ letterSpacing: 0.12 }), { root });

    expect(root.dataset.a11yLetterSpacing).toBe("true");
    expect(root.style.getPropertyValue("--a11y-letter-spacing")).toBe("0.12em");
    expect(root.dataset.a11yLineHeight).toBeUndefined();
    expect(root.dataset.a11yWordSpacing).toBeUndefined();
  });

  it("marks and scales text size together", () => {
    applySettings(settings({ fontScale: 1.5 }), { root });

    expect(root.dataset.a11yTextScale).toBe("true");
    expect(root.style.getPropertyValue("--a11y-font-scale")).toBe("1.5");
  });

  it("marks click-to-read while read aloud on interaction is on", () => {
    applySettings(settings({ tts: { ...DEFAULT_SETTINGS.tts, enabled: true } }), { root });

    expect(root.dataset.a11yReadOnClick).toBe("true");
  });

  it("gates custom colours behind a single flag", () => {
    applySettings(settings({ customColors: { background: "#000000" } }), { root });
    expect(root.dataset.a11yCustomColors).toBe("true");
    expect(root.style.getPropertyValue("--a11y-custom-bg")).toBe("#000000");

    applySettings(settings({ customColors: null }), { root });
    expect(root.dataset.a11yCustomColors).toBeUndefined();
    expect(root.style.getPropertyValue("--a11y-custom-bg")).toBe("");
  });

  it("injects the daltonisation filters once, only when a colour-vision theme needs them", () => {
    applySettings(settings({ theme: "monochrome" }), { root });
    expect(document.getElementById("unijobs-a11y-daltonize-defs")).toBeNull();

    applySettings(settings({ theme: "deuteranopia" }), { root });
    applySettings(settings({ theme: "protanopia" }), { root });

    expect(document.querySelectorAll("#unijobs-a11y-daltonize-defs")).toHaveLength(1);
    expect(document.getElementById("unijobs-a11y-daltonize-deuteranopia")).not.toBeNull();
  });

  it("clearSettings leaves no attribute and no empty style attribute behind", () => {
    applySettings(
      settings({
        theme: "invert",
        fontScale: 1.7,
        wordSpacing: 0.2,
        highlight: { links: true, headings: true, focus: true, hover: true },
      }),
      { root },
    );

    clearSettings({ root });

    expect(Object.keys(root.dataset)).toEqual([]);
    expect(root.hasAttribute("style")).toBe(false);
  });
});
