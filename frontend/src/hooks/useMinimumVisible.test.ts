import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useMinimumVisible } from "./useMinimumVisible";

async function tick(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("useMinimumVisible", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("is visible immediately once active", () => {
    const { result } = renderHook(() => useMinimumVisible(true, 400));

    expect(result.current).toBe(true);
  });

  it("is never visible if it was never activated", () => {
    const { result } = renderHook(() => useMinimumVisible(false, 400));

    expect(result.current).toBe(false);
  });

  it("stays visible past the moment activity stops, until the minimum has elapsed", async () => {
    const { result, rerender } = renderHook(({ active }) => useMinimumVisible(active, 400), {
      initialProps: { active: true },
    });

    await tick(30);
    rerender({ active: false });

    expect(result.current).toBe(true);

    await tick(369);
    expect(result.current).toBe(true);

    await tick(1);
    expect(result.current).toBe(false);
  });

  it("hides immediately once inactive, if the minimum had already elapsed", async () => {
    const { result, rerender } = renderHook(({ active }) => useMinimumVisible(active, 400), {
      initialProps: { active: true },
    });

    await tick(500);
    rerender({ active: false });

    expect(result.current).toBe(false);
  });

  it("restarts the minimum window on a second activation", async () => {
    const { result, rerender } = renderHook(({ active }) => useMinimumVisible(active, 400), {
      initialProps: { active: true },
    });

    await tick(500);
    rerender({ active: false });
    expect(result.current).toBe(false);

    rerender({ active: true });
    await tick(300);
    rerender({ active: false });

    expect(result.current).toBe(true);

    await tick(100);
    expect(result.current).toBe(false);
  });
});
