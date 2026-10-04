import { useState } from "react";

import { Button } from "@/components/Button/Button";
import { Card } from "@/components/Card/Card";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { Input } from "@/components/Field/Input";
import { Select } from "@/components/Field/Select";
import { ErrorMessage, Spinner, Toast } from "@/components/Feedback";
import { sponsorCandidates } from "@/models/api/types";
import type { Institution, SponsorVerdict } from "@/models/api/types";
import { SPONSOR_LABELS } from "@/utilities/format";
import { useRegisterSearch, useResolveSponsor, useReviewQueue } from "@/viewmodels/useInstitutions";

const VERDICT_OPTIONS: SponsorVerdict[] = [
  "CONFIRMED",
  "CONFIRMED_VIA_PARENT",
  "B_RATED",
  "PROVISIONAL",
  "OTHER_ROUTE_ONLY",
  "NOT_FOUND",
];

const MIN_SEARCH_LENGTH = 3;

const candidateRow =
  "flex min-h-11 cursor-pointer flex-wrap items-center gap-2 rounded-sm px-2 py-1 text-body-sm hover:bg-surface-sunken";

export function ReviewQueue() {
  const queue = useReviewQueue();
  const [toast, setToast] = useState<string | null>(null);

  if (queue.isLoading) return <Spinner label="Loading review queue" />;
  if (queue.isError)
    return <ErrorMessage error={queue.error} onRetry={() => void queue.refetch()} />;

  const rows = queue.data ?? [];

  return (
    <div className="mx-auto max-w-narrow space-y-4">
      <header>
        <h1 className="font-display text-heading-xl font-bold">Sponsor review queue</h1>
        <p className="mt-1 text-body-sm text-text-secondary">
          {rows.length} institution{rows.length === 1 ? "" : "s"} whose legal entity has not been
          confirmed. Each answer is remembered, so the question is asked once.
        </p>
      </header>

      {rows.length === 0 ? (
        <EmptyPanel
          title="Nothing to review"
          body="Every institution has a confirmed sponsor verdict."
        />
      ) : null}

      <ul className="space-y-4">
        {rows.map((institution) => (
          <li key={institution.id}>
            <ReviewRow institution={institution} onResolved={setToast} />
          </li>
        ))}
      </ul>

      <Toast message={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}

function ReviewRow({
  institution,
  onResolved,
}: {
  institution: Institution;
  onResolved: (message: string) => void;
}) {
  const resolve = useResolveSponsor();
  const [search, setSearch] = useState("");
  const [chosen, setChosen] = useState(institution.sponsor_match?.registered_legal_name ?? "");
  const [verdict, setVerdict] = useState<SponsorVerdict>("CONFIRMED");

  const registerResults = useRegisterSearch(search, MIN_SEARCH_LENGTH);

  const suggestions = sponsorCandidates(institution.sponsor_match);

  return (
    <Card as="article" className="space-y-4">
      <div>
        <h2 className="font-display text-heading-sm font-semibold">{institution.name}</h2>
        <p className="mt-1 text-body-sm text-text-secondary">
          {institution.city} · {institution.nation} ·{" "}
          <a
            href={institution.careers_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand underline underline-offset-2 hover:decoration-2"
          >
            careers page ↗
          </a>
        </p>
      </div>

      {suggestions.length > 0 ? (
        <div>
          <h3 className="text-overline font-semibold tracking-wide text-text-muted uppercase">
            Suggested entries
          </h3>
          <ul className="mt-1">
            {suggestions.map((candidate) => (
              <li key={candidate.organisation_name}>
                <label className={candidateRow}>
                  <input
                    type="radio"
                    name={`candidate-${institution.id}`}
                    value={candidate.organisation_name}
                    checked={chosen === candidate.organisation_name}
                    onChange={() => setChosen(candidate.organisation_name)}
                    className="h-4 w-4 accent-[var(--color-brand)]"
                  />
                  <strong>{candidate.organisation_name}</strong>
                  {candidate.town_city ? (
                    <span className="text-text-secondary">· {candidate.town_city}</span>
                  ) : null}
                  {candidate.type_rating ? (
                    <span className="text-text-secondary">· {candidate.type_rating}</span>
                  ) : null}
                  <span className="ml-auto text-caption tabular-nums text-text-muted">
                    {Math.round((candidate.similarity ?? 0) * 100)}% similar
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-body-sm text-text-secondary">
          Nothing on the register resembles this name. It may be sponsored by a parent body —
          search for that below.
        </p>
      )}

      <div>
        <label
          htmlFor={`register-search-${institution.id}`}
          className="block text-body-sm font-medium"
        >
          Search the register directly
        </label>
        <Input
          id={`register-search-${institution.id}`}
          type="search"
          value={search}
          placeholder="e.g. UK Research and Innovation"
          onChange={(event) => setSearch(event.target.value)}
          className="mt-1"
        />
        {registerResults.data?.length ? (
          <ul className="mt-2">
            {registerResults.data.map((candidate) => (
              <li key={candidate.organisation_name}>
                <label className={candidateRow}>
                  <input
                    type="radio"
                    name={`candidate-${institution.id}`}
                    value={candidate.organisation_name}
                    checked={chosen === candidate.organisation_name}
                    onChange={() => {
                      setChosen(candidate.organisation_name);
                      setVerdict("CONFIRMED_VIA_PARENT");
                    }}
                    className="h-4 w-4 accent-[var(--color-brand)]"
                  />
                  {candidate.organisation_name}
                  {candidate.town_city ? (
                    <span className="text-text-secondary">· {candidate.town_city}</span>
                  ) : null}
                </label>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label htmlFor={`verdict-${institution.id}`} className="block text-body-sm font-medium">
            Verdict
          </label>
          <Select
            id={`verdict-${institution.id}`}
            value={verdict}
            onChange={(event) => setVerdict(event.target.value as SponsorVerdict)}
            className="mt-1 w-auto"
          >
            {VERDICT_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {SPONSOR_LABELS[option]}
              </option>
            ))}
          </Select>
        </div>

        <Button
          variant="primary"
          disabled={verdict !== "NOT_FOUND" && !chosen}
          onClick={() =>
            resolve.mutate(
              { id: institution.id, registered_legal_name: chosen, verdict },
              { onSuccess: () => onResolved(`Recorded a verdict for ${institution.name}.`) },
            )
          }
        >
          Save decision
        </Button>

        <Button
          variant="quiet"
          onClick={() =>
            resolve.mutate(
              { id: institution.id, registered_legal_name: "", verdict: "NOT_FOUND" },
              { onSuccess: () => onResolved(`${institution.name} marked as not on the register.`) },
            )
          }
        >
          Not on the register
        </Button>
      </div>
    </Card>
  );
}
