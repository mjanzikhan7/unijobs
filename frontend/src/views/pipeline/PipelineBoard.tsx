import { useState } from "react";

import { Card } from "@/components/Card/Card";
import { Chip } from "@/components/Chip/Chip";
import { Select } from "@/components/Field/Select";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { SegmentedControl } from "@/components/SegmentedControl/SegmentedControl";
import type { Application, ApplicationStatus } from "@/models/api/types";
import { formatDate } from "@/utilities/format";
import { useBoard, useMoveApplication } from "@/viewmodels/useBoard";

const statusRule: Record<string, string> = {
  FOUND: "var(--color-status-found-text)",
  READY: "var(--color-status-ready-text)",
  APPLIED: "var(--color-status-applied-text)",
  ACKNOWLEDGED: "var(--color-status-acknowledged-text)",
  INTERVIEW: "var(--color-status-interview-text)",
  OFFER: "var(--color-status-offer-text)",
  REJECTED: "var(--color-status-rejected-text)",
  GHOSTED: "var(--color-status-ghosted-text)",
};

export function PipelineBoard() {
  const board = useBoard();
  const move = useMoveApplication();
  const [dragging, setDragging] = useState<number | null>(null);
  const [mobileColumn, setMobileColumn] = useState<string | null>(null);

  if (board.isLoading) return <Spinner label="Loading pipeline" />;
  if (board.isError)
    return <ErrorMessage error={board.error} onRetry={() => void board.refetch()} />;

  const columns = board.data?.columns ?? [];
  const moveTargets = columns.map((item) => ({ status: item.status, label: item.label }));
  const shown = mobileColumn ?? columns[0]?.status ?? null;

  return (
    <div className="space-y-4">
      <h1 className="font-display text-heading-xl font-bold">Pipeline</h1>

      {shown ? (
        <div className="-mx-4 overflow-x-auto px-4 md:hidden">
          <SegmentedControl
            label="Show column"
            name="pipeline-column"
            value={shown}
            onChange={setMobileColumn}
            options={columns.map((column) => ({
              value: column.status,
              label: `${column.label} ${column.applications.length}`,
            }))}
          />
        </div>
      ) : null}

      <div
        tabIndex={0}
        role="region"
        aria-label="Pipeline columns"
        className="flex gap-3 md:overflow-x-auto md:pb-2"
      >
        {columns.map((column) => (
          <section
            key={column.status}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => {
              if (dragging !== null) move.mutate({ id: dragging, status: column.status });
              setDragging(null);
            }}
            aria-label={`${column.label}, ${column.applications.length} applications`}
            style={{ borderTopColor: statusRule[column.status] }}
            className={`w-full shrink-0 rounded-md border border-t-2 border-border-subtle bg-surface-sunken p-3 md:w-60 ${
              column.status === shown ? "" : "hidden md:block"
            }`}
          >
            <h2 className="flex items-baseline justify-between gap-2 text-body-sm font-semibold">
              {column.label}
              <span className="tabular-nums text-text-muted">{column.applications.length}</span>
            </h2>

            {column.applications.length === 0 ? (
              <p className="mt-3 rounded-sm border border-dashed border-border-subtle px-3 py-6 text-center text-caption text-text-muted">
                Nothing here yet
              </p>
            ) : (
              <ul className="mt-3 space-y-2">
                {column.applications.map((application) => (
                  <li key={application.id}>
                    <ApplicationCard
                      application={application}
                      columns={moveTargets}
                      onDragStart={() => setDragging(application.id)}
                      onMove={(status) => move.mutate({ id: application.id, status })}
                    />
                  </li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

interface CardProps {
  application: Application;
  columns: Array<{ status: string; label: string }>;
  onDragStart: () => void;
  onMove: (status: ApplicationStatus) => void;
}

function ApplicationCard({ application, columns, onDragStart, onMove }: CardProps) {
  const job = application.job_detail;

  return (
    <Card as="article" padding="sm" draggable onDragStart={onDragStart} className="space-y-1.5">
      <h3 className="text-body-sm font-semibold">{job.title}</h3>
      <p className="text-caption text-text-muted">{job.institution_name}</p>

      {application.ghosted_flagged ? (
        <Chip tone="caution">Possibly ghosted</Chip>
      ) : null}

      {application.next_action ? (
        <p className="text-caption text-text-secondary">
          {application.next_action}
          {application.next_action_due ? ` · due ${formatDate(application.next_action_due)}` : ""}
        </p>
      ) : null}

      {application.applied_at ? (
        <p className="text-caption text-text-muted">Applied {formatDate(application.applied_at)}</p>
      ) : null}

      <label className="sr-only" htmlFor={`move-${application.id}`}>
        Move {job.title} to another column
      </label>
      <Select
        id={`move-${application.id}`}
        value={application.status}
        onChange={(event) => onMove(event.target.value as ApplicationStatus)}
        className="h-9 text-caption"
      >
        {columns.map((column) => (
          <option key={column.status} value={column.status}>
            {column.label}
          </option>
        ))}
      </Select>
    </Card>
  );
}
