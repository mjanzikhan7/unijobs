import { Link, useParams } from "react-router-dom";

import { Card } from "@/components/Card/Card";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { Fact } from "@/components/Fact/Fact";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { Icon } from "@/components/Icon/Icon";
import { MonogramTile } from "@/components/MonogramTile/MonogramTile";
import { JobCard } from "@/views/jobs/JobCard";
import { useAuth } from "@/viewmodels/auth";
import { useInstitution } from "@/viewmodels/useInstitutions";
import { useJobs } from "@/viewmodels/useJobs";

export function InstitutionDetail() {
  const { slug = "" } = useParams();
  const { role } = useAuth();
  const institution = useInstitution(slug);
  const jobs = useJobs(`?institution=${encodeURIComponent(slug)}&status=OPEN`);

  if (institution.isLoading) return <Spinner label="Loading institution" />;
  if (institution.isError) {
    return <ErrorMessage error={institution.error} onRetry={() => void institution.refetch()} />;
  }
  if (!institution.data) {
    return (
      <EmptyPanel
        title="Not found"
        body="No institution with that name."
        action={
          <Link to="/institutions" className="text-brand underline underline-offset-2 hover:decoration-2">
            Back to all institutions
          </Link>
        }
      />
    );
  }

  const detail = institution.data;
  const results = jobs.data?.results ?? [];
  const sponsor = detail.sponsor_match;
  const hasContact = Boolean(detail.contact_email || detail.contact_phone || detail.address);

  return (
    <div className="mx-auto max-w-content space-y-6">
      {detail.banner_url ? (
        <img
          src={detail.banner_url}
          alt=""
          className="h-40 w-full rounded-md object-cover sm:h-56"
        />
      ) : (
        <div aria-hidden="true" className="h-40 w-full rounded-md bg-brand-subtle sm:h-56" />
      )}

      <p className="text-body-sm">
        <Link to="/institutions" className="text-brand underline underline-offset-2 hover:decoration-2">
          ← All institutions
        </Link>
      </p>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="min-w-0 flex-1 space-y-6">
          <header className="space-y-3">
            <div className="flex items-center gap-3">
              {detail.logo_url ? (
                <img
                  src={detail.logo_url}
                  alt={`${detail.name} logo`}
                  className="h-16 w-16 shrink-0 rounded-md object-contain"
                />
              ) : (
                <MonogramTile name={detail.name} size="lg" />
              )}
              <h1 className="font-display text-heading-xl font-bold">{detail.name}</h1>
            </div>

            <p className="text-body-sm text-text-secondary">
              {[detail.city, detail.nation, detail.institution_type].filter(Boolean).join(" · ")}
            </p>

            {detail.careers_url ? (
              <p className="text-body-sm">
                <a
                  href={detail.careers_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="inline-flex items-center gap-1 text-brand underline underline-offset-2 hover:decoration-2"
                >
                  Their own careers site
                  <Icon name="external-link" className="h-4 w-4" />
                </a>
              </p>
            ) : null}

            {role === "ADMIN" ? (
              <p className="text-body-sm">
                <Link
                  to={`/admin/institutions?edit=${encodeURIComponent(detail.slug)}`}
                  className="text-brand underline underline-offset-2 hover:decoration-2"
                >
                  Edit banner, logo, about &amp; contact details
                </Link>
              </p>
            ) : null}
          </header>

          {detail.description ? (
            <section>
              <h2 className="font-display text-heading-md font-semibold">About</h2>
              <p className="mt-2 max-w-prose text-body whitespace-pre-line text-text-secondary">
                {detail.description}
              </p>
            </section>
          ) : null}

          <section className="space-y-3">
            <h2 className="font-display text-heading-md font-semibold">Open vacancies</h2>
            {jobs.isLoading ? <Spinner label="Loading vacancies" /> : null}
            {jobs.isError ? (
              <ErrorMessage error={jobs.error} onRetry={() => void jobs.refetch()} />
            ) : null}

            {!jobs.isLoading && results.length === 0 ? (
              <EmptyPanel
                title="Nothing open here at the moment"
                body="Vacancies appear here as soon as the next crawl finds them."
              />
            ) : (
              <ol className="space-y-3">
                {results.map((job) => (
                  <li key={job.id}>
                    <JobCard job={job} />
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>

        <aside className="w-full shrink-0 space-y-4 lg:w-80">
          <Card as="section" aria-label="Key facts" className="space-y-3">
            <h2 className="font-display text-heading-sm font-semibold">Key facts</h2>
            <dl className="space-y-3">
              <Fact label="Sponsor licence" value={sponsor?.verdict ?? "Unknown"} />
              {sponsor?.registered_legal_name ? (
                <Fact label="Registered as" value={sponsor.registered_legal_name} />
              ) : null}
              <Fact label="Open vacancies" value={jobs.data?.count ?? 0} />
            </dl>
          </Card>

          {hasContact ? (
            <Card as="section" aria-label="Contact" className="space-y-3">
              <h2 className="font-display text-heading-sm font-semibold">Contact</h2>
              <ul className="space-y-2 text-body-sm text-text-secondary">
                {detail.contact_email ? (
                  <li className="flex items-start gap-2">
                    <Icon name="mail" className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
                    <a href={`mailto:${detail.contact_email}`} className="text-brand underline underline-offset-2 hover:decoration-2">
                      {detail.contact_email}
                    </a>
                  </li>
                ) : null}
                {detail.contact_phone ? (
                  <li className="flex items-start gap-2">
                    <Icon name="phone" className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
                    <a
                      href={`tel:${detail.contact_phone.replace(/\s+/g, "")}`}
                      className="text-brand underline underline-offset-2 hover:decoration-2"
                    >
                      {detail.contact_phone}
                    </a>
                  </li>
                ) : null}
                {detail.address ? (
                  <li className="flex items-start gap-2">
                    <Icon name="map-pin" className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
                    <span className="whitespace-pre-line">{detail.address}</span>
                  </li>
                ) : null}
              </ul>
            </Card>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
