import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { A11yEngine } from "../src/core/engine";
import { DEFAULT_SETTINGS } from "../src/core/settings";
import { createNoopStorageAdapter, type StorageAdapter } from "../src/core/storage";

const html = document.documentElement;

function a11yAttributes(): string[] {
  return Object.keys(html.dataset).filter((key) => key.startsWith("a11y"));
}

function storageReturning(stored: unknown, write = vi.fn(async () => {})): StorageAdapter {
  return {
    read: async () => stored as never,
    write,
    clear: async () => {},
  };
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

describe("A11yEngine", () => {
  let engine: A11yEngine | undefined;

  beforeEach(() => {
    html.removeAttribute("style");
    for (const key of a11yAttributes()) delete html.dataset[key];
  });

  afterEach(() => {
    engine?.destroy();
    engine = undefined;
  });

  async function start(storage: StorageAdapter = createNoopStorageAdapter()): Promise<A11yEngine> {
    engine = new A11yEngine({ storage, persistDebounceMs: 10 });
    await engine.init();
    return engine;
  }

  it("leaves the page untouched at default settings", async () => {
    await start();

    expect(a11yAttributes()).toEqual([]);
    expect(html.style.getPropertyValue("--a11y-font-scale")).toBe("");
  });

  it("marks text scaling on the root only while the size differs from 100%", async () => {
    const e = await start();

    e.set("fontScale", 1.4);
    expect(html.dataset.a11yTextScale).toBe("true");
    expect(html.style.getPropertyValue("--a11y-font-scale")).toBe("1.4");

    e.set("fontScale", 1);
    expect(html.dataset.a11yTextScale).toBeUndefined();
    expect(html.style.getPropertyValue("--a11y-font-scale")).toBe("");
  });

  it("changing a setting by hand clears the active profile marker", async () => {
    const e = await start();

    e.applyProfile("dyslexia");
    e.set("fontScale", 2);

    expect(e.settings.profile).toBeNull();
    expect(e.settings.fontFamily).toBe("dyslexic");
  });

  it("switching profile replaces the previous profile's changes rather than stacking them", async () => {
    const e = await start();

    e.applyProfile("low-vision");
    e.applyProfile("dyslexia");

    expect(e.settings.profile).toBe("dyslexia");
    expect(e.settings.fontFamily).toBe("dyslexic");
    expect(e.settings.theme).toBe("default");
    expect(e.settings.fontScale).toBe(1);
  });

  it("choosing the active profile again turns it off and gives back the earlier settings", async () => {
    const e = await start();
    e.set("fontScale", 1.2);

    e.applyProfile("low-vision");
    expect(e.settings.fontScale).toBe(1.5);

    e.applyProfile("low-vision");
    expect(e.settings.profile).toBeNull();
    expect(e.settings.fontScale).toBe(1.2);
    expect(e.settings.theme).toBe("default");
  });

  it("clearProfile restores the settings from before the profile, even after switching profiles", async () => {
    const e = await start();
    e.set("theme", "contrast-light");

    e.applyProfile("low-vision");
    e.applyProfile("older-users");
    e.clearProfile();

    expect(e.settings.profile).toBeNull();
    expect(e.settings.theme).toBe("contrast-light");
    expect(e.settings.fontScale).toBe(1);
  });

  it("clearProfile after a reload reverts only the keys that profile changed", async () => {
    const e = await start(
      storageReturning({
        ...DEFAULT_SETTINGS,
        profile: "dyslexia",
        fontFamily: "dyslexic",
        letterSpacing: 0.08,
        wordSpacing: 0.16,
        lineHeight: 1.8,
        contentWidth: "narrow",
        theme: "contrast-dark",
      }),
    );

    e.clearProfile();

    expect(e.settings.fontFamily).toBe("default");
    expect(e.settings.lineHeight).toBe(1.5);
    expect(e.settings.theme).toBe("contrast-dark");
  });

  it("resetKeys reverts one section and leaves the others alone", async () => {
    const e = await start();
    e.set("theme", "contrast-dark");
    e.set("fontScale", 1.3);

    e.resetKeys(["theme", "customColors"]);

    expect(e.settings.theme).toBe("default");
    expect(e.settings.fontScale).toBe(1.3);
  });

  it("persists a change once the debounce has passed", async () => {
    const write = vi.fn(async () => {});
    const e = await start(storageReturning(null, write));

    e.set("fontScale", 1.1);
    e.set("fontScale", 1.2);
    await sleep(30);

    expect(write).toHaveBeenCalledTimes(1);
    expect(write.mock.calls[0]).toEqual([expect.objectContaining({ fontScale: 1.2 })]);
  });

  it("reset() wins over a save still waiting on its debounce", async () => {
    const write = vi.fn(async () => {});
    const e = await start(storageReturning(null, write));

    e.set("fontScale", 1.4);
    e.reset();
    await sleep(30);

    expect(write).not.toHaveBeenCalled();
    expect(e.settings.fontScale).toBe(1);
  });

  it("ignores corrupted stored values instead of putting them on the page", async () => {
    const e = await start(
      storageReturning({ fontScale: "huge", theme: "neon", lineHeight: 99, highlight: { links: "yes" } }),
    );

    expect(e.settings.fontScale).toBe(1);
    expect(e.settings.theme).toBe("default");
    expect(e.settings.lineHeight).toBe(2.5);
    expect(e.settings.highlight.links).toBe(false);
  });

  it("discards settings written by a newer version of the package", async () => {
    const e = await start(storageReturning({ version: 99, theme: "contrast-dark" }));

    expect(e.settings.theme).toBe("default");
  });

  it("never throws when storage cannot be read", async () => {
    engine = new A11yEngine({
      storage: {
        read: () => Promise.reject(new Error("blocked")),
        write: async () => {},
        clear: async () => {},
      },
    });

    await expect(engine.init()).resolves.toBeUndefined();
    expect(engine.settings.theme).toBe("default");
  });

  it("notifies subscribers of each change and stops after unsubscribing", async () => {
    const e = await start();
    const listener = vi.fn();
    const unsubscribe = e.subscribe(listener);

    e.set("motion", "off");
    unsubscribe();
    e.set("motion", "default");

    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("destroy() removes every attribute and property it set", async () => {
    const e = await start();
    e.set("theme", "contrast-dark");
    e.set("fontScale", 1.8);
    e.set("letterSpacing", 0.1);
    e.set("highlight", { links: true, headings: true, focus: false, hover: false });

    e.destroy();
    engine = undefined;

    expect(a11yAttributes()).toEqual([]);
    expect(html.hasAttribute("style")).toBe(false);
  });
});
