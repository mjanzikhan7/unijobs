import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import type { Institution } from "@/models/api/types";
import { lastCrawl } from "@/models/api/types";

export const MULTI_VALUE_KEYS = [
  "institution",
  "nation",
  "category",
  "discipline",
  "status",
  "source",
  "contract_type",
  "hours",
  "workplace",
  "sponsor_verdict",
  "threshold_verdict",
] as const;

export type MultiValueKey = (typeof MULTI_VALUE_KEYS)[number];

export const SINGLE_VALUE_KEYS = [
  "q",
  "city",
  "salary_min",
  "salary_max",
  "min_fitness",
  "posted_after",
  "closing_before",
  "closing_after",
  "sponsorable",
  "saved",
  "order",
  "page",
] as const;

export type SingleValueKey = (typeof SINGLE_VALUE_KEYS)[number];

export interface JobFilters {
  multi: Partial<Record<MultiValueKey, string[]>>;
  single: Partial<Record<SingleValueKey, string>>;
}

const RESTRICTIVENESS: readonly string[] = [
  "q",
  "min_fitness",
  "salary_min",
  "threshold_verdict",
  "sponsor_verdict",
  "sponsorable",
  "closing_before",
  "posted_after",
  "institution",
  "category",
  "discipline",
  "city",
  "contract_type",
  "hours",
  "workplace",
  "nation",
  "status",
];

export function parseFilters(params: URLSearchParams): JobFilters {
  const multi: Partial<Record<MultiValueKey, string[]>> = {};
  for (const key of MULTI_VALUE_KEYS) {
    const values = params.getAll(key).filter(Boolean);
    if (values.length > 0) multi[key] = values;
  }

  const single: Partial<Record<SingleValueKey, string>> = {};
  for (const key of SINGLE_VALUE_KEYS) {
    const value = params.get(key);
    if (value) single[key] = value;
  }

  return { multi, single };
}

export function filtersToParams(filters: JobFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, values] of Object.entries(filters.multi)) {
    for (const value of values ?? []) params.append(key, value);
  }
  for (const [key, value] of Object.entries(filters.single)) {
    if (value) params.set(key, value);
  }
  return params;
}

export function activeFilterCount(filters: JobFilters): number {
  const multi = Object.values(filters.multi).filter((values) => (values ?? []).length > 0).length;
  const single = Object.keys(filters.single).filter(
    (key) => key !== "order" && key !== "page",
  ).length;
  return multi + single;
}

export function mostRestrictiveFilter(filters: JobFilters): string | null {
  for (const key of RESTRICTIVENESS) {
    if (filters.multi[key as MultiValueKey]?.length) return key;
    if (filters.single[key as SingleValueKey]) return key;
  }
  return null;
}

export function useJobFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [pending, setPending] = useState<JobFilters | null>(null);
  const [pendingFor, setPendingFor] = useState(searchParams);
  const fromUrl = useMemo(() => parseFilters(searchParams), [searchParams]);

  if (searchParams !== pendingFor) {
    setPendingFor(searchParams);
    setPending(null);
  }
  const filters = searchParams === pendingFor && pending ? pending : fromUrl;

  const setFilters = useCallback(
    (next: JobFilters) => {
      setPending(next);
      setSearchParams(filtersToParams(next), { replace: false });
    },
    [setSearchParams],
  );

  const toggleValue = useCallback(
    (key: MultiValueKey, value: string) => {
      const current = filters.multi[key] ?? [];
      const next = current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value];

      const updated: JobFilters = {
        multi: { ...filters.multi, [key]: next },
        single: { ...filters.single },
      };
      delete updated.single.page;
      setFilters(updated);
    },
    [filters, setFilters],
  );

  const setValue = useCallback(
    (key: SingleValueKey, value: string | null) => {
      const single = { ...filters.single };
      if (value) {
        single[key] = value;
      } else {
        delete single[key];
      }
      if (key !== "page") delete single.page;
      setFilters({ multi: { ...filters.multi }, single });
    },
    [filters, setFilters],
  );

  const clearFilter = useCallback(
    (key: string) => {
      const multi = { ...filters.multi };
      const single = { ...filters.single };
      delete multi[key as MultiValueKey];
      delete single[key as SingleValueKey];
      delete single.page;
      setFilters({ multi, single });
    },
    [filters, setFilters],
  );

  const clearAll = useCallback(() => {
    setFilters({ multi: {}, single: {} });
  }, [setFilters]);

  return { filters, searchParams, setFilters, toggleValue, setValue, clearFilter, clearAll };
}

export function toQueryParams(filters: JobFilters): Record<string, unknown> {
  return { ...filters.multi, ...filters.single };
}

export type SortMode = "ranking" | "attention";

export const SORT_OPTIONS: Array<{ value: SortMode; label: string }> = [
  { value: "ranking", label: "Ranking" },
  { value: "attention", label: "Attention required" },
];

export function attentionRank(institution: Institution): number {
  const last = lastCrawl(institution);
  if (!last) return 1;
  if (last.dropped_to_zero) return 0;
  if (last.outcome !== "OK") return 0;
  if (last.fallback_fired) return 2;
  return 3;
}

export function compareByRanking(left: Institution, right: Institution): number {
  const leftRanking = left.ranking ?? Number.POSITIVE_INFINITY;
  const rightRanking = right.ranking ?? Number.POSITIVE_INFINITY;
  const rank = leftRanking - rightRanking;
  return rank !== 0 ? rank : left.name.localeCompare(right.name);
}

export function compareByAttention(left: Institution, right: Institution): number {
  const rank = attentionRank(left) - attentionRank(right);
  return rank !== 0 ? rank : left.name.localeCompare(right.name);
}
