import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { ErrorMessage, Spinner, Toast } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import { CrawlLogPanel } from "@/views/crawl/CrawlLogPanel";
import { JobCard } from "@/views/jobs/JobCard";
import type { JobRevision } from "@/models/api/types";
import { formatDateTime, humanise } from "@/utilities/format";
import { useRestartCrawl } from "@/viewmodels/useCrawlControl";
import { useCrawlRun, useRunDiff } from "@/viewmodels/useCrawlRuns";

type Tabname = "new" | "changed" | "disappeared";

const changeColumns: DataTableColumn<JobRevision>[] = [
  {
    key: "job",
    header: "Job",
    isRowHeader: true,
    cell: (row) => (
      <>
        {row.job_title}
        <span className="text-text-muted"> · {row.institution_name}</span>
      </>
    ),
  },
  { key: "field", header: "Field", cell: (row) => humanise(row.field ?? "") },
  {
    key: "before",
    header: "Before",
    cell: (row) => <del className="text-danger">{row.value_before || "—"}</del>,
  },
  {
    key: "after",
    header: "After",
    cell: (row) => <ins className="text-success no-underline">{row.value_after || "—"}</ins>,
  },
];

export function RunDetail() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const run = useCrawlRun(id);
  const diff = useRunDiff(id);
  const restartCrawl = useRestartCrawl();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tabname>("new");
  const [toast, setToast] = useState<{ message: string; tone: "info" | "error" } | null>(null);

  const onRestart = (scope: "all" | "failures") => {
    restartCrawl.mutate(
      { runId: id, scope },
      {
        onSuccess: (newRun) => {
          setToast({ message: `Run ${newRun.id} started.`, tone: "info" });
          void navigate(`/admin/crawl/${newRun.id}`);
        },
        onError: () =>
          setToast({
            message:
              scope === "failures"
                ? "Nothing needs retrying — every institution came back OK."
                : "Could not start a new run.",
            tone: "error",
          }),
      },
    );
  };

  if (diff.isLoading || run.isLoading) return <Spinner label="Loading run" />;
  if (diff.isError) return <ErrorMessage error={diff.error} onRetry={() => void diff.refetch()} />;
  if (!diff.data) return null;

  const counts: Record<Tabname, number> = {
    new: diff.data.new.length,
    changed: diff.data.changed.length,
    disappeared: diff.data.disappeared.length,
  };

  return (
    <div className="space-y-4">
      <header className="space-y-2">
        <h1 className="font-display text-heading-xl font-bold">Run #{id}</h1>
        <p className="text-body-sm text-text-secondary">
          {humanise(run.data?.status ?? "")} · started {formatDateTime(run.data?.started_at)} ·{" "}
          <span className="tabular-nums">
            {run.data?.institutions_done ?? 0} of {run.data?.institutions_total ?? 0}
          </span>{" "}
          institutions
        </p>
        {run.data?.status !== "RUNNING" ? (
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => onRestart("all")} disabled={restartCrawl.isPending}>
              Restart
            </Button>
            {run.data?.retriable_count ? (
              <Button
                size="sm"
                onClick={() => onRestart("failures")}
                disabled={restartCrawl.isPending}
              >
                Retry {run.data.retriable_count} failure
                {run.data.retriable_count === 1 ? "" : "s"}
              </Button>
            ) : null}
          </div>
        ) : null}
      </header>

      <details>
        <summary className="cursor-pointer text-body-sm font-medium">Log</summary>
        <div className="mt-2">
          <CrawlLogPanel runId={id} />
        </div>
      </details>

      <Tabs
        value={tab}
        onChange={(_event, next: Tabname) => setTab(next)}
        aria-label="What changed"
        variant="scrollable"
        scrollButtons="auto"
        textColor="inherit"
      >
        {(["new", "changed", "disappeared"] as const).map((name) => (
          <Tab
            key={name}
            value={name}
            id={`tab-${name}`}
            aria-controls={`panel-${name}`}
            label={`${humanise(name)} (${counts[name]})`}
          />
        ))}
      </Tabs>

      <div id={`panel-${tab}`} role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {counts[tab] === 0 ? (
          <EmptyPanel
            title={`Nothing ${tab === "new" ? "new" : tab} in this run`}
            body="That is a result, not a failure — it means this run found no change of this kind."
          />
        ) : tab === "changed" ? (
          <DataTable<JobRevision>
            caption="Fields that changed in this run"
            columns={changeColumns}
            rows={diff.data.changed}
            rowKey={(row) => row.id}
          />
        ) : (
          <ol className="space-y-3">
            {(tab === "new" ? diff.data.new : diff.data.disappeared).map((job) => (
              <li key={job.id}>
                <JobCard job={job} />
              </li>
            ))}
          </ol>
        )}
      </div>

      {run.data?.institution_results?.some((result) => !result.permits_closure) ? (
        <Notice tone="info">
          Some institutions did not return a clean result in this run. No vacancies were closed for
          those — an unreachable portal is not evidence that its jobs are gone.
        </Notice>
      ) : null}

      <Toast message={toast?.message ?? null} tone={toast?.tone} onDismiss={() => setToast(null)} />
    </div>
  );
}
