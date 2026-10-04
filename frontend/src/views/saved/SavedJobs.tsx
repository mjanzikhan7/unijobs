import { Button } from "@/components/Button/Button";
import { Chip } from "@/components/Chip/Chip";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { JobCard } from "@/views/jobs/JobCard";
import { savedTags } from "@/models/api/types";
import { closingLabel } from "@/utilities/format";
import { useSavedJobs, useUnsaveJob } from "@/viewmodels/useSavedJobs";

export function SavedJobs() {
  const saved = useSavedJobs();
  const unsave = useUnsaveJob();

  if (saved.isLoading) return <Spinner label="Loading saved jobs" />;
  if (saved.isError)
    return <ErrorMessage error={saved.error} onRetry={() => void saved.refetch()} />;

  const rows = saved.data?.results ?? [];

  return (
    <div className="mx-auto max-w-narrow space-y-4">
      <header>
        <h1 className="font-display text-heading-xl font-bold">Saved jobs</h1>
        <p className="mt-1 text-body-sm text-text-secondary">
          Ordered by closing date — soonest first.
        </p>
      </header>

      {rows.length === 0 ? (
        <EmptyPanel
          title="Nothing saved yet"
          body={
            <>
              Press{" "}
              <kbd className="rounded-xs border border-border-strong bg-surface px-1.5 py-0.5 font-mono text-caption">
                s
              </kbd>{" "}
              on a job in the list to save it.
            </>
          }
        />
      ) : null}

      <ol className="space-y-3">
        {rows.map((row) => (
          <li key={row.id} className="flex flex-col gap-3 sm:flex-row sm:items-start">
            <div className="min-w-0 flex-1">
              <JobCard job={row.job_detail} />
            </div>
            <div className="flex shrink-0 flex-row flex-wrap items-center gap-2 sm:w-44 sm:flex-col sm:items-start">
              <p className="text-body-sm text-text-secondary">
                {closingLabel(row.job_detail.closing_date)}
              </p>
              {row.job_detail.status === "DISAPPEARED" ? (
                <Chip tone="unknown">No longer listed</Chip>
              ) : null}
              {savedTags(row).map((tag) => (
                <Chip key={tag}>{tag}</Chip>
              ))}
              <Button variant="quiet" size="sm" onClick={() => unsave.mutate(row.id)}>
                Remove
              </Button>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
