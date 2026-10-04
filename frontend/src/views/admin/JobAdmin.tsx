import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Badge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { Select } from "@/components/Field/Select";
import { Input } from "@/components/Field/Input";
import { ErrorMessage } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import { Pagination } from "@/components/Pagination/Pagination";
import { ApiError } from "@/models/api/client";
import type { Job } from "@/models/api/types";
import { useAuth } from "@/viewmodels/auth";
import { formatDate } from "@/utilities/format";
import { useDeleteJob, useJobs, useReinstateJob, useWithdrawJob } from "@/viewmodels/useJobs";

const filterLabel = "block text-body-sm font-medium text-text-primary";

export function JobAdmin() {
  const navigate = useNavigate();
  const { role, assignedInstitutions } = useAuth();
  const [source, setSource] = useState<"" | "PORTAL" | "MANUAL">("");
  const [status, setStatus] = useState<"" | "OPEN" | "WITHDRAWN" | "DISAPPEARED">("OPEN");
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  function changeFilter<T>(set: (value: T) => void) {
    return (value: T) => {
      set(value);
      setPage(1);
    };
  }

  const query = new URLSearchParams();
  if (source) query.set("source", source);
  if (status) query.set("status", status);
  if (term.trim()) query.set("q", term.trim());
  if (role === "RECRUITER") {
    for (const slug of assignedInstitutions) query.append("institution", slug);
  }
  query.set("page", String(page));
  query.set("page_size", String(pageSize));
  const jobs = useJobs(`?${query.toString()}`);

  const totalPages = jobs.data?.total_pages ?? 1;
  const count = jobs.data?.count ?? 0;
  const shown = jobs.data?.results.length ?? 0;

  const withdraw = useWithdrawJob();
  const reinstate = useReinstateJob();
  const remove = useDeleteJob();

  const refusal = [withdraw.error, reinstate.error, remove.error].find(
    (error): error is ApiError => error instanceof ApiError,
  );

  const columns: DataTableColumn<Job>[] = [
    {
      key: "title",
      header: "Title",
      isRowHeader: true,
      cell: (job) => (
        <Link to={`/jobs/${job.id}`} className="text-brand underline underline-offset-2 hover:decoration-2">
          {job.title}
        </Link>
      ),
    },
    {
      key: "institution",
      header: "Institution",
      cell: (job) => (
        <Link to={`/institutions/${job.institution_slug}`} className="text-brand underline underline-offset-2 hover:decoration-2">
          {job.institution_name}
        </Link>
      ),
    },
    {
      key: "origin",
      header: "Origin",
      cell: (job) =>
        job.source !== "MANUAL" ? (
          <Badge tone="neutral">crawled</Badge>
        ) : (
          <Badge tone="unknown">by hand</Badge>
        ),
    },
    { key: "status", header: "Status", cell: (job) => job.status },
    {
      key: "closing",
      header: "Closing",
      numeric: true,
      cell: (job) => formatDate(job.closing_date),
    },
    {
      key: "actions",
      header: "Actions",
      cell: (job) => (
        <span className="flex flex-wrap gap-1">
          {job.status === "WITHDRAWN" ? (
            <Button variant="quiet" size="sm" onClick={() => reinstate.mutate(job.id)}>
              Reinstate
            </Button>
          ) : (
            <Button
              variant="quiet"
              size="sm"
              onClick={() => withdraw.mutate({ id: job.id, reason: "" })}
            >
              Withdraw
            </Button>
          )}

          {job.source === "MANUAL" ? (
            <>
              <Link
                to={`/admin/jobs/${job.id}/edit`}
                className="inline-flex h-9 items-center rounded-md px-3 text-body-sm font-semibold text-brand hover:bg-brand-subtle"
              >
                Edit
              </Link>
              <Button variant="quiet" size="sm" onClick={() => remove.mutate(job.id)}>
                Delete
              </Button>
            </>
          ) : null}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="font-display text-heading-xl font-bold">Manage jobs</h1>
        <Button variant="primary" onClick={() => void navigate("/admin/jobs/new")}>
          Add job
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-48 flex-1">
          <label htmlFor="job-admin-q" className={filterLabel}>
            Search
          </label>
          <Input
            id="job-admin-q"
            type="search"
            value={term}
            onChange={(event) => changeFilter(setTerm)(event.target.value)}
            className="mt-1"
          />
        </div>

        <div>
          <label htmlFor="job-admin-source" className={filterLabel}>
            Origin
          </label>
          <Select
            id="job-admin-source"
            value={source}
            onChange={(event) => changeFilter(setSource)(event.target.value as typeof source)}
            className="mt-1 w-auto"
          >
            <option value="">All</option>
            <option value="PORTAL">Crawled</option>
            <option value="MANUAL">Added by hand</option>
          </Select>
        </div>

        <div>
          <label htmlFor="job-admin-status" className={filterLabel}>
            Status
          </label>
          <Select
            id="job-admin-status"
            value={status}
            onChange={(event) => changeFilter(setStatus)(event.target.value as typeof status)}
            className="mt-1 w-auto"
          >
            <option value="OPEN">Open</option>
            <option value="WITHDRAWN">Withdrawn</option>
            <option value="DISAPPEARED">No longer listed</option>
            <option value="">Any</option>
          </Select>
        </div>

        <div>
          <label htmlFor="job-admin-page-size" className={filterLabel}>
            Per page
          </label>
          <Select
            id="job-admin-page-size"
            value={pageSize}
            onChange={(event) => changeFilter(setPageSize)(Number(event.target.value))}
            className="mt-1 w-auto"
          >
            {[25, 50, 100, 200].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {refusal ? <Notice tone="warning">{refusal.message}</Notice> : null}

      {jobs.isError ? <ErrorMessage error={jobs.error} onRetry={() => void jobs.refetch()} /> : null}

      <p className="text-body-sm tabular-nums text-text-secondary">
        {count === 0
          ? "No jobs match these filters."
          : `Showing ${shown} of ${count} jobs — page ${jobs.data?.page ?? 1} of ${totalPages}`}
      </p>

      <DataTable<Job>
        caption="Jobs"
        columns={columns}
        rows={jobs.data?.results ?? []}
        rowKey={(job) => job.id}
        loading={jobs.isLoading}
        emptyTitle="No jobs match these filters"
        emptyBody="Widen the search, or set Status to Any."
      />

      <Pagination
        label="Jobs"
        page={jobs.data?.page ?? 1}
        totalPages={totalPages}
        hasPrevious={Boolean(jobs.data?.previous)}
        hasNext={Boolean(jobs.data?.next)}
        onChange={setPage}
      />
    </div>
  );
}
