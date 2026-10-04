import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCreateRuleset, useRescreen, useRulesets } from "./useRulesets";
import { urlOf } from "@/models/api/client";
import { queryKeys } from "@/models/queryKeys";
import { createTestStore, isInvalidated, paginate, seedQuery, storeWrapper, stubFetch } from "@/test-utils";
import type { Ruleset } from "@/models/api/types";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("useRulesets", () => {
  it("fetches the version list", async () => {
    const ruleset = { id: 4, version: 4, is_active: true } as unknown as Ruleset;
    stubFetch({ "/rulesets/": paginate([ruleset]) });
    const { result } = renderHook(() => useRulesets(), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.data?.results).toHaveLength(1));
  });
});

describe("useCreateRuleset", () => {
  it("POSTs a new version rather than patching the one in force", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse({ id: 5, version: 5 }));
    const { result } = renderHook(() => useCreateRuleset(), {
      wrapper: storeWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ standard_general_threshold: 39000 });
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/rulesets/");
    expect((options as RequestInit).method).toBe("POST");
  });

  it("invalidates the ruleset list so the new version and its 'in force' flag show up", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ id: 5 }));
    const store = createTestStore();
    seedQuery(store, queryKeys.rulesets());
    const { result } = renderHook(() => useCreateRuleset(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current.mutateAsync({});
    });

    expect(isInvalidated(store, queryKeys.rulesets())).toBe(true);
  });
});

describe("useRescreen", () => {
  it("posts to the given ruleset's rescreen action and returns the counts", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ screened: 2106, changed: 48 }));
    const { result } = renderHook(() => useRescreen(), { wrapper: storeWrapper() });

    result.current.mutate(4);

    await waitFor(() => expect(result.current.data?.changed).toBe(48));
  });

  it("invalidates every job list, since verdicts may have changed", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ screened: 0, changed: 0 }));
    const store = createTestStore();
    seedQuery(store, queryKeys.jobs(""));
    seedQuery(store, queryKeys.job(12));
    const { result } = renderHook(() => useRescreen(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current.mutateAsync(4);
    });

    expect(isInvalidated(store, queryKeys.jobs(""))).toBe(true);
    expect(isInvalidated(store, queryKeys.job(12))).toBe(true);
  });
});
