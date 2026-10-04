import { API_BASE, apiHeaders, request } from "@/models/api/client";
import type { Paginated } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export interface CVSuggestions {
  skills: string[];
  domains: string[];
  seniority: string[];
  projects: string[];
  education: string[];
  years_experience: number;
  missing: string[];
}

export interface CV {
  id: number;
  original_filename: string;
  content_type: string;
  byte_size: number;
  suggestions: CVSuggestions | null;
  applied_at: string | null;
  uploaded_at: string;
}

export function useCVs(): UseQueryResult<Paginated<CV>> {
  return useQuery({
    queryKey: queryKeys.cvs(),
    queryFn: () => request<Paginated<CV>>("/cvs/"),
  });
}

export function useUploadCV(): UseMutationResult<CV, Error, File> {
  return useMutation({
    mutationFn: async (file) => {
      const body = new FormData();
      body.append("file", file);

      const headers = apiHeaders("POST");

      const response = await fetch(`${API_BASE}/cvs/upload/`, {
        method: "POST",
        headers,
        body,
        credentials: "same-origin",
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const detail =
          payload && typeof payload === "object" && "detail" in payload
            ? String(payload.detail)
            : "That file could not be read.";
        throw new Error(detail);
      }
      return payload as CV;
    },
    invalidates: [queryKeys.cvs()],
  });
}

export function useApplyCV(): UseMutationResult<
  unknown,
  Error,
  { id: number; body: Partial<CVSuggestions> & { replace?: boolean } }
> {
  return useMutation({
    mutationFn: ({ id, body }) => request(`/cvs/${id}/apply_to_profile/`, { method: "POST", body }),
    invalidates: [
      queryKeys.cvs(),
      queryKeys.profiles(),
      ["jobs"],
    ],
  });
}

export function useDeleteCV(): UseMutationResult<void, Error, number> {
  return useMutation({
    mutationFn: (id) => request<void>(`/cvs/${id}/`, { method: "DELETE" }),
    invalidates: [queryKeys.cvs()],
  });
}
