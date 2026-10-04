import { downloadFile, request, toQueryString } from "@/models/api/client";
import type { FacetResponse, Job, JobDetail, Paginated } from "@/models/api/types";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export function jobQueryString(params: Record<string, unknown>): string {
  return toQueryString(params);
}

export function exportJobsCsv(query: string): Promise<void> {
  return downloadFile(`/jobs/export/${query}`, "he-jobs.csv");
}

export function useJobs(query: string): UseQueryResult<Paginated<Job>> {
  return useQuery({
    queryKey: queryKeys.jobs(query),
    queryFn: () => request<Paginated<Job>>(`/jobs/${query}`),
    placeholderData: (previous) => previous,
  });
}

export function useFacets(query: string): UseQueryResult<FacetResponse> {
  return useQuery({
    queryKey: queryKeys.facets(query),
    queryFn: () => request<FacetResponse>(`/jobs/facets/${query}`),
    placeholderData: (previous) => previous,
  });
}

export function useJob(id: number): UseQueryResult<JobDetail> {
  return useQuery({
    queryKey: queryKeys.job(id),
    queryFn: () => request<JobDetail>(`/jobs/${id}/`),
    enabled: Number.isFinite(id),
  });
}

export function useWithdrawJob(): UseMutationResult<Job, Error, { id: number; reason: string }> {
  return useMutation({
    mutationFn: ({ id, reason }) =>
      request<Job>(`/jobs/${id}/withdraw/`, { method: "POST", body: { reason } }),
    invalidates: [["jobs"]],
  });
}

export function useReinstateJob(): UseMutationResult<Job, Error, number> {
  return useMutation({
    mutationFn: (id) => request<Job>(`/jobs/${id}/reinstate/`, { method: "POST" }),
    invalidates: [["jobs"]],
  });
}

export function useDeleteJob(): UseMutationResult<void, Error, number> {
  return useMutation({
    mutationFn: (id) => request<void>(`/jobs/${id}/`, { method: "DELETE" }),
    invalidates: [["jobs"]],
  });
}

export interface JobFormFields {
  title: string;
  department: string;
  category: string;
  reference: string;
  location_raw: string;
  city: string;
  salary_raw: string;
  grade_raw: string;
  contract_raw: string;
  hours_raw: string;
  contract_type: string;
  hours: string;
  workplace: string;
  discipline: string;
  description_html: string;
  closing_date: string | null;
  posted_date: string | null;
}

export interface ManualJobPayload extends JobFormFields {
  institution: string;
  source_url: string;
}

export function useAddManualJob(): UseMutationResult<JobDetail, Error, ManualJobPayload> {
  return useMutation({
    mutationFn: (payload) =>
      request<JobDetail>("/jobs/manual/", { method: "POST", body: payload }),
    invalidates: [["jobs"]],
  });
}

export function useUpdateJob(): UseMutationResult<
  JobDetail,
  Error,
  { id: number; changes: Partial<JobFormFields> }
> {
  return useMutation({
    mutationFn: ({ id, changes }) =>
      request<JobDetail>(`/jobs/${id}/`, { method: "PATCH", body: changes }),
    invalidates: (_, { id }) => [["jobs"], queryKeys.job(id)],
  });
}

export interface ExtractedJobDraft {
  source_url?: string;
  title?: string;
  department?: string;
  location_raw?: string;
  salary_raw?: string;
  description_html?: string;
  closing_date?: string | null;
  posted_date?: string | null;
  reference?: string;
}

export interface ExtractJobResult {
  extracted: boolean;
  reason?: string;
  draft: ExtractedJobDraft;
}

export function useExtractJob(): UseMutationResult<ExtractJobResult, Error, string> {
  return useMutation({
    mutationFn: (url) =>
      request<ExtractJobResult>("/jobs/extract/", { method: "POST", body: { url } }),
  });
}
