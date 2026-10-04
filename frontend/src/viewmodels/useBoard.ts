import { request } from "@/models/api/client";
import type { Application } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export interface BoardColumn {
  status: string;
  label: string;
  applications: Application[];
}

export function useBoard(): UseQueryResult<{ columns: BoardColumn[] }> {
  return useQuery({
    queryKey: queryKeys.board(),
    queryFn: () => request<{ columns: BoardColumn[] }>("/applications/board/"),
  });
}

export function useCreateApplication(): UseMutationResult<
  Application,
  Error,
  { job: number; status?: string }
> {
  return useMutation({
    mutationFn: (body) => request<Application>("/applications/", { method: "POST", body }),
    invalidates: [["applications"]],
  });
}

export function useMoveApplication(): UseMutationResult<
  Application,
  Error,
  { id: number; status: string }
> {
  return useMutation({
    mutationFn: ({ id, status }) =>
      request<Application>(`/applications/${id}/move/`, { method: "POST", body: { status } }),
    invalidates: [["applications"]],
  });
}
