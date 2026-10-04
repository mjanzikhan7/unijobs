import { Icon } from "@/components/Icon/Icon";
import type { Discipline, FacetValue } from "@/models/api/types";
import { ACADEMIC_DISCIPLINES, DISCIPLINE_LABELS, PROFESSIONAL_DISCIPLINES } from "@/utilities/format";

interface DisciplineBrowseProps {
  values: FacetValue[];
  selected: string[];
  onSelect: (discipline: Discipline) => void;
}

const SECTIONS: Array<{ heading: string; disciplines: readonly Discipline[] }> = [
  { heading: "Academic discipline / field of expertise", disciplines: ACADEMIC_DISCIPLINES },
  { heading: "Professional, managerial & support services", disciplines: PROFESSIONAL_DISCIPLINES },
];

export function DisciplineBrowse({ values, selected, onSelect }: DisciplineBrowseProps) {
  if (values.length === 0) return null;
  const counts = new Map(values.map((row) => [row.value, row.count]));

  return (
    <details
      aria-label="Browse by discipline"
      className="group rounded-md border border-border-subtle bg-surface shadow-xs"
      open={selected.length === 0 || undefined}
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-5 py-4 font-display text-heading-sm font-semibold [&::-webkit-details-marker]:hidden">
        <span>Browse by discipline</span>
        <Icon
          name="chevron-down"
          className="h-4 w-4 shrink-0 text-text-muted transition-transform duration-[var(--duration-fast)] group-open:rotate-180"
        />
      </summary>
      <div className="space-y-5 border-t border-border-subtle px-5 pt-4 pb-5">
        {SECTIONS.map(({ heading, disciplines }) => (
          <div key={heading}>
            <h3 className="border-b border-border-subtle pb-2 text-overline font-semibold tracking-wide text-text-muted uppercase">
              {heading}
            </h3>
            <ul className="mt-1 grid gap-x-6 sm:grid-cols-2">
              {disciplines.map((discipline) => {
                const count = counts.get(discipline) ?? 0;
                return (
                  <li key={discipline}>
                    <button
                      type="button"
                      disabled={count === 0}
                      onClick={() => onSelect(discipline)}
                      className={[
                        "flex min-h-11 w-full items-center justify-between gap-2 rounded-sm px-2 text-left text-body-sm",
                        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
                        count === 0
                          ? "cursor-not-allowed text-text-muted"
                          : "cursor-pointer text-brand hover:bg-surface-sunken",
                      ].join(" ")}
                    >
                      <span className="min-w-0 flex-1 truncate">
                        {DISCIPLINE_LABELS[discipline]}
                      </span>
                      <span
                        className="shrink-0 text-caption tabular-nums text-text-muted"
                        aria-label={`${count} results`}
                      >
                        {count}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </details>
  );
}
