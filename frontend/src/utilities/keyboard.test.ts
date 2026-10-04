import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { isTypingTarget, useShortcuts } from "./keyboard";
import type { Shortcut } from "./keyboard";

function press(key: string, target?: EventTarget): void {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
  if (target) {
    Object.defineProperty(event, "target", { value: target });
  }
  window.dispatchEvent(event);
}

function shortcut(key: string, handler: () => void, allowInInput = false): Shortcut {
  return { key, description: key, handler, allowInInput };
}

describe("useShortcuts", () => {
  it("fires the handler for its key", () => {
    const handler = vi.fn();
    renderHook(() => useShortcuts([shortcut("j", handler)]));

    press("j");

    expect(handler).toHaveBeenCalledOnce();
  });

  it("ignores keys nobody registered", () => {
    const handler = vi.fn();
    renderHook(() => useShortcuts([shortcut("j", handler)]));

    press("z");

    expect(handler).not.toHaveBeenCalled();
  });

  it("does not fire while the user is typing in a text field", () => {
    const handler = vi.fn();
    const input = document.createElement("input");
    renderHook(() => useShortcuts([shortcut("j", handler)]));

    press("j", input);

    expect(handler).not.toHaveBeenCalled();
  });

  it("does not fire while the user is typing in a textarea", () => {
    const handler = vi.fn();
    const textarea = document.createElement("textarea");
    renderHook(() => useShortcuts([shortcut("s", handler)]));

    press("s", textarea);

    expect(handler).not.toHaveBeenCalled();
  });

  it("fires an opted-in shortcut even while typing, so Escape still works", () => {
    const handler = vi.fn();
    const input = document.createElement("input");
    renderHook(() => useShortcuts([shortcut("Escape", handler, true)]));

    press("Escape", input);

    expect(handler).toHaveBeenCalledOnce();
  });

  it("never hijacks a browser or OS chord", () => {
    const handler = vi.fn();
    renderHook(() => useShortcuts([shortcut("s", handler)]));

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "s", metaKey: true }));

    expect(handler).not.toHaveBeenCalled();
  });

  it("stops listening once the component unmounts", () => {
    const handler = vi.fn();
    const { unmount } = renderHook(() => useShortcuts([shortcut("j", handler)]));

    unmount();
    press("j");

    expect(handler).not.toHaveBeenCalled();
  });

  it("can be disabled outright", () => {
    const handler = vi.fn();
    renderHook(() => useShortcuts([shortcut("j", handler)], false));

    press("j");

    expect(handler).not.toHaveBeenCalled();
  });

  it("fires only the first matching shortcut", () => {
    const first = vi.fn();
    const second = vi.fn();
    renderHook(() => useShortcuts([shortcut("j", first), shortcut("j", second)]));

    press("j");

    expect(second).not.toHaveBeenCalled();
  });
});

describe("isTypingTarget", () => {
  it.each(["input", "textarea", "select"])("treats a %s as somewhere you type", (tag) => {
    expect(isTypingTarget(document.createElement(tag))).toBe(true);
  });

  it("treats a plain element as somewhere you do not", () => {
    expect(isTypingTarget(document.createElement("div"))).toBe(false);
  });

  it("treats a contenteditable element as somewhere you type", () => {
    const element = document.createElement("div");
    element.contentEditable = "true";
    Object.defineProperty(element, "isContentEditable", { value: true });

    expect(isTypingTarget(element)).toBe(true);
  });

  it("copes with no target at all", () => {
    expect(isTypingTarget(null)).toBe(false);
  });
});
