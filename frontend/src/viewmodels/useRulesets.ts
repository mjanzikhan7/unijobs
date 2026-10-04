import { request } from "@/models/api/client";
import type { Paginated, Ruleset } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export function useRulesets(): UseQueryResult<Paginated<Ruleset>> {
  return useQuery({
    queryKey: queryKeys.rulesets(),
    queryFn: () => request<Paginated<Ruleset>>("/rulesets/"),
  });
}

export function useCreateRuleset(): UseMutationResult<Ruleset, Error, Record<string, unknown>> {
  return useMutation({
    mutationFn: (body) => request<Ruleset>("/rulesets/", { method: "POST", body }),
    invalidates: [queryKeys.rulesets()],
  });
}

export function useRescreen(): UseMutationResult<
  { screened: number; changed: number },
  Error,
  number
> {
  return useMutation({
    mutationFn: (rulesetId: number) =>
      request<{ screened: number; changed: number }>(`/rulesets/${rulesetId}/rescreen/`, {
        method: "POST",
      }),
    invalidates: [["jobs"]],
  });
}
