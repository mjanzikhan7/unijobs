import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Card } from "@/components/Card/Card";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { Input } from "@/components/Field/Input";
import { MonogramTile } from "@/components/MonogramTile/MonogramTile";
import { useInstitutions } from "@/viewmodels/useInstitutions";

export function InstitutionList() {
  const institutions = useInstitutions();
  const [term, setTerm] = useState("");

  const rows = useMemo(() => {
    const all = institutions.data?.results ?? [];
    const needle = term.trim().toLowerCase();
    const matching = needle
      ? all.filter(
          (row) =>
            row.name.toLowerCase().includes(needle) ||
            (row.city ?? "").toLowerCase().includes(needle),
        )
      : all;
    return [...matching].sort(
      (a, b) => (b.open_jobs ?? 0) - (a.open_jobs ?? 0) || a.name.localeCompare(b.name),
    );
  }, [institutions.data, term]);

  if (institutions.isLoading) return <Spinner label="Loading institutions" />;
  if (institutions.isError) {
    return <ErrorMessage error={institutions.error} onRetry={() => void institutions.refetch()} />;
  }

  return (
    <div className="mx-auto max-w-content space-y-4">
      <header className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-heading-xl font-bold">Institutions</h1>
        <label className="sr-only" htmlFor="institution-filter">
          Filter institutions
        </label>
        <Input
          id="institution-filter"
          type="search"
          placeholder="Filter by name or city"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          className="max-w-xs"
        />
        <p className="text-body-sm tabular-nums text-text-secondary">{rows.length} institutions</p>
      </header>

      {rows.length === 0 ? (
        <EmptyPanel
          title="No institutions match"
          body={`Nothing matched “${term}”. Try a shorter term, or a city.`}
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((institution) => (
            <Card as="li" key={institution.id} interactive padding="sm">
              <div className="flex items-start gap-3">
                <MonogramTile name={institution.name} />
                <div className="min-w-0 flex-1">
                  <Link
                    to={`/institutions/${institution.slug}`}
                    className="font-medium text-brand underline underline-offset-2 hover:decoration-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
                  >
                    {institution.name}
                  </Link>
                  <p className="mt-0.5 text-caption text-text-muted">
                    {[institution.city, institution.nation].filter(Boolean).join(" · ")}
                  </p>
                </div>
                <p className="shrink-0 text-body-sm tabular-nums text-text-secondary">
                  {institution.open_jobs ?? 0} open
                </p>
              </div>
            </Card>
          ))}
        </ul>
      )}
    </div>
  );
}
