import { request } from "@/models/api/client";
import type { CrawlRun, CrawlRunDetail, Paginated, RunDiff } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export function useCrawlRuns(): UseQueryResult<Paginated<CrawlRun>> {
  return useQuery({
    queryKey: queryKeys.runs(),
    queryFn: () => request<Paginated<CrawlRun>>("/crawl-runs/"),
  });
}

export function useCrawlRun(id: number): UseQueryResult<CrawlRunDetail> {
  return useQuery({
    queryKey: queryKeys.run(id),
    queryFn: () => request<CrawlRunDetail>(`/crawl-runs/${id}/`),
    enabled: Number.isFinite(id),
  });
}

export function useRunDiff(id: number): UseQueryResult<RunDiff> {
  return useQuery({
    queryKey: queryKeys.runDiff(id),
    queryFn: () => request<RunDiff>(`/crawl-runs/${id}/diff/`),
    enabled: Number.isFinite(id),
  });
}

export function useStartCrawl(): UseMutationResult<CrawlRun, Error, string[] | undefined> {
  return useMutation({
    mutationFn: (institutions?: string[]) =>
      request<CrawlRun>("/crawl-runs/", {
        method: "POST",
        body: { institutions: institutions ?? [] },
      }),
    invalidates: [["crawl-runs"]],
  });
}
