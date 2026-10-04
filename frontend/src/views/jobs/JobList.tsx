import type { CSSProperties } from "react";
import { useCallback, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { ErrorMessage, Spinner, Toast } from "@/components/Feedback";
import { Icon } from "@/components/Icon/Icon";
import { Pagination } from "@/components/Pagination/Pagination";
import type { Discipline, Job } from "@/models/api/types";
import {
  activeFilterCount,
  mostRestrictiveFilter,
  toQueryParams,
  useJobFilters,
} from "@/utilities/filters";
import type { JobFilters as Filters, MultiValueKey, SingleValueKey } from "@/utilities/filters";
import { JOB_LIST_SHORTCUTS, useShortcuts } from "@/utilities/keyboard";
import type { Shortcut } from "@/utilities/keyboard";
import { useInstitutions } from "@/viewmodels/useInstitutions";
import { exportJobsCsv, jobQueryString, useFacets, useJobs } from "@/viewmodels/useJobs";
import { useMinimumVisible } from "@/hooks/useMinimumVisible";
import { useSaveJob, useUnsaveJob } from "@/viewmodels/useSavedJobs";
import { useCreateSavedSearch } from "@/viewmodels/useSavedSearches";

import { DisciplineBrowse } from "./DisciplineBrowse";
import { JobCard } from "./JobCard";
import { JobFiltersPanel } from "./JobFilters";
import { JobListEmpty } from "./JobListEmpty";
import { JobListSkeleton } from "./JobListSkeleton";
import { MobileFilterSheet } from "./MobileFilterSheet";

function describeFilterValue(filters: Filters, key: string): string | undefined {
  const multi = filters.multi[key as MultiValueKey];
  if (multi?.length) return multi.join(", ");
  return filters.single[key as SingleValueKey];
}

const SORT_OPTIONS = [
  { value: "-posted", label: "Newest" },
  { value: "closing", label: "Closing soonest" },
  { value: "-fitness", label: "Best fit" },
  { value: "-salary", label: "Highest salary" },
] as const;

export function JobList() {
  const navigate = useNavigate();
  const { filters, searchParams, toggleValue, setValue, clearFilter, clearAll } = useJobFilters();
  const query = useMemo(() => jobQueryString(toQueryParams(filters)), [filters]);

  const jobs = useJobs(query);
  const searching = useMinimumVisible(jobs.isFetching);
  const facets = useFacets(query);
  const institutions = useInstitutions();
  const saveJob = useSaveJob();
  const unsaveJob = useUnsaveJob();
  const createSavedSearch = useCreateSavedSearch();

  const searchRef = useRef<HTMLInputElement>(null);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [toast, setToast] = useState<{ message: string; tone: "info" | "error" } | null>(null);

  const results = useMemo(() => jobs.data?.results ?? [], [jobs.data]);

  const onSave = useCallback(
    (job: Job) => {
      if (job.is_saved) {
        setToast({ message: "Open the saved view to remove it.", tone: "info" });
        return;
      }
      saveJob.mutate(job.id, {
        onError: () => setToast({ message: "Could not save that job. Try again.", tone: "error" }),
        onSuccess: () => setToast({ message: `Saved “${job.title}”.`, tone: "info" }),
      });
    },
    [saveJob],
  );

  const shortcuts = useMemo<Shortcut[]>(
    () => [
      { key: "/", description: "Focus search", handler: () => searchRef.current?.focus() },
      {
        key: "j",
        description: "Next job",
        handler: () => setFocusedIndex((index) => Math.min(index + 1, results.length - 1)),
      },
      {
        key: "k",
        description: "Previous job",
        handler: () => setFocusedIndex((index) => Math.max(index - 1, 0)),
      },
      {
        key: "s",
        description: "Save",
        handler: () => {
          const job = results[focusedIndex];
          if (job) onSave(job);
        },
      },
      {
        key: "Enter",
        description: "Open",
        handler: () => {
          const job = results[focusedIndex];
          if (job) void navigate(`/jobs/${job.id}`);
        },
      },
      {
        key: "Escape",
        description: "Blur search",
        allowInInput: true,
        handler: () => searchRef.current?.blur(),
      },
    ],
    [results, focusedIndex, navigate, onSave],
  );

  useShortcuts(shortcuts);

  const onExport = useCallback(async () => {
    try {
      await exportJobsCsv(query);
    } catch {
      setToast({ message: "Export failed.", tone: "error" });
    }
  }, [query]);

  const onSaveSearch = useCallback(() => {
    const name = window.prompt("Name this search");
    if (!name) return;
    createSavedSearch.mutate(
      { name, query: searchParams.toString() },
      {
        onSuccess: () => setToast({ message: `Saved search “${name}”.`, tone: "info" }),
        onError: () => setToast({ message: "Could not save that search.", tone: "error" }),
      },
    );
  }, [createSavedSearch, searchParams]);

  const activeCount = activeFilterCount(filters);
  const restrictive = mostRestrictiveFilter(filters);
  const page = jobs.data?.page ?? 1;

  const filterPanel = (
    <JobFiltersPanel
      filters={filters}
      facets={facets.data}
      institutions={institutions.data?.results ?? []}
      onToggle={toggleValue}
      onSet={setValue}
      onClearAll={clearAll}
    />
  );

  return (
    <div className="mx-auto flex max-w-content flex-col gap-4">
      <div className="flex flex-col gap-1 rounded-2xl border border-border-subtle bg-surface p-2 shadow-xs sm:flex-row sm:items-stretch sm:gap-0 sm:divide-x sm:divide-border-subtle">
        <div className="relative flex min-w-0 flex-1 items-center gap-2.5 rounded-xl px-2 py-1.5 sm:pr-4">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-subtle text-brand">
            <Icon name="search" className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <label htmlFor="job-search" className="block text-caption font-medium text-text-muted">
              Search
            </label>
            <input
              id="job-search"
              ref={searchRef}
              type="search"
              placeholder="Titles, departments, adverts…"
              defaultValue={filters.single.q ?? ""}
              onKeyDown={(event) => {
                if (event.key === "Enter") setValue("q", event.currentTarget.value || null);
              }}
              className="w-full truncate border-0 bg-transparent p-0 text-body font-medium text-text-primary placeholder:font-normal placeholder:text-text-muted focus:outline-none focus-visible:outline-none"
            />
          </div>
          {searching ? (
            <Spinner label="Searching…" inline />
          ) : filters.single.q ? (
            <button
              type="button"
              onClick={() => {
                if (searchRef.current) searchRef.current.value = "";
                setValue("q", null);
              }}
              aria-label="Clear search"
              className="shrink-0 rounded-full p-1.5 text-text-muted hover:bg-surface-sunken hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              <Icon name="close" className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        <div className="flex items-center gap-2.5 rounded-xl px-2 py-1.5 sm:px-4">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-subtle text-brand">
            <Icon name="trends" className="h-4 w-4" />
          </span>
          <div>
            <label
              htmlFor="job-sort"
              className="block text-caption font-medium text-text-muted"
            >
              Sort by
            </label>
            <select
              id="job-sort"
              value={filters.single.order ?? "-posted"}
              onChange={(event) => setValue("order", event.target.value)}
              className="border-0 bg-transparent p-0 text-body font-medium text-text-primary focus:outline-none focus-visible:outline-none"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-xl px-2 py-1.5 sm:pl-4">
          <Button variant="quiet" size="sm" onClick={onSaveSearch}>
            Save search
          </Button>
          <Button variant="quiet" size="sm" onClick={() => void onExport()}>
            Export
          </Button>
        </div>
      </div>

      <MobileFilterSheet activeCount={activeCount}>{filterPanel}</MobileFilterSheet>

      <div className="flex gap-6">
        <aside
          id="job-filters"
          tabIndex={-1}
          aria-label="Filters"
          className="sticky top-20 hidden h-fit max-h-[calc(100vh-6rem)] w-72 shrink-0 overflow-y-auto lg:block"
        >
          <Card padding="sm">{filterPanel}</Card>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="mb-4">
            <DisciplineBrowse
              values={facets.data?.facets.discipline ?? []}
              selected={filters.multi.discipline ?? []}
              onSelect={(discipline: Discipline) => toggleValue("discipline", discipline)}
            />
          </div>

          <p className="mb-3 text-body-sm text-text-secondary" role="status" aria-live="polite">
            {jobs.isLoading
              ? "Searching…"
              : `${jobs.data?.count ?? 0} vacanc${jobs.data?.count === 1 ? "y" : "ies"}`}
          </p>

          {jobs.isLoading ? <JobListSkeleton /> : null}
          {jobs.isError ? (
            <ErrorMessage error={jobs.error} onRetry={() => void jobs.refetch()} />
          ) : null}

          {!jobs.isLoading && !jobs.isError && results.length === 0 ? (
            <JobListEmpty
              restrictiveFilter={restrictive}
              filterValue={restrictive ? describeFilterValue(filters, restrictive) : undefined}
              onClearFilter={clearFilter}
              onClearAll={clearAll}
              activeFilters={activeCount}
            />
          ) : null}

          <ol className="flex flex-col gap-3">
            {results.map((job, index) => (
              <li key={job.id} style={{ "--stagger": index } as CSSProperties}>
                <JobCard job={job} isFocused={index === focusedIndex} onSave={onSave} />
              </li>
            ))}
          </ol>

          <div className="mt-6">
            <Pagination
              label="Jobs"
              page={page}
              totalPages={jobs.data?.total_pages ?? 0}
              hasPrevious={Boolean(jobs.data?.previous)}
              hasNext={Boolean(jobs.data?.next)}
              onChange={(next) => setValue("page", String(next))}
            />
          </div>
        </div>
      </div>

      <details className="text-body-sm text-text-secondary">
        <summary className="cursor-pointer">Keyboard shortcuts</summary>
        <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
          {JOB_LIST_SHORTCUTS.map((shortcut) => (
            <div key={shortcut.key} className="flex items-center gap-2">
              <dt>
                <kbd className="rounded-xs border border-border-strong bg-surface-sunken px-1.5 py-0.5 font-mono text-caption">
                  {shortcut.key}
                </kbd>
              </dt>
              <dd>{shortcut.description}</dd>
            </div>
          ))}
        </dl>
      </details>

      <Toast message={toast?.message ?? null} tone={toast?.tone} onDismiss={() => setToast(null)} />
      {unsaveJob.isError ? <ErrorMessage error={unsaveJob.error} /> : null}
    </div>
  );
}
