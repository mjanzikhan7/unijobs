import { request, toQueryString } from "@/models/api/client";
import type { CrawlLogEntry } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useQuery } from "@/store/queries/useQuery";

export interface RunLogs {
  entries: CrawlLogEntry[];
  isLoading: boolean;
}

export function useRunLogs(runId: number | null): RunLogs {
  const query = useQuery<CrawlLogEntry[]>({
    queryKey: queryKeys.runLogs(runId ?? -1),
    queryFn: async ({ previous }) => {
      const seen = previous ?? [];
      const after = seen.at(-1)?.id ?? 0;
      const fresh = await request<CrawlLogEntry[]>(
        `/crawl-runs/${runId}/logs/${toQueryString({ after })}`,
      );
      return fresh.length ? [...seen, ...fresh] : seen;
    },
    enabled: runId !== null,
    refetchInterval: 3_000,
  });

  return { entries: query.data ?? [], isLoading: query.isLoading };
}
