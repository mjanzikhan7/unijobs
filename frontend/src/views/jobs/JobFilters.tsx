import { Button } from "@/components/Button/Button";
import { FacetGroup } from "@/components/FacetGroup/FacetGroup";
import { Input } from "@/components/Field/Input";
import { Icon } from "@/components/Icon/Icon";
import type { Discipline, FacetResponse, Institution } from "@/models/api/types";
import { MULTI_VALUE_KEYS, SINGLE_VALUE_KEYS } from "@/utilities/filters";
import type { JobFilters as Filters, MultiValueKey, SingleValueKey } from "@/utilities/filters";
import { DISCIPLINE_LABELS, filterLabel, humanise } from "@/utilities/format";

const FACET_LABELS: Array<{ key: MultiValueKey; label: string }> = [
  { key: "sponsor_verdict", label: "Sponsorship" },
  { key: "threshold_verdict", label: "Salary band" },
  { key: "discipline", label: "Discipline" },
  { key: "nation", label: "Nation" },
  { key: "category", label: "Category" },
  { key: "contract_type", label: "Contract" },
  { key: "hours", label: "Hours" },
  { key: "workplace", label: "Workplace" },
  { key: "status", label: "Status" },
  { key: "institution", label: "Institution" },
];

interface JobFiltersProps {
  filters: Filters;
  facets: FacetResponse | undefined;
  institutions: Institution[];
  onToggle: (key: MultiValueKey, value: string) => void;
  onSet: (key: SingleValueKey, value: string | null) => void;
  onClearAll: () => void;
}

const fieldLabel = "block text-body-sm font-medium text-text-primary";
const hint = "mt-1 text-caption text-text-muted";

interface ActiveChip {
  id: string;
  label: string;
  onRemove: () => void;
}

function activeChips(
  filters: Filters,
  institutionNames: Map<string, string>,
  onToggle: (key: MultiValueKey, value: string) => void,
  onSet: (key: SingleValueKey, value: string | null) => void,
): ActiveChip[] {
  const chips: ActiveChip[] = [];
  for (const key of MULTI_VALUE_KEYS) {
    for (const value of filters.multi[key] ?? []) {
      const label =
        key === "institution"
          ? (institutionNames.get(value) ?? value)
          : key === "discipline"
            ? (DISCIPLINE_LABELS[value as Discipline] ?? value)
            : humanise(value);
      chips.push({ id: `${key}:${value}`, label, onRemove: () => onToggle(key, value) });
    }
  }
  for (const key of SINGLE_VALUE_KEYS) {
    if (key === "order" || key === "page" || key === "q") continue;
    const value = filters.single[key];
    if (!value) continue;
    const label = key === "sponsorable" ? "Sponsorship possible" : `${filterLabel(key)}: ${value}`;
    chips.push({ id: key, label, onRemove: () => onSet(key, null) });
  }
  return chips;
}

export function JobFiltersPanel({
  filters,
  facets,
  institutions,
  onToggle,
  onSet,
  onClearAll,
}: JobFiltersProps) {
  const institutionNames = new Map(institutions.map((row) => [row.slug, row.name]));
  const chips = activeChips(filters, institutionNames, onToggle, onSet);

  return (
    <div aria-label="Filters" className="flex flex-col gap-4">
      {chips.length > 0 ? (
        <div className="flex flex-wrap gap-1.5" aria-label="Active filters">
          {chips.map((chip) => (
            <button
              key={chip.id}
              type="button"
              onClick={chip.onRemove}
              className="inline-flex items-center gap-1 rounded-sm border border-brand bg-brand-subtle px-2 py-1 text-caption font-medium text-brand hover:bg-brand hover:text-text-inverse focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
            >
              {chip.label}
              <Icon name="close" className="h-3 w-3" />
              <span className="sr-only">, remove filter</span>
            </button>
          ))}
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-2">
        <h2 className="font-display text-heading-sm font-semibold">Filters</h2>
        <Button variant="quiet" size="sm" onClick={onClearAll}>
          Clear all
        </Button>
      </div>

      <div className="rounded-sm bg-brand-subtle p-3">
        <label
          htmlFor="filter-sponsorable"
          className="flex min-h-11 cursor-pointer items-center gap-2 text-body-sm font-medium"
        >
          <input
            id="filter-sponsorable"
            type="checkbox"
            checked={filters.single.sponsorable === "true"}
            onChange={(event) => onSet("sponsorable", event.target.checked ? "true" : null)}
            className="h-4 w-4 shrink-0 accent-[var(--color-brand)]"
          />
          Only where sponsorship is possible
        </label>
        <p className={hint}>
          Honours an advert that rules sponsorship out, even at a confirmed sponsor.
        </p>
      </div>

      <div>
        <label htmlFor="filter-salary-min" className={fieldLabel}>
          Salary floor at least
        </label>
        <Input
          id="filter-salary-min"
          type="number"
          inputMode="numeric"
          step={1000}
          value={filters.single.salary_min ?? ""}
          placeholder="e.g. 45000"
          onChange={(event) => onSet("salary_min", event.target.value || null)}
          className="mt-1"
        />
        <p className={hint}>Compared against the bottom of the advertised range.</p>
      </div>

      <div>
        <label htmlFor="filter-fitness" className={fieldLabel}>
          Minimum fitness
        </label>
        <div className="mt-1 flex items-center gap-3">
          <input
            id="filter-fitness"
            type="range"
            min={0}
            max={100}
            step={5}
            value={filters.single.min_fitness ?? "0"}
            onChange={(event) =>
              onSet("min_fitness", event.target.value === "0" ? null : event.target.value)
            }
            className="min-w-0 flex-1 accent-[var(--color-brand)]"
          />
          <output
            htmlFor="filter-fitness"
            className="w-8 shrink-0 text-right text-body-sm tabular-nums text-text-secondary"
          >
            {filters.single.min_fitness ?? "0"}
          </output>
        </div>
      </div>

      <div>
        <label htmlFor="filter-closing-before" className={fieldLabel}>
          Closing before
        </label>
        <Input
          id="filter-closing-before"
          type="date"
          value={filters.single.closing_before ?? ""}
          onChange={(event) => onSet("closing_before", event.target.value || null)}
          className="mt-1"
        />
      </div>

      {FACET_LABELS.map(({ key, label }) => (
        <FacetGroup
          key={key}
          name={key}
          label={label}
          values={facets?.facets[key] ?? []}
          selected={filters.multi[key] ?? []}
          onToggle={(value) => onToggle(key, value)}
          formatValue={
            key === "institution"
              ? (slug) => institutionNames.get(slug) ?? slug
              : key === "discipline"
                ? (value) => DISCIPLINE_LABELS[value as Discipline] ?? value
                : undefined
          }
        />
      ))}
    </div>
  );
}
