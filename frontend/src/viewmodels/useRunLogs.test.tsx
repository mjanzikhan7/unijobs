import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useRunLogs } from "./useRunLogs";
import { urlOf } from "@/models/api/client";
import { storeWrapper } from "@/test-utils";

function entry(id: number, message: string) {
  return { id, level: "INFO", message, extra: {}, institution: null, institution_name: null, created_at: "2026-08-24T09:00:00Z" };
}

async function tick(ms = 3_000): Promise<void> {
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

describe("useRunLogs", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("does nothing while there is no run to watch", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear();

    const { result } = renderHook(() => useRunLogs(null), { wrapper: storeWrapper() });

    expect(result.current.entries).toEqual([]);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows the first poll's lines", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(
      jsonResponse([entry(1, "started"), entry(2, "crawled Bath")]),
    );

    const { result } = renderHook(() => useRunLogs(7), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.entries).toHaveLength(2));
    expect(result.current.entries.map((e) => e.message)).toEqual(["started", "crawled Bath"]);
  });

  it("appends new lines rather than replacing what it already has", async () => {
    vi.spyOn(globalThis, "fetch").mockClear()
      .mockResolvedValueOnce(jsonResponse([entry(1, "started")]))
      .mockResolvedValue(jsonResponse([entry(2, "crawled Bath")]));

    const { result } = renderHook(() => useRunLogs(7), { wrapper: storeWrapper() });
    await waitFor(() => expect(result.current.entries).toHaveLength(1));

    await tick();

    await waitFor(() => expect(result.current.entries).toHaveLength(2));
    expect(result.current.entries.map((e) => e.message)).toEqual(["started", "crawled Bath"]);
  });

  it("asks only for what is new, not the whole history, on every poll", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValueOnce(jsonResponse([entry(1, "started"), entry(2, "crawled Bath")]))
      .mockResolvedValue(jsonResponse([]));

    const { result } = renderHook(() => useRunLogs(7), { wrapper: storeWrapper() });
    await waitFor(() => expect(result.current.entries).toHaveLength(2));

    await tick();

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
    const secondCallUrl = urlOf(fetchSpy.mock.calls[1]![0]);
    expect(secondCallUrl).toContain("after=2");
  });

  it("does not grow when a poll comes back empty", async () => {
    vi.spyOn(globalThis, "fetch").mockClear()
      .mockResolvedValueOnce(jsonResponse([entry(1, "started")]))
      .mockResolvedValue(jsonResponse([]));

    const { result } = renderHook(() => useRunLogs(7), { wrapper: storeWrapper() });
    await waitFor(() => expect(result.current.entries).toHaveLength(1));

    await tick();
    await tick();

    expect(result.current.entries).toHaveLength(1);
  });

  it("starts over when the run id changes", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse([entry(1, "started")]));

    const { result, rerender } = renderHook(({ id }) => useRunLogs(id), {
      wrapper: storeWrapper(),
      initialProps: { id: 7 },
    });
    await waitFor(() => expect(result.current.entries).toHaveLength(1));

    rerender({ id: 8 });

    expect(result.current.entries).toEqual([]);
  });
});
