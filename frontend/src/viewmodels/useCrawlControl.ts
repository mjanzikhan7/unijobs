import { request } from "@/models/api/client";
import type { CrawlRun, RestartScope } from "@/models/api/types";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";

function useRunControl(
  action: "pause" | "resume" | "cancel",
): UseMutationResult<CrawlRun, Error, number> {
  return useMutation({
    mutationFn: (runId: number) =>
      request<CrawlRun>(`/crawl-runs/${runId}/${action}/`, { method: "POST" }),
    invalidates: [["crawl-runs"]],
  });
}

export function usePauseCrawl(): UseMutationResult<CrawlRun, Error, number> {
  return useRunControl("pause");
}

export function useResumeCrawl(): UseMutationResult<CrawlRun, Error, number> {
  return useRunControl("resume");
}

export function useCancelCrawl(): UseMutationResult<CrawlRun, Error, number> {
  return useRunControl("cancel");
}

export function useRestartCrawl(): UseMutationResult<
  CrawlRun,
  Error,
  { runId: number; scope: RestartScope }
> {
  return useMutation({
    mutationFn: ({ runId, scope }) =>
      request<CrawlRun>(`/crawl-runs/${runId}/restart/`, { method: "POST", body: { scope } }),
    invalidates: [["crawl-runs"]],
  });
}
