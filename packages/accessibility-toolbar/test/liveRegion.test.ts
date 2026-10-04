import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createLiveAnnouncer } from "../src/react/liveRegion";

const polite = () => document.getElementById("unijobs-a11y-live-polite")!;

describe("createLiveAnnouncer", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date", "requestAnimationFrame"] });
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("mounts live regions without an ARIA role that would collide with the host's", () => {
    createLiveAnnouncer();

    expect(polite().getAttribute("aria-live")).toBe("polite");
    expect(polite().hasAttribute("role")).toBe(false);
  });

  it("coalesces rapid messages and announces the last one, not the first", () => {
    const { announce } = createLiveAnnouncer();

    announce("Text size 110%");
    vi.advanceTimersByTime(20);
    expect(polite().textContent).toBe("Text size 110%");

    announce("Text size 120%");
    announce("Text size 150%");
    vi.advanceTimersByTime(600);

    expect(polite().textContent).toBe("Text size 150%");
  });
});
