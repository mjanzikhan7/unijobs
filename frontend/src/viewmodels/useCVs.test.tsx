import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useApplyCV, useCVs, useDeleteCV, useUploadCV } from "./useCVs";
import { urlOf } from "@/models/api/client";
import { queryKeys } from "@/models/queryKeys";
import { createTestStore, isInvalidated, paginate, seedQuery, storeWrapper, stubFetch } from "@/test-utils";
import type { CV } from "./useCVs";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const cv: CV = {
  id: 1,
  original_filename: "cv.pdf",
  content_type: "application/pdf",
  byte_size: 128_000,
  suggestions: null,
  applied_at: null,
  uploaded_at: "2026-09-01T09:00:00Z",
};

describe("useCVs", () => {
  it("fetches the CV list", async () => {
    stubFetch({ "/cvs/": paginate([cv]) });
    const { result } = renderHook(() => useCVs(), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.data?.results).toHaveLength(1));
  });
});

describe("useUploadCV", () => {
  it("sends the session cookie and the CSRF token, since it bypasses the shared helper", async () => {
    document.cookie = "csrftoken=csrf-test-value";
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(cv));
    const { result } = renderHook(() => useUploadCV(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync(new File(["content"], "cv.pdf"));
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    const init = options as RequestInit & { headers: Record<string, string> };
    expect(urlOf(url)).toContain("/cvs/upload/");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers["X-CSRFToken"]).toBe("csrf-test-value");
    expect(init.headers.Authorization).toBeUndefined();
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  it("surfaces the server's own error detail rather than a generic message", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(
      jsonResponse({ detail: "That file is not a CV we recognise." }, 422),
    );
    const { result } = renderHook(() => useUploadCV(), { wrapper: storeWrapper() });

    result.current.mutate(new File(["content"], "cv.pdf"));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("That file is not a CV we recognise.");
  });

  it("falls back to a plain message when the server sends no readable body", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(new Response("not json", { status: 500 }));
    const { result } = renderHook(() => useUploadCV(), { wrapper: storeWrapper() });

    result.current.mutate(new File(["content"], "cv.pdf"));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("That file could not be read.");
  });
});

describe("useApplyCV", () => {
  it("invalidates CVs, profiles and every job list — fitness was re-scored", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    const store = createTestStore();
    seedQuery(store, queryKeys.cvs());
    seedQuery(store, queryKeys.profiles());
    seedQuery(store, queryKeys.jobs("?page=2"));
    const { result } = renderHook(() => useApplyCV(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current.mutateAsync({ id: 1, body: { replace: true } });
    });

    expect(isInvalidated(store, queryKeys.cvs())).toBe(true);
    expect(isInvalidated(store, queryKeys.profiles())).toBe(true);
    expect(isInvalidated(store, queryKeys.jobs("?page=2"))).toBe(true);
  });
});

describe("useDeleteCV", () => {
  it("deletes the given CV", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(new Response(null, { status: 204 }));
    const { result } = renderHook(() => useDeleteCV(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync(9);
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/cvs/9/");
    expect((options as RequestInit).method).toBe("DELETE");
  });
});
