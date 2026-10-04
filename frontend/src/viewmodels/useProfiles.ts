import { request } from "@/models/api/client";
import type { CandidateProfile, Paginated } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export function useProfiles(): UseQueryResult<Paginated<CandidateProfile>> {
  return useQuery({
    queryKey: queryKeys.profiles(),
    queryFn: () => request<Paginated<CandidateProfile>>("/profiles/"),
  });
}
