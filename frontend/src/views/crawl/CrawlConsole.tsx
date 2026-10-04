import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "@/components/Badge/Badge";
import type { BadgeTone } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { Chip } from "@/components/Chip/Chip";
import { Select } from "@/components/Field/Select";
import { ErrorMessage, Spinner, Toast } from "@/components/Feedback";
import { ApiError } from "@/models/api/client";
import type { CrawlOutcome, Institution, LastCrawl } from "@/models/api/types";
import { lastCrawl } from "@/models/api/types";
import type { SortMode } from "@/utilities/filters";
import { attentionRank, compareByAttention, compareByRanking, SORT_OPTIONS } from "@/utilities/filters";
import { formatDateTime, humanise } from "@/utilities/format";
import { useActiveRun } from "@/viewmodels/useActiveRun";
import { useCancelCrawl, usePauseCrawl, useResumeCrawl } from "@/viewmodels/useCrawlControl";
import { useCrawlRuns, useStartCrawl } from "@/viewmodels/useCrawlRuns";
import { useInstitutions, useUpdateInstitution } from "@/viewmodels/useInstitutions";

import { CrawlLogPanel } from "./CrawlLogPanel";

const OUTCOME_TONES: Record<CrawlOutcome, BadgeTone> = {
  OK: "positive",
  ZERO_RESULTS: "caution",
  ROBOTS_DISALLOWED: "neutral",
  BLOCKED: "negative",
  OFFLINE: "negative",
  TIMEOUT: "negative",
  PARSE_ERROR: "negative",
  NO_ADAPTER: "caution",
  SKIPPED: "neutral",
};

export function CrawlConsole() {
  const institutions = useInstitutions();
  const runs = useCrawlRuns();
  const activeRun = useActiveRun();
  const startCrawl = useStartCrawl();
  const pauseCrawl = usePauseCrawl();
  const resumeCrawl = useResumeCrawl();
  const cancelCrawl = useCancelCrawl();
  const updateInstitution = useUpdateInstitution();
  const [toast, setToast] = useState<{ message: string; tone: "info" | "error" } | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>("ranking");

  const activeRunId = activeRun.data?.run?.id ?? null;
  const activeRunStatus = activeRun.data?.run?.status;
  const controlPending = pauseCrawl.isPending || resumeCrawl.isPending || cancelCrawl.isPending;

  const onPause = () => {
    if (activeRunId === null) return;
    pauseCrawl.mutate(activeRunId, {
      onError: () => setToast({ message: "Could not pause the crawl.", tone: "error" }),
    });
  };

  const onResume = () => {
    if (activeRunId === null) return;
    resumeCrawl.mutate(activeRunId, {
      onError: () => setToast({ message: "Could not resume the crawl.", tone: "error" }),
    });
  };

  const onCancel = () => {
    if (activeRunId === null) return;
    cancelCrawl.mutate(activeRunId, {
      onSuccess: () => setToast({ message: `Run ${activeRunId} stopped.`, tone: "info" }),
      onError: () => setToast({ message: "Could not stop the crawl.", tone: "error" }),
    });
  };

  const rows = useMemo(() => {
    const list = [...(institutions.data?.results ?? [])];
    list.sort(sortMode === "ranking" ? compareByRanking : compareByAttention);
    return list;
  }, [institutions.data, sortMode]);

  const onStart = (slugs?: string[]) => {
    startCrawl.mutate(slugs, {
      onSuccess: (run) => setToast({ message: `Crawl run ${run.id} started.`, tone: "info" }),
      onError: (error) => {
        const activeId =
          error instanceof ApiError ? (error.extra.active_run_id as number | undefined) : undefined;
        setToast({
          message: activeId
            ? `A crawl is already running (run ${activeId}).`
            : "Could not start a crawl.",
          tone: "error",
        });
      },
    });
  };

  const needingAttention = rows.filter((row) => attentionRank(row) <= 1).length;

  const columns: DataTableColumn<Institution>[] = [
    { key: "rank", header: "Rank", numeric: true, cell: (row) => row.ranking ?? "—" },
    {
      key: "name",
      header: "Institution",
      isRowHeader: true,
      cell: (row) => {
        const last = lastCrawl(row);
        return (
          <>
            <a
              href={row.careers_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand underline underline-offset-2 hover:decoration-2"
            >
              {row.name}
            </a>
            {last?.error_detail ? (
              <details className="mt-1">
                <summary className="cursor-pointer text-caption text-danger">
                  {last.error_class || "Error"}
                </summary>
                <p className="mt-1 text-caption text-text-secondary">{last.error_detail}</p>
              </details>
            ) : null}
          </>
        );
      },
    },
    {
      key: "adapter",
      header: "Adapter",
      cell: (row) => {
        const last = lastCrawl(row);
        return (
          <span className="flex flex-wrap items-center gap-1">
            {row.effective_platform ? humanise(row.effective_platform) : "—"}
            {last?.fallback_fired ? <Chip tone="caution">fallback</Chip> : null}
          </span>
        );
      },
    },
    {
      key: "outcome",
      header: "Outcome",
      cell: (row) => {
        const last = lastCrawl(row);
        if (!last) return <Badge tone="neutral">Never crawled</Badge>;
        const outcome: CrawlOutcome = last.outcome ?? "SKIPPED";
        return <Badge tone={OUTCOME_TONES[outcome]}>{humanise(outcome)}</Badge>;
      },
    },
    {
      key: "found",
      header: "Found",
      numeric: true,
      cell: (row) => lastCrawl(row)?.vacancies_found ?? "—",
    },
    {
      key: "previously",
      header: "Previously",
      numeric: true,
      cell: (row) => {
        const last = lastCrawl(row);
        return (
          <>
            {last?.previous_vacancies_found ?? "—"}
            {last?.dropped_to_zero ? (
              <span className="ml-1 text-danger" title="Had vacancies, now has none">
                ↓
              </span>
            ) : null}
          </>
        );
      },
    },
    {
      key: "last-crawled",
      header: "Last crawled",
      cell: (row) => {
        const last: LastCrawl | null = lastCrawl(row);
        return last ? formatDateTime(last.started_at) : "—";
      },
    },
    {
      key: "enabled",
      header: "Enabled",
      cell: (row) => (
        <>
          <label className="sr-only" htmlFor={`enabled-${row.id}`}>
            Crawl {row.name}
          </label>
          <input
            id={`enabled-${row.id}`}
            type="checkbox"
            checked={row.crawl_enabled}
            onChange={(event) =>
              updateInstitution.mutate({
                id: row.id,
                changes: { crawl_enabled: event.target.checked },
              })
            }
            className="h-5 w-5 accent-[var(--color-brand)]"
          />
        </>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      cell: (row) => (
        <Button
          variant="quiet"
          size="sm"
          onClick={() => onStart([row.slug])}
          disabled={Boolean(activeRunId)}
        >
          Re-crawl
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-heading-xl font-bold">Crawl console</h1>
          <p className="mt-1 text-body-sm text-text-secondary">
            {institutions.data?.count ?? 0} institutions ·{" "}
            <strong className="text-text-primary">{needingAttention} need attention</strong>
          </p>
        </div>
        <Button
          variant="primary"
          onClick={() => onStart(undefined)}
          disabled={Boolean(activeRunId) || startCrawl.isPending}
        >
          {activeRunId ? "Crawl in progress" : "Run crawl"}
        </Button>
      </header>

      {activeRunId ? (
        <Card aria-live="polite" className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-heading-sm font-semibold">
              Run{" "}
              <Link to={`/admin/crawl/${activeRunId}`} className="text-brand underline underline-offset-2 hover:decoration-2">
                #{activeRunId}
              </Link>{" "}
              {activeRunStatus === "PAUSED" ? "paused" : "in progress"}
            </h2>
            <p className="text-body-sm tabular-nums text-text-secondary">
              {activeRun.data?.run?.institutions_done ?? 0} of{" "}
              {activeRun.data?.run?.institutions_total ?? "?"} done
            </p>
            <div className="flex gap-2">
              {activeRunStatus === "RUNNING" ? (
                <Button variant="quiet" size="sm" onClick={onPause} disabled={controlPending}>
                  Pause
                </Button>
              ) : null}
              {activeRunStatus === "PAUSED" ? (
                <Button variant="quiet" size="sm" onClick={onResume} disabled={controlPending}>
                  Resume
                </Button>
              ) : null}
              <Button variant="quiet" size="sm" onClick={onCancel} disabled={controlPending}>
                Stop
              </Button>
            </div>
          </div>
          <CrawlLogPanel runId={activeRunId} />
        </Card>
      ) : null}

      {institutions.isLoading ? <Spinner label="Loading institutions" /> : null}
      {institutions.isError ? (
        <ErrorMessage error={institutions.error} onRetry={() => void institutions.refetch()} />
      ) : null}

      <div className="flex items-center gap-2">
        <label htmlFor="console-sort" className="text-body-sm font-medium">
          Sort by
        </label>
        <Select
          id="console-sort"
          value={sortMode}
          onChange={(event) => setSortMode(event.target.value as SortMode)}
          className="w-auto"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>

      <DataTable<Institution>
        caption={`Every institution, with its most recent crawl outcome, ordered by ${
          sortMode === "ranking" ? "league-table ranking" : "attention required"
        }`}
        columns={columns}
        rows={rows}
        rowKey={(row) => row.id}
        loading={institutions.isLoading}
        rowAlarming={(row) => Boolean(lastCrawl(row)?.dropped_to_zero)}
        emptyTitle="No institutions yet"
        emptyBody="Seed the institution list, then run a crawl to populate this table."
      />

      <section>
        <h2 className="font-display text-heading-md font-semibold">Recent runs</h2>
        <ul className="mt-2 space-y-1 text-body-sm text-text-secondary">
          {(runs.data?.results ?? []).slice(0, 10).map((run) => (
            <li key={run.id}>
              <Link to={`/admin/crawl/${run.id}`} className="text-brand underline underline-offset-2 hover:decoration-2">
                Run #{run.id}
              </Link>{" "}
              · {humanise(run.status ?? "")} · {formatDateTime(run.started_at)} ·{" "}
              <span className="tabular-nums">
                +{run.jobs_new} new, ~{run.jobs_updated} updated, −{run.jobs_closed} closed
              </span>
            </li>
          ))}
        </ul>
      </section>

      <Toast message={toast?.message ?? null} tone={toast?.tone} onDismiss={() => setToast(null)} />
    </div>
  );
}
