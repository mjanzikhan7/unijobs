import { request } from "@/models/api/client";
import { queryKeys } from "@/models/queryKeys";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export interface CandidateOverview {
  days: number;
  active_candidates: number;
  searches: number;
  searches_with_no_results: number;
  empty_search_rate: number;
  job_views: number;
  saves: number;
  applications: number;
  cv_uploads: number;
  view_to_save_rate: number;
  save_to_apply_rate: number;
}

export interface DimensionRow {
  value: string;
  views: number;
  saves: number;
  applications: number;
  total: number;
}

export interface SearchRow {
  query: string;
  searches: number;
  searchers: number;
  found_nothing: number;
}

export interface InstitutionEngagement {
  slug: string;
  name: string;
  views: number;
  saves: number;
  applications: number;
  total: number;
}

export interface CandidateInsights {
  days: number;
  limit: number;
  overview: CandidateOverview;
  by_day: Record<string, number | string>[];
  top_searches: SearchRow[];
  by_nation: DimensionRow[];
  by_category: DimensionRow[];
  institutions: InstitutionEngagement[];
}

export interface PostingRow {
  slug: string;
  name: string;
  posted: number;
  open_now: number;
  closed: number;
  withdrawn: number;
}

export interface InstitutionInsights {
  days: number;
  limit: number;
  institutions: PostingRow[];
  by_day: { day: string; posted: number }[];
  totals: { posted: number; open_now: number; institutions_posting: number };
  engagement: InstitutionEngagement[];
}

export interface CloudTerm {
  term: string;
  occurrences: number;
  searchers: number;
}

export interface SearchCloud {
  days: number;
  max_occurrences: number;
  terms: CloudTerm[];
}

export function useCandidateInsights(days: number): UseQueryResult<CandidateInsights> {
  return useQuery({
    queryKey: queryKeys.insights("candidates", days),
    queryFn: () => request<CandidateInsights>(`/insights/candidates/?days=${days}`),
  });
}

export function useInstitutionInsights(
  days: number,
  limit = 500,
): UseQueryResult<InstitutionInsights> {
  return useQuery({
    queryKey: [...queryKeys.insights("institutions", days), limit],
    queryFn: () => request<InstitutionInsights>(`/insights/institutions/?days=${days}&limit=${limit}`),
  });
}

export function useSearchCloud(days: number): UseQueryResult<SearchCloud> {
  return useQuery({
    queryKey: queryKeys.insights("search-cloud", days),
    queryFn: () => request<SearchCloud>(`/insights/search-cloud/?days=${days}`),
  });
}
