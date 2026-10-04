import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Badge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { ConfirmDialog } from "@/components/ConfirmDialog/ConfirmDialog";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import { EMPTY_JOB_FORM, JobForm } from "@/views/admin/JobForm";
import type { JobFormValues } from "@/views/admin/JobForm";
import { formatDate } from "@/utilities/format";
import { useDeleteJob, useJob, useUpdateJob } from "@/viewmodels/useJobs";

export function EditJob() {
  const navigate = useNavigate();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const job = useJob(id);
  const update = useUpdateJob();
  const remove = useDeleteJob();

  const [values, setValues] = useState<JobFormValues>(EMPTY_JOB_FORM);
  const [dateError, setDateError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const [loadedFrom, setLoadedFrom] = useState<typeof job.data>(undefined);
  if (job.data && job.data !== loadedFrom) {
    setLoadedFrom(job.data);
    const detail = job.data;
    setValues({
      institution: detail.institution_slug,
      source_url: detail.source_url,
      title: detail.title,
      department: detail.department ?? "",
      category: detail.category ?? "",
      reference: detail.reference ?? "",
      location_raw: detail.location_raw ?? "",
      city: detail.city ?? "",
      salary_raw: detail.salary_raw ?? "",
      grade_raw: detail.grade_raw ?? "",
      contract_raw: detail.contract_raw ?? "",
      hours_raw: detail.hours_raw ?? "",
      contract_type: detail.contract_type ?? "",
      hours: detail.hours ?? "",
      workplace: detail.workplace ?? "",
      discipline: detail.discipline && detail.discipline !== "OTHER" ? detail.discipline : "",
      description_html: detail.description_html ?? "",
      closing_date: detail.closing_date ?? null,
      posted_date: detail.posted_date ?? null,
    });
  }

  if (job.isLoading) return <Spinner label="Loading job" />;
  if (job.isError) return <ErrorMessage error={job.error} onRetry={() => void job.refetch()} />;
  if (!job.data) return null;

  const detail = job.data;

  if (detail.source !== "MANUAL") {
    return (
      <div className="mx-auto max-w-content space-y-4">
        <Button variant="quiet" size="sm" onClick={() => void navigate("/admin/jobs")} type="button">
          ← Manage jobs
        </Button>
        <Notice tone="warning">
          This advert came from a crawl and is the employer&rsquo;s text. The next crawl would
          overwrite an edit and recreate a deletion.
        </Notice>
        <div className="flex gap-2">
          <Button variant="quiet" onClick={() => void navigate("/admin/jobs")}>
            Back to Manage jobs
          </Button>
          <Button variant="primary" onClick={() => void navigate(`/jobs/${detail.id}`)}>
            Withdraw it instead
          </Button>
        </div>
      </div>
    );
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (
      values.posted_date &&
      values.closing_date &&
      values.closing_date < values.posted_date
    ) {
      setDateError("The closing date cannot be before the posted date.");
      return;
    }
    setDateError(null);

    const changes: Partial<JobFormValues> = { ...values };
    delete changes.institution;
    delete changes.source_url;
    update.mutate({ id, changes }, { onSuccess: () => void navigate(`/jobs/${id}`) });
  };

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-content space-y-6 pb-24">
      <div>
        <Button variant="quiet" size="sm" onClick={() => void navigate("/admin/jobs")} type="button">
          ← Manage jobs
        </Button>
        <div className="mt-2 flex items-center gap-2">
          <h1 className="font-display text-heading-xl font-bold">Edit job</h1>
          <Badge tone="unknown">By hand</Badge>
        </div>
        <p className="mt-1 text-body-sm text-text-secondary">
          Only jobs added by hand can be edited. A crawled advert is the employer&rsquo;s text.{" "}
          <span aria-hidden="true" className="text-danger">
            *
          </span>{" "}
          marks a required field.
        </p>
      </div>

      <Card as="section" className="space-y-4">
        <JobForm
          values={values}
          onChange={setValues}
          institutionOptions={[]}
          lockedInstitution={{
            slug: detail.institution_slug,
            name: detail.institution_name,
          }}
          disabled={update.isPending}
        />
      </Card>

      {dateError ? <Notice tone="danger">{dateError}</Notice> : null}
      {update.isError ? <ErrorMessage error={update.error} /> : null}
      {remove.isError ? <ErrorMessage error={remove.error} /> : null}

      <p className="text-caption text-text-muted">
        {detail.screening?.ruleset_version
          ? `Last screened ${formatDate(detail.screening.screened_at)} · ruleset v${detail.screening.ruleset_version}. `
          : ""}
        Saving re-screens this job.
      </p>

      <div className="sticky bottom-0 -mx-4 flex flex-wrap items-center gap-2 border-t border-border-subtle bg-surface px-4 py-3">
        <Button variant="quiet" type="button" onClick={() => void navigate("/admin/jobs")}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save changes"}
        </Button>
        <Button
          variant="danger"
          type="button"
          className="sm:ml-auto"
          onClick={() => setConfirmingDelete(true)}
        >
          Delete this job
        </Button>
      </div>

      <ConfirmDialog
        open={confirmingDelete}
        title="Delete this job?"
        description="This job was added by hand, so it will not come back on the next crawl. Any candidate who saved it will lose it."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={() => {
          setConfirmingDelete(false);
          remove.mutate(id, { onSuccess: () => void navigate("/admin/jobs") });
        }}
        onCancel={() => setConfirmingDelete(false)}
      />
    </form>
  );
}
