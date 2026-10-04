import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createTestStore, isInvalidated, seedQuery, storeWrapper } from "@/test-utils";

import { useMutation } from "./useMutation";

describe("useMutation", () => {
  it("goes from idle to pending to success, and hands back the result", async () => {
    const { result } = renderHook(
      () => useMutation({ mutationFn: (name: string) => Promise.resolve(`hello ${name}`) }),
      { wrapper: storeWrapper() },
    );
    expect(result.current.isIdle).toBe(true);
    const onSuccess = vi.fn();

    act(() => result.current.mutate("amara", { onSuccess }));

    expect(result.current.isPending).toBe(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe("hello amara");
    expect(onSuccess).toHaveBeenCalledWith("hello amara", "amara");
  });

  it("invalidates the keys it names once the server accepts the change", async () => {
    const store = createTestStore();
    seedQuery(store, ["things", "list"]);
    seedQuery(store, ["others"]);
    const { result } = renderHook(
      () =>
        useMutation({
          mutationFn: (id: number) => Promise.resolve(id),
          invalidates: (_data, id) => [["things"], ["thing", id]],
        }),
      { wrapper: storeWrapper(store) },
    );

    await act(() => result.current.mutateAsync(3));

    expect(isInvalidated(store, ["things", "list"])).toBe(true);
    expect(isInvalidated(store, ["others"])).toBe(false);
  });

  it("reports a refusal, invalidates nothing, and clears on reset", async () => {
    const store = createTestStore();
    seedQuery(store, ["things"]);
    const { result } = renderHook(
      () =>
        useMutation({
          mutationFn: () => Promise.reject(new Error("refused")),
          invalidates: [["things"]],
        }),
      { wrapper: storeWrapper(store) },
    );
    const onError = vi.fn();

    act(() => result.current.mutate(undefined, { onError }));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("refused");
    expect(onError).toHaveBeenCalled();
    expect(isInvalidated(store, ["things"])).toBe(false);

    act(() => result.current.reset());

    expect(result.current.isIdle).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("rejects mutateAsync with the server's error", async () => {
    const { result } = renderHook(
      () => useMutation({ mutationFn: () => Promise.reject(new Error("refused")) }),
      { wrapper: storeWrapper() },
    );

    await act(async () => {
      await expect(result.current.mutateAsync()).rejects.toThrow("refused");
    });
  });

  it("shows the latest call, not a slower earlier one that finishes after it", async () => {
    let finishFirst!: (value: string) => void;
    const first = new Promise<string>((resolve) => {
      finishFirst = resolve;
    });
    const mutationFn = vi.fn().mockReturnValueOnce(first).mockResolvedValue("second");
    const { result } = renderHook(() => useMutation<string, number>({ mutationFn }), {
      wrapper: storeWrapper(),
    });

    act(() => result.current.mutate(1));
    act(() => result.current.mutate(2));
    await waitFor(() => expect(result.current.data).toBe("second"));

    await act(async () => {
      finishFirst("first");
      await first;
    });

    expect(result.current.data).toBe("second");
  });
});
