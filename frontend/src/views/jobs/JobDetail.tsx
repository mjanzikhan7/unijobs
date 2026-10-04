import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { SponsorBadge, ThresholdBadge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { Chip } from "@/components/Chip/Chip";
import { ConfirmDialog } from "@/components/ConfirmDialog/ConfirmDialog";
import { Fact } from "@/components/Fact/Fact";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { FitRing } from "@/components/FitRing/FitRing";
import { Icon } from "@/components/Icon/Icon";
import { Notice } from "@/components/Notice/Notice";
import { fitnessReasons, jobRevisions } from "@/models/api/types";
import {
  closingLabel,
  daysUntil,
  DISCIPLINE_LABELS,
  formatDate,
  humanise,
  money,
  salaryRange,
} from "@/utilities/format";
import { useCreateApplication, useMoveApplication } from "@/viewmodels/useBoard";
import { useJob } from "@/viewmodels/useJobs";
import { useSaveJob } from "@/viewmodels/useSavedJobs";

const sectionHeading = "font-display text-heading-md font-semibold";
const factGrid = "mt-3 grid gap-x-6 gap-y-4 sm:grid-cols-2";

export function JobDetail() {
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = Number(params.id);
  const job = useJob(id);
  const saveJob = useSaveJob();
  const createApplication = useCreateApplication();
  const moveApplication = useMoveApplication();
  const [confirmingApply, setConfirmingApply] = useState(false);

  if (job.isLoading) return <Spinner label="Loading vacancy" />;
  if (job.isError) return <ErrorMessage error={job.error} onRetry={() => void job.refetch()} />;
  if (!job.data) return null;

  const detail = job.data;
  const screening = detail.screening;
  const reasons = fitnessReasons(detail);
  const revisions = jobRevisions(detail);

  function recordApplyDecision(applied: boolean) {
    const status = applied ? "APPLIED" : "FOUND";
    if (detail.application_id) {
      moveApplication.mutate({ id: detail.application_id, status });
    } else {
      createApplication.mutate({ job: detail.id, status });
    }
    setConfirmingApply(false);
  }

  const verdicts = (
    <div className="flex flex-wrap items-center gap-2">
      <SponsorBadge
        verdict={screening?.sponsor_verdict}
        matchedName={screening?.sponsor_matched_name}
        advertExcludes={screening?.advert_excludes_sponsorship}
      />
      <ThresholdBadge
        verdict={screening?.threshold_verdict}
        explanation={screening?.threshold_explanation}
      />
    </div>
  );

  const applyLink = (
    <a
      href={detail.apply_url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => setConfirmingApply(true)}
      className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-md border border-cta bg-cta px-4 font-semibold text-text-inverse transition-colors duration-[var(--duration-fast)] ease-[var(--ease-out)] hover:border-[var(--color-cta-hover)] hover:bg-[var(--color-cta-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
    >
      Apply on the employer&rsquo;s site ↗
    </a>
  );

  const saveButton = (
    <Button
      className="w-full"
      onClick={() => saveJob.mutate(detail.id)}
      disabled={detail.is_saved ?? false}
    >
      {detail.is_saved ? "Saved" : "Save"}
    </Button>
  );

  return (
    <article className="mx-auto max-w-content pb-24 lg:pb-0">
      <Button
        variant="quiet"
        size="sm"
        type="button"
        onClick={() => void navigate(-1)}
        className="mb-4"
      >
        <Icon name="chevron-left" className="h-4 w-4" />
        Back to results
      </Button>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="min-w-0 flex-1 space-y-8">
          <header className="space-y-3">
            <h1 className="font-display text-heading-xl font-bold">{detail.title}</h1>
            <p className="text-body-sm text-text-secondary">
              <Link
                to={`/institutions/${detail.institution_slug}`}
                className="font-medium text-brand underline underline-offset-2 hover:decoration-2"
              >
                {detail.institution_name}
              </Link>
              {detail.department ? ` · ${detail.department}` : ""}
              {detail.category ? ` · ${detail.category}` : ""}
              {detail.location_raw ? ` · ${detail.location_raw}` : ""}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              {verdicts}
              <span className="flex items-center gap-2">
                <FitRing score={detail.fitness_score} size="md" />
                <span className="text-caption text-text-muted">Fit</span>
              </span>
            </div>
          </header>

          <Card as="section" aria-label="Key facts">
            <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
              <Fact label="Location" value={detail.location_raw || detail.city} />
              <Fact label="Salary as advertised" value={detail.salary_raw || "Not stated"} />
              <Fact label="Salary parsed" value={salaryRange(screening)} />
              <Fact label="Screened on" value={money(screening?.screened_on)} />
              <Fact label="Grade" value={detail.grade_raw} />
              <Fact
                label="Discipline"
                value={
                  detail.discipline && detail.discipline !== "OTHER"
                    ? DISCIPLINE_LABELS[detail.discipline]
                    : undefined
                }
              />
              <Fact
                label="Contract"
                value={
                  detail.contract_raw
                    ? `${humanise(detail.contract_type ?? "UNKNOWN")} — advertised as “${detail.contract_raw}”`
                    : humanise(detail.contract_type ?? "UNKNOWN")
                }
              />
              <Fact
                label="Hours"
                value={
                  detail.hours_raw
                    ? `${humanise(detail.hours ?? "UNKNOWN")} — advertised as “${detail.hours_raw}”`
                    : humanise(detail.hours ?? "UNKNOWN")
                }
              />
              <Fact label="Workplace" value={humanise(detail.workplace ?? "UNKNOWN")} />
              <Fact label="Posted" value={formatDate(detail.posted_date)} />
              <Fact
                label="Closing"
                value={closingLabel(detail.closing_date)}
                danger={daysUntil(detail.closing_date) === 0}
              />
              <Fact label="Reference" value={detail.reference} />
            </dl>
          </Card>

          {detail.status === "DISAPPEARED" ? (
            <Notice tone="warning">
              <strong>No longer listed.</strong> This vacancy was last seen on{" "}
              {formatDate(detail.last_seen_at)}. The link may be dead — but adverts do move, so it
              is still worth a look.
            </Notice>
          ) : null}

          {screening?.advert_excludes_sponsorship ? (
            <Notice tone="danger" quote={screening.advert_exclusion_phrase}>
              <strong>This advert rules sponsorship out.</strong> That is evidence about this post
              specifically, and it overrides the employer&rsquo;s register entry. Applying is
              still your decision.
            </Notice>
          ) : null}

          <section>
            <h2 className={sectionHeading}>Why these verdicts</h2>
            <dl className={factGrid}>
              <Fact
                label="Sponsorship"
                value={
                  screening?.sponsor_matched_name
                    ? `Matched to “${screening.sponsor_matched_name}” on the sponsor register.`
                    : "No entry on the sponsor register matched this institution."
                }
              />
              <Fact label="Salary band" value={screening?.threshold_explanation} />
              <Fact
                label="Rules in force"
                value={
                  screening?.ruleset_version
                    ? `Ruleset v${screening.ruleset_version}, applied ${formatDate(screening.screened_at)}`
                    : null
                }
              />
              <Fact
                label="Immigration Rules"
                value={statutoryLabel(screening?.general_threshold_met, screening?.going_rate_met)}
              />
            </dl>
          </section>

          {reasons.length > 0 ? (
            <section>
              <h2 className={sectionHeading}>Fitness, and the gaps</h2>
              <p className="mt-1 text-body-sm text-text-muted">
                Fitness ranks what is already takeable. It never changes the sponsorship verdict.
              </p>
              <ul className="mt-3 space-y-2 text-body-sm">
                {reasons.map((reason) => (
                  <li key={reason.criterion}>
                    <strong>{humanise(reason.criterion)}</strong> ×{reason.weight} —{" "}
                    <span className="tabular-nums">{Math.round(reason.fraction * 100)}%</span>
                    {reason.matched?.length ? (
                      <span className="text-text-secondary"> · matched: {reason.matched.join(", ")}</span>
                    ) : null}
                    {reason.missing?.length ? (
                      <span className="text-danger"> · missing: {reason.missing.join(", ")}</span>
                    ) : null}
                    {reason.note ? (
                      <span className="text-text-muted"> {reason.note}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section>
            <h2 className={sectionHeading}>The advert</h2>
            {detail.description_html ? (
              <pre
                tabIndex={0}
                role="region"
                aria-label="The advert, as the employer published it"
                className="mt-3 max-h-[540px] overflow-auto rounded-md border border-border-subtle bg-surface-sunken p-4 font-sans text-body-sm whitespace-pre-wrap text-text-secondary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
              >
                {detail.description_text}
              </pre>
            ) : (
              <p className="mt-3 text-body-sm text-text-secondary">
                No description was captured. Follow the link above to read it on the portal.
              </p>
            )}
          </section>

          {detail.category ? (
            <section>
              <h2 className={sectionHeading}>Advert information</h2>
              <dl className="mt-3 flex flex-wrap items-center gap-2 text-body-sm">
                <dt className="text-text-secondary">Category</dt>
                <dd>
                  <Chip>{detail.category}</Chip>
                </dd>
              </dl>
            </section>
          ) : null}

          {revisions.length > 0 ? (
            <section>
              <h2 className={sectionHeading}>What has changed</h2>
              <ul className="mt-3 space-y-2 text-body-sm">
                {revisions.map((revision, index) => (
                  <li key={`${revision.field}-${index}`}>
                    <strong>{humanise(revision.field)}</strong> on{" "}
                    {formatDate(revision.changed_at)}:{" "}
                    <del className="text-danger">{revision.before || "—"}</del> →{" "}
                    <ins className="text-success no-underline">{revision.after || "—"}</ins>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        <aside
          aria-label="Apply"
          className={[
            "fixed inset-x-0 bottom-0 z-30 flex gap-2 border-t border-border-subtle bg-surface px-4 py-3",
            "lg:static lg:z-auto lg:block lg:w-80 lg:shrink-0 lg:space-y-3 lg:border-0 lg:p-0",
          ].join(" ")}
        >
          <Card className="flex-1 border-0 bg-transparent p-0 shadow-none lg:sticky lg:top-20 lg:space-y-3 lg:border lg:bg-surface lg:p-5 lg:shadow-xs">
            <div className="flex gap-2 lg:block lg:space-y-3">
              <div className="min-w-0 flex-1">{applyLink}</div>
              <div className="w-28 lg:w-auto">{saveButton}</div>
            </div>
          </Card>
        </aside>
      </div>

      <ConfirmDialog
        open={confirmingApply}
        title="Did you apply to this job?"
        description="This only updates your own Pipeline board — nothing is sent to the employer from here."
        confirmLabel="Yes, mark Applied"
        cancelLabel="Not yet"
        onConfirm={() => recordApplyDecision(true)}
        onCancel={() => recordApplyDecision(false)}
      />
    </article>
  );
}

function statutoryLabel(
  generalMet: boolean | null | undefined,
  goingRateMet: boolean | null | undefined,
): string {
  if (generalMet === null || generalMet === undefined) {
    return "Cannot be assessed — the advertised salary could not be read.";
  }
  if (generalMet && goingRateMet) return "Clears the general threshold and the going rate.";
  if (generalMet) return "Clears the general threshold but not the occupation going rate.";
  return "Below the general threshold for the Skilled Worker route.";
}
