import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useJobs } from "./useJobs";
import { useSaveJob, useUnsaveJob } from "./useSavedJobs";
import { urlOf } from "@/models/api/client";
import { queryKeys } from "@/models/queryKeys";
import {
  createTestStore,
  isInvalidated,
  makeJob,
  paginate,
  seedQuery,
  storeWrapper,
} from "@/test-utils";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function serve(list: unknown) {
  let answerSave!: (response: Response) => void;
  const save = new Promise<Response>((resolve) => {
    answerSave = resolve;
  });
  vi.spyOn(globalThis, "fetch").mockClear().mockImplementation((input, init) => {
    if (urlOf(input).includes("/saved-jobs/") && init?.method === "POST") return save;
    return Promise.resolve(jsonResponse(list));
  });
  return { answerSave, save };
}

describe("useSaveJob", () => {
  it("marks the job as saved before the server has answered", async () => {
    const { answerSave, save } = serve(paginate([makeJob({ id: 7 }), makeJob({ id: 8 })]));
    const { result } = renderHook(() => ({ jobs: useJobs(""), saveJob: useSaveJob() }), {
      wrapper: storeWrapper(),
    });
    await waitFor(() => expect(result.current.jobs.data?.results).toHaveLength(2));

    act(() => result.current.saveJob.mutate(7));

    await waitFor(() => expect(result.current.jobs.data?.results[0]?.is_saved).toBe(true));
    expect(result.current.jobs.data?.results[1]?.is_saved).toBe(false);
    expect(result.current.saveJob.isPending).toBe(true);

    await act(async () => {
      answerSave(jsonResponse({ id: 1, job: 7 }, 201));
      await save;
    });
    await waitFor(() => expect(result.current.saveJob.isSuccess).toBe(true));
  });

  it("puts the list back when the server refuses", async () => {
    const { answerSave, save } = serve(paginate([makeJob({ id: 7 })]));
    const { result } = renderHook(() => ({ jobs: useJobs(""), saveJob: useSaveJob() }), {
      wrapper: storeWrapper(),
    });
    await waitFor(() => expect(result.current.jobs.data?.results).toHaveLength(1));

    act(() => result.current.saveJob.mutate(7));
    await waitFor(() => expect(result.current.jobs.data?.results[0]?.is_saved).toBe(true));

    await act(async () => {
      answerSave(jsonResponse({ detail: "Not allowed." }, 403));
      await save;
    });

    await waitFor(() => expect(result.current.saveJob.isError).toBe(true));
    await waitFor(() => expect(result.current.jobs.data?.results[0]?.is_saved).toBe(false));
  });
});

describe("useUnsaveJob", () => {
  it("deletes the saved row and marks the lists it appears in as stale", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(new Response(null, { status: 204 }));
    const store = createTestStore();
    seedQuery(store, queryKeys.savedJobs());
    seedQuery(store, queryKeys.jobs(""));
    const { result } = renderHook(() => useUnsaveJob(), { wrapper: storeWrapper(store) });

    await act(() => result.current.mutateAsync(5));

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/saved-jobs/5/");
    expect((options as RequestInit).method).toBe("DELETE");
    expect(isInvalidated(store, queryKeys.savedJobs())).toBe(true);
    expect(isInvalidated(store, queryKeys.jobs(""))).toBe(true);
  });
});
