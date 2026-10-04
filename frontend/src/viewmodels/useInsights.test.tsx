import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCandidateInsights, useInstitutionInsights, useSearchCloud } from "./useInsights";
import { urlOf } from "@/models/api/client";
import { storeWrapper } from "@/test-utils";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("useCandidateInsights", () => {
  it("asks for the requested window", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ days: 30 }));
    const { result } = renderHook(() => useCandidateInsights(30), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/insights/candidates/?days=30");
  });
});

describe("useInstitutionInsights", () => {
  it("defaults the row limit to 500 — this table is meant to be the whole estate", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ days: 90 }));
    const { result } = renderHook(() => useInstitutionInsights(90), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/insights/institutions/?days=90&limit=500");
  });

  it("lets a caller override the limit", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ days: 90 }));
    const { result } = renderHook(() => useInstitutionInsights(90, 50), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("limit=50");
  });
});

describe("useSearchCloud", () => {
  it("asks for the requested window", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ days: 7 }));
    const { result } = renderHook(() => useSearchCloud(7), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/insights/search-cloud/?days=7");
  });
});
