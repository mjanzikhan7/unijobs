import { act, renderHook, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createAppStore } from "@/store/store";
import { createTestStore, isInvalidated, seedQuery, storeWrapper } from "@/test-utils";

import { queriesInvalidated } from "./slice";
import { useQuery } from "./useQuery";

const KEY = ["things", "list"] as const;

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("useQuery", () => {
  it("reports loading on the very first render, then the answer", async () => {
    const queryFn = vi.fn().mockResolvedValue("answer");
    const { result } = renderHook(() => useQuery({ queryKey: KEY, queryFn }), {
      wrapper: storeWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.data).toBe("answer"));
    expect(result.current.isSuccess).toBe(true);
    expect(result.current.isFetching).toBe(false);
  });

  it("makes one request when two hooks ask for the same key at once", async () => {
    const queryFn = vi.fn().mockResolvedValue("answer");
    const { result } = renderHook(
      () => [useQuery({ queryKey: KEY, queryFn }), useQuery({ queryKey: KEY, queryFn })] as const,
      { wrapper: storeWrapper() },
    );

    await waitFor(() => expect(result.current[1].data).toBe("answer"));
    expect(result.current[0].data).toBe("answer");
    expect(queryFn).toHaveBeenCalledTimes(1);
  });

  it("still makes one request under StrictMode, which mounts every effect twice", async () => {
    const queryFn = vi.fn().mockResolvedValue("answer");
    const Store = storeWrapper();
    const { result } = renderHook(() => useQuery({ queryKey: KEY, queryFn }), {
      wrapper: ({ children }) => (
        <StrictMode>
          <Store>{children}</Store>
        </StrictMode>
      ),
    });

    await waitFor(() => expect(result.current.data).toBe("answer"));
    expect(queryFn).toHaveBeenCalledTimes(1);
  });

  it("does not fetch while disabled, and does once enabled", async () => {
    const queryFn = vi.fn().mockResolvedValue("answer");
    const { result, rerender } = renderHook(
      ({ enabled }) => useQuery({ queryKey: KEY, queryFn, enabled }),
      { wrapper: storeWrapper(), initialProps: { enabled: false } },
    );

    expect(result.current.isLoading).toBe(false);
    expect(queryFn).not.toHaveBeenCalled();

    rerender({ enabled: true });

    await waitFor(() => expect(result.current.data).toBe("answer"));
  });

  it("trusts a fresh answer instead of fetching it again", () => {
    const store = createAppStore({ staleTime: 60_000 });
    seedQuery(store, KEY, "cached");
    const queryFn = vi.fn().mockResolvedValue("new");

    const { result } = renderHook(() => useQuery({ queryKey: KEY, queryFn }), {
      wrapper: storeWrapper(store),
    });

    expect(result.current.data).toBe("cached");
    expect(queryFn).not.toHaveBeenCalled();
  });

  it("refetches a query on screen when it is invalidated", async () => {
    const store = createTestStore();
    const queryFn = vi.fn().mockResolvedValueOnce("before").mockResolvedValue("after");
    const { result } = renderHook(() => useQuery({ queryKey: KEY, queryFn }), {
      wrapper: storeWrapper(store),
    });
    await waitFor(() => expect(result.current.data).toBe("before"));

    act(() => {
      store.dispatch(queriesInvalidated({ key: ["things"] }));
    });

    await waitFor(() => expect(result.current.data).toBe("after"));
    expect(isInvalidated(store, KEY)).toBe(false);
  });

  it("throws away a request that was already in flight when the data changed", async () => {
    const store = createTestStore();
    const slow = deferred<string>();
    const queryFn = vi.fn().mockReturnValueOnce(slow.promise).mockResolvedValue("after");
    const { result } = renderHook(() => useQuery({ queryKey: KEY, queryFn }), {
      wrapper: storeWrapper(store),
    });
    await waitFor(() => expect(queryFn).toHaveBeenCalledTimes(1));

    act(() => {
      store.dispatch(queriesInvalidated({ key: KEY }));
    });
    await waitFor(() => expect(result.current.data).toBe("after"));

    await act(async () => {
      slow.resolve("before");
      await slow.promise;
    });

    expect(result.current.data).toBe("after");
  });

  it("only marks a query nobody is showing, and fetches nothing", () => {
    const store = createTestStore();
    seedQuery(store, KEY, "cached");

    store.dispatch(queriesInvalidated({ key: ["things"] }));

    expect(isInvalidated(store, KEY)).toBe(true);
  });

  it("retries as the policy allows, then reports the error", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const store = createAppStore({ retry: (failureCount) => failureCount < 1, gcTime: 0 });
    const queryFn = vi.fn().mockRejectedValue(new Error("server down"));
    const { result } = renderHook(() => useQuery({ queryKey: KEY, queryFn }), {
      wrapper: storeWrapper(store),
    });

    await waitFor(() => expect(result.current.failureCount).toBe(1));
    expect(result.current.isError).toBe(false);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("server down");
    expect(queryFn).toHaveBeenCalledTimes(2);
  });

  it("keeps the last good answer when a refresh fails, and recovers on retry", async () => {
    const queryFn = vi
      .fn()
      .mockResolvedValueOnce("good")
      .mockRejectedValueOnce(new Error("blip"))
      .mockResolvedValue("better");
    const { result } = renderHook(() => useQuery({ queryKey: KEY, queryFn }), {
      wrapper: storeWrapper(),
    });
    await waitFor(() => expect(result.current.data).toBe("good"));

    await act(() => result.current.refetch());

    expect(result.current.isError).toBe(true);
    expect(result.current.data).toBe("good");

    await act(() => result.current.refetch());

    expect(result.current.isError).toBe(false);
    expect(result.current.data).toBe("better");
  });

  it("shows the previous key's answer as a placeholder while the next one loads", async () => {
    const next = deferred<string>();
    const queryFn = vi.fn().mockResolvedValueOnce("page 1").mockReturnValue(next.promise);
    const { result, rerender } = renderHook(
      ({ page }) =>
        useQuery({
          queryKey: ["things", page],
          queryFn,
          placeholderData: (previous: string | undefined) => previous,
        }),
      { wrapper: storeWrapper(), initialProps: { page: 1 } },
    );
    await waitFor(() => expect(result.current.data).toBe("page 1"));

    rerender({ page: 2 });

    await waitFor(() => expect(result.current.isPlaceholderData).toBe(true));
    expect(result.current.data).toBe("page 1");
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(true);

    await act(async () => {
      next.resolve("page 2");
      await next.promise;
    });

    await waitFor(() => expect(result.current.data).toBe("page 2"));
    expect(result.current.isPlaceholderData).toBe(false);
  });
});
