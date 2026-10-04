import { API_BASE, apiHeaders, request } from "@/models/api/client";
import type { Institution, Paginated, RegisterCandidate } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export function useInstitutions(): UseQueryResult<Paginated<Institution>> {
  return useQuery({
    queryKey: queryKeys.institutions(),
    queryFn: () => request<Paginated<Institution>>("/institutions/?page_size=200"),
  });
}

export function useReviewQueue(): UseQueryResult<Institution[]> {
  return useQuery({
    queryKey: queryKeys.reviewQueue(),
    queryFn: () => request<Institution[]>("/institutions/review-queue/"),
  });
}

export function useRegisterSearch(
  term: string,
  minimumLength: number,
): UseQueryResult<RegisterCandidate[]> {
  return useQuery({
    queryKey: queryKeys.registerSearch(term),
    queryFn: () =>
      request<RegisterCandidate[]>(`/institutions/register-search/?q=${encodeURIComponent(term)}`),
    enabled: term.trim().length >= minimumLength,
  });
}

export function useUpdateInstitution(): UseMutationResult<
  Institution,
  Error,
  { id: number; changes: Partial<Institution> }
> {
  return useMutation({
    mutationFn: ({ id, changes }) =>
      request<Institution>(`/institutions/${id}/`, { method: "PATCH", body: changes }),
    invalidates: [["institutions"]],
  });
}

export function useResolveSponsor(): UseMutationResult<
  Institution,
  Error,
  { id: number; registered_legal_name: string; verdict: string; notes?: string }
> {
  return useMutation({
    mutationFn: ({ id, ...body }) =>
      request<Institution>(`/institutions/${id}/resolve-sponsor/`, { method: "POST", body }),
    invalidates: [["institutions"]],
  });
}

export function useInstitution(slug: string): UseQueryResult<Institution | null> {
  return useQuery({
    queryKey: queryKeys.institution(slug),
    queryFn: async () => {
      const page = await request<Paginated<Institution>>(
        `/institutions/?slug=${encodeURIComponent(slug)}`,
      );
      return page.results[0] ?? null;
    },
  });
}

export function useCreateInstitution(): UseMutationResult<
  Institution,
  Error,
  Partial<Institution>
> {
  return useMutation({
    mutationFn: (body) => request<Institution>("/institutions/", { method: "POST", body }),
    invalidates: [["institutions"]],
  });
}

export function useDeleteInstitution(): UseMutationResult<void, Error, number> {
  return useMutation({
    mutationFn: (id) => request<void>(`/institutions/${id}/`, { method: "DELETE" }),
    invalidates: [["institutions"]],
  });
}

export function useUploadInstitutionMedia(): UseMutationResult<
  Institution,
  Error,
  { id: number; logo?: File; banner?: File }
> {
  return useMutation({
    mutationFn: async ({ id, logo, banner }) => {
      const body = new FormData();
      if (logo) body.append("logo", logo);
      if (banner) body.append("banner", banner);

      const headers = apiHeaders("POST");

      const response = await fetch(`${API_BASE}/institutions/${id}/media/`, {
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
            : "That image could not be read.";
        throw new Error(detail);
      }
      return payload as Institution;
    },
    invalidates: [["institutions"]],
  });
}
