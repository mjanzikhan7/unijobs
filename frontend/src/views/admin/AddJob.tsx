import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { Input } from "@/components/Field/Input";
import { Notice } from "@/components/Notice/Notice";
import { useAuth } from "@/viewmodels/auth";
import { EMPTY_JOB_FORM, JobForm } from "@/views/admin/JobForm";
import type { JobFormValues } from "@/views/admin/JobForm";
import { useInstitutions } from "@/viewmodels/useInstitutions";
import { useAddManualJob, useExtractJob } from "@/viewmodels/useJobs";

export function AddJob() {
  const navigate = useNavigate();
  const { role, assignedInstitutions } = useAuth();
  const institutions = useInstitutions();
  const extract = useExtractJob();
  const addJob = useAddManualJob();

  const [importUrl, setImportUrl] = useState("");
  const [values, setValues] = useState<JobFormValues>(EMPTY_JOB_FORM);
  const [extractNotice, setExtractNotice] = useState<string | null>(null);

  const institutionOptions = (institutions.data?.results ?? []).filter((institution) =>
    role === "RECRUITER" ? assignedInstitutions.includes(institution.slug) : true,
  );

  const onImport = () => {
    if (!importUrl.trim()) return;
    setExtractNotice(null);
    extract.mutate(importUrl.trim(), {
      onSuccess: (result) => {
        setValues((current) => ({
          ...current,
          source_url: result.draft.source_url ?? importUrl.trim(),
          title: result.draft.title ?? current.title,
          department: result.draft.department ?? current.department,
          location_raw: result.draft.location_raw ?? current.location_raw,
          salary_raw: result.draft.salary_raw ?? current.salary_raw,
          description_html: result.draft.description_html ?? current.description_html,
          closing_date: result.draft.closing_date ?? current.closing_date,
          posted_date: result.draft.posted_date ?? current.posted_date,
          reference: result.draft.reference ?? current.reference,
        }));
        if (!result.extracted) {
          setExtractNotice(
            result.reason
              ? `Could not read that page: ${result.reason}. Fill the rest in by hand.`
              : "Could not read that page. Fill the rest in by hand.",
          );
        }
      },
    });
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    addJob.mutate(values, {
      onSuccess: (job) => void navigate(`/jobs/${job.id}`),
    });
  };

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-content space-y-6 pb-24">
      <div>
        <Button variant="quiet" size="sm" onClick={() => void navigate("/admin/jobs")} type="button">
          ← Manage jobs
        </Button>
        <h1 className="mt-2 font-display text-heading-xl font-bold">Add a job by hand</h1>
        <p className="mt-1 text-body-sm text-text-secondary">
          For a portal the crawler cannot reach. Screened through the same pipeline as a crawled
          job, and never closed by crawl diffing.{" "}
          <span aria-hidden="true" className="text-danger">
            *
          </span>{" "}
          marks a required field.
        </p>
      </div>

      <Card as="section" className="space-y-3">
        <h2 className="font-display text-heading-sm font-semibold">Import from a URL</h2>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="min-w-0 flex-1">
            <label htmlFor="import-url" className="block text-body-sm font-medium text-text-primary">
              Paste the advert URL
            </label>
            <Input
              id="import-url"
              type="url"
              value={importUrl}
              onChange={(event) => setImportUrl(event.target.value)}
              placeholder="https://www.example.ac.uk/jobs/vacancy/123"
              className="mt-1"
            />
          </div>
          <Button
            type="button"
            variant="primary"
            onClick={onImport}
            disabled={extract.isPending || !importUrl.trim()}
          >
            {extract.isPending ? <Spinner label="Reading…" inline /> : "Read this page"}
          </Button>
        </div>
        <p className="text-caption text-text-muted">
          We will try to read the details. Check everything before saving.
        </p>
        {extractNotice ? <Notice tone="warning">{extractNotice}</Notice> : null}
        {extract.isError ? <ErrorMessage error={extract.error} /> : null}
      </Card>

      <Card as="section" className="space-y-4">
        <h2 className="font-display text-heading-sm font-semibold">The job</h2>
        <JobForm
          values={values}
          onChange={setValues}
          institutionOptions={institutionOptions}
          disabled={addJob.isPending}
        />
      </Card>

      <Notice tone="info">
        This will be screened for sponsorship and salary as soon as it is saved, exactly like a
        crawled job.
      </Notice>

      {addJob.isError ? <ErrorMessage error={addJob.error} /> : null}

      <div className="sticky bottom-0 -mx-4 flex justify-end gap-2 border-t border-border-subtle bg-surface px-4 py-3">
        <Button variant="quiet" type="button" onClick={() => void navigate("/admin/jobs")}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={addJob.isPending}>
          {addJob.isPending ? "Saving…" : "Save job"}
        </Button>
      </div>
    </form>
  );
}
