import { request } from "@/models/api/client";
import type { CrawlRun } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export function useActiveRun(): UseQueryResult<{ run: CrawlRun | null }> {
  return useQuery({
    queryKey: queryKeys.activeRun(),
    queryFn: () => request<{ run: CrawlRun | null }>("/crawl-runs/active/"),
    refetchInterval: (data) => (data?.run ? 5_000 : false),
  });
}
