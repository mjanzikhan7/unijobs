import { Link } from "react-router-dom";

import { Badge, SponsorBadge, ThresholdBadge } from "@/components/Badge/Badge";
import { Card } from "@/components/Card/Card";
import { ClosesBadge } from "@/components/ClosesBadge/ClosesBadge";
import { FitRing } from "@/components/FitRing/FitRing";
import { SalaryDisplay } from "@/components/SalaryDisplay/SalaryDisplay";
import type { Job } from "@/models/api/types";
import { DISCIPLINE_LABELS, formatDate, truncate } from "@/utilities/format";

interface JobCardProps {
  job: Job;
  isFocused?: boolean;
  onSave?: (job: Job) => void;
}

export function JobCard({ job, isFocused = false, onSave }: JobCardProps) {
  const screening = job.screening;

  return (
    <Card
      as="article"
      interactive
      data-testid="job-card"
      data-job-id={job.id}
      aria-current={isFocused ? "true" : undefined}
      className={isFocused ? "outline outline-2 outline-offset-2 outline-brand" : undefined}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="min-w-0 text-heading-sm font-semibold">
          <Link
            to={`/jobs/${job.id}`}
            className="text-brand underline underline-offset-2 hover:decoration-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
          >
            {truncate(job.title, 110)}
          </Link>
        </h3>
        <div className="flex shrink-0 items-center gap-2">
          <ClosesBadge value={job.closing_date} />
          {onSave ? (
            <button
              type="button"
              onClick={() => onSave(job)}
              aria-pressed={job.is_saved ?? false}
              aria-label={job.is_saved ? `Unsave ${job.title}` : `Save ${job.title}`}
              className="flex h-11 w-11 items-center justify-center rounded-full border border-border-strong text-body-lg text-text-secondary hover:border-brand hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              <span aria-hidden="true">{job.is_saved ? "★" : "☆"}</span>
            </button>
          ) : null}
        </div>
      </div>

      <p className="mt-1 text-body-sm text-text-secondary">
        {job.institution_name}
        {job.city ? <span className="text-text-muted"> · {job.city}</span> : null}
      </p>

      {job.discipline && job.discipline !== "OTHER" ? (
        <p className="mt-0.5 text-caption text-text-muted">
          {DISCIPLINE_LABELS[job.discipline]}
        </p>
      ) : null}

      <div className="mt-3">
        <SalaryDisplay screening={screening} raw={job.salary_raw} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <SponsorBadge
          verdict={screening?.sponsor_verdict}
          matchedName={screening?.sponsor_matched_name}
          advertExcludes={screening?.advert_excludes_sponsorship}
        />
        <ThresholdBadge
          verdict={screening?.threshold_verdict}
          explanation={screening?.threshold_explanation}
        />
        {job.status === "DISAPPEARED" ? (
          <Badge tone="unknown" title="No longer listed on the portal">
            No longer listed
          </Badge>
        ) : null}
        <span className="ml-auto">
          <FitRing score={job.fitness_score} size="sm" />
        </span>
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-body-sm text-text-secondary">
        <div className="flex gap-1">
          <dt className="text-text-muted">Posted</dt>
          <dd>{formatDate(job.posted_date)}</dd>
        </div>
        {job.grade_raw ? (
          <div className="flex gap-1">
            <dt className="text-text-muted">Grade</dt>
            <dd>{job.grade_raw}</dd>
          </div>
        ) : null}
      </dl>

      <div className="mt-4 flex items-center justify-between gap-3 border-t border-border-subtle pt-3 text-body-sm">
        <span
          className="min-w-0 truncate text-text-muted"
          title={job.source ? `Sourced via ${job.source.toLowerCase()}` : undefined}
        >
          via {job.institution_name}&rsquo;s own listing
        </span>
        <Link
          to={`/jobs/${job.id}`}
          className="shrink-0 font-medium text-brand underline underline-offset-2 hover:decoration-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
        >
          View details →
        </Link>
      </div>
    </Card>
  );
}
