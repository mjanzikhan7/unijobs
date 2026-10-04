import { select } from "redux-saga/effects";

import { request } from "@/models/api/client";
import type { Job, Paginated, SavedJob } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { cancelQueries, invalidateQueries, setQueryData } from "@/store/queries/effects";
import type { QueryKey } from "@/store/queries/queryKey";
import { selectQueriesData } from "@/store/queries/slice";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";
import type { Saga } from "@/store/saga";

export function useSavedJobs(): UseQueryResult<Paginated<SavedJob>> {
  return useQuery({
    queryKey: queryKeys.savedJobs(),
    queryFn: () => request<Paginated<SavedJob>>("/saved-jobs/"),
  });
}

type JobListSnapshot = [QueryKey, Paginated<Job> | undefined][];

function* refreshSavedState(): Saga {
  yield invalidateQueries(["jobs"]);
  yield invalidateQueries(queryKeys.savedJobs());
}

export function useSaveJob(): UseMutationResult<SavedJob, Error, number> {
  return useMutation({
    mutationFn: (jobId: number) =>
      request<SavedJob>("/saved-jobs/", { method: "POST", body: { job: jobId } }),
    onMutate: function* (jobId): Saga<JobListSnapshot> {
      yield cancelQueries(["jobs"]);
      const snapshot = (yield select(selectQueriesData, ["jobs"])) as JobListSnapshot;
      for (const [key, data] of snapshot) {
        if (!data?.results) continue;
        yield setQueryData(key, {
          ...data,
          results: data.results.map((job) =>
            job.id === jobId ? { ...job, is_saved: true } : job,
          ),
        });
      }
      return snapshot;
    },
    onError: function* (_error, _jobId, snapshot): Saga {
      for (const [key, data] of snapshot ?? []) yield setQueryData(key, data);
    },
    onSettled: refreshSavedState,
  });
}

export function useUnsaveJob(): UseMutationResult<void, Error, number> {
  return useMutation({
    mutationFn: (savedId: number) => request<void>(`/saved-jobs/${savedId}/`, { method: "DELETE" }),
    onSettled: refreshSavedState,
  });
}
