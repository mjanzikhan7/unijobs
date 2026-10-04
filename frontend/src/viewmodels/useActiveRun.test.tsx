import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useActiveRun } from "./useActiveRun";
import { storeWrapper } from "@/test-utils";

function runAt(done: number, total: number, status = "RUNNING") {
  return {
    run: {
      id: 1,
      status,
      institutions_done: done,
      institutions_total: total,
      jobs_created: done * 3,
      started_at: "2026-08-24T09:00:00Z",
    },
  };
}

async function tick(ms = 5_000): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("useActiveRun", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("reports the run in progress", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(runAt(2, 40)));

    const { result } = renderHook(() => useActiveRun(), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.data?.run?.institutions_done).toBe(2));
  });

  it("updates incrementally as the run progresses", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValueOnce(jsonResponse(runAt(2, 40)))
      .mockResolvedValue(jsonResponse(runAt(9, 40)));

    const { result } = renderHook(() => useActiveRun(), { wrapper: storeWrapper() });
    await waitFor(() => expect(result.current.data?.run?.institutions_done).toBe(2));

    await tick();

    await waitFor(() => expect(result.current.data?.run?.institutions_done).toBe(9));
    expect(fetchSpy.mock.calls.length).toBeGreaterThan(1);
  });

  it("keeps polling after a failed request rather than giving up", async () => {
    vi.spyOn(globalThis, "fetch").mockClear()
      .mockResolvedValueOnce(jsonResponse(runAt(3, 40)))
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValue(jsonResponse(runAt(11, 40)));

    const { result } = renderHook(() => useActiveRun(), { wrapper: storeWrapper() });
    await waitFor(() => expect(result.current.data?.run?.institutions_done).toBe(3));

    await tick();
    await tick();

    await waitFor(() => expect(result.current.data?.run?.institutions_done).toBe(11));
  });

  it("stops polling once no run is active", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ run: null }));

    const { result } = renderHook(() => useActiveRun(), { wrapper: storeWrapper() });
    await waitFor(() => expect(result.current.data?.run).toBeNull());

    const afterFirst = fetchSpy.mock.calls.length;
    await tick(30_000);

    expect(fetchSpy.mock.calls.length).toBe(afterFirst);
  });

  it("stops polling when the run finishes", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValueOnce(jsonResponse(runAt(40, 40)))
      .mockResolvedValue(jsonResponse({ run: null }));

    const { result } = renderHook(() => useActiveRun(), { wrapper: storeWrapper() });
    await waitFor(() => expect(result.current.data?.run?.institutions_done).toBe(40));

    await tick();
    await waitFor(() => expect(result.current.data?.run).toBeNull());

    const settled = fetchSpy.mock.calls.length;
    await tick(30_000);

    expect(fetchSpy.mock.calls.length).toBe(settled);
  });
});
