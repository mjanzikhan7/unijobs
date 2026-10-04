import { request } from "@/models/api/client";
import type { Paginated, SavedSearch } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export function useSavedSearches(): UseQueryResult<Paginated<SavedSearch>> {
  return useQuery({
    queryKey: queryKeys.savedSearches(),
    queryFn: () => request<Paginated<SavedSearch>>("/saved-searches/"),
  });
}

export function useCreateSavedSearch(): UseMutationResult<
  SavedSearch,
  Error,
  { name: string; query: string }
> {
  return useMutation({
    mutationFn: (body) => request<SavedSearch>("/saved-searches/", { method: "POST", body }),
    invalidates: [queryKeys.savedSearches()],
  });
}
