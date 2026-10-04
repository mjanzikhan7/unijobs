import { afterEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_SETTINGS } from "../src/core/settings";
import { createLocalStorageAdapter } from "../src/core/storage";

describe("createLocalStorageAdapter", () => {
  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("round-trips a write through read()", async () => {
    const adapter = createLocalStorageAdapter("test.key");
    await adapter.write({ ...DEFAULT_SETTINGS, fontScale: 1.6 });

    const read = await adapter.read();
    expect(read?.fontScale).toBe(1.6);
  });

  it("clear() removes the stored value", async () => {
    const adapter = createLocalStorageAdapter("test.key");
    await adapter.write(DEFAULT_SETTINGS);
    await adapter.clear();

    expect(await adapter.read()).toBeNull();
  });

  it("read() returns null instead of throwing on malformed JSON", async () => {
    window.localStorage.setItem("test.key", "{not json");
    const adapter = createLocalStorageAdapter("test.key");

    await expect(adapter.read()).resolves.toBeNull();
  });

  it("write() swallows a quota/private-mode error", async () => {
    const adapter = createLocalStorageAdapter("test.key");
    vi.spyOn(window.localStorage.__proto__, "setItem").mockImplementation(() => {
      throw new DOMException("QuotaExceededError");
    });

    await expect(adapter.write(DEFAULT_SETTINGS)).resolves.toBeUndefined();
  });
});
