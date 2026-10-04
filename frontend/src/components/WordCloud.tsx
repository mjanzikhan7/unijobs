import { Link } from "react-router-dom";

import type { CloudTerm } from "@/viewmodels/useInsights";

const MIN_REM = 0.85;
const MAX_REM = 2.6;

interface Props {
  terms: CloudTerm[];
  maxOccurrences: number;
}

export function WordCloud({ terms, maxOccurrences }: Props) {
  if (terms.length === 0) {
    return (
      <p
        role="status"
        className="rounded-md border border-dashed border-border-subtle px-4 py-8 text-center text-body-sm text-text-muted"
      >
        Nothing searched yet in this window.
      </p>
    );
  }

  return (
    <ul className="flex flex-wrap items-baseline gap-x-3 gap-y-1" aria-label="Most searched terms">
      {terms.map((term) => (
        <li key={term.term}>
          <Link
            className="text-brand underline underline-offset-2 hover:decoration-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            style={{ fontSize: `${sizeFor(term.occurrences, maxOccurrences)}rem` }}
            to={`/?q=${encodeURIComponent(term.term)}`}
            title={`${term.term}: ${term.occurrences} searches by ${term.searchers} people`}
          >
            {term.term}
            <span className="sr-only">
              , {term.occurrences} searches by {term.searchers} people
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function sizeFor(occurrences: number, max: number): number {
  if (max <= 0) return MIN_REM;
  const share = Math.sqrt(occurrences) / Math.sqrt(max);
  return Number((MIN_REM + share * (MAX_REM - MIN_REM)).toFixed(2));
}
