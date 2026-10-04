import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCancelCrawl, usePauseCrawl, useRestartCrawl, useResumeCrawl } from "./useCrawlControl";
import { urlOf } from "@/models/api/client";
import { storeWrapper } from "@/test-utils";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("usePauseCrawl", () => {
  it("posts to the run's pause action", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ id: 7, status: "PAUSED" }));
    const { result } = renderHook(() => usePauseCrawl(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync(7);
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/crawl-runs/7/pause/");
    expect((options as RequestInit).method).toBe("POST");
  });
});

describe("useResumeCrawl", () => {
  it("posts to the run's resume action", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ id: 7, status: "RUNNING" }));
    const { result } = renderHook(() => useResumeCrawl(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync(7);
    });

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/crawl-runs/7/resume/");
  });
});

describe("useCancelCrawl", () => {
  it("posts to the run's cancel action", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ id: 7, status: "CANCELLED" }));
    const { result } = renderHook(() => useCancelCrawl(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync(7);
    });

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/crawl-runs/7/cancel/");
  });
});

describe("useRestartCrawl", () => {
  it("posts the chosen scope in the body", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse({ id: 9, status: "RUNNING" }));
    const { result } = renderHook(() => useRestartCrawl(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync({ runId: 7, scope: "failures" });
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/crawl-runs/7/restart/");
    const body = JSON.parse((options as RequestInit).body as string) as { scope: string };
    expect(body.scope).toBe("failures");
  });

  it("returns the newly created run", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ id: 9, status: "RUNNING" }));
    const { result } = renderHook(() => useRestartCrawl(), { wrapper: storeWrapper() });

    result.current.mutate({ runId: 7, scope: "all" });

    await waitFor(() => expect(result.current.data?.id).toBe(9));
  });
});
