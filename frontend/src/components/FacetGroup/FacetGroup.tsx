import type { FacetValue } from "@/models/api/types";
import { Icon } from "@/components/Icon/Icon";
import { humanise } from "@/utilities/format";

interface FacetGroupProps {
  name: string;
  label: string;
  values: FacetValue[];
  selected: string[];
  onToggle: (value: string) => void;
  formatValue?: (value: string) => string;
}

export function FacetGroup({
  name,
  label,
  values,
  selected,
  onToggle,
  formatValue = humanise,
}: FacetGroupProps) {
  if (values.length === 0) return null;

  return (
    <details className="group border-t border-border-subtle pt-3" open={selected.length > 0 || undefined}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 pb-1 text-overline font-semibold tracking-wide text-text-muted uppercase [&::-webkit-details-marker]:hidden">
        <span>
          {label}
          {selected.length > 0 ? ` (${selected.length})` : ""}
        </span>
        <Icon name="chevron-down" className="h-3.5 w-3.5 transition-transform duration-[var(--duration-fast)] group-open:rotate-180" />
      </summary>
      <fieldset>
        <legend className="sr-only">{label}</legend>
        <ul>
        {values.map(({ value, count }) => {
          const isSelected = selected.includes(value);
          const disabled = count === 0 && !isSelected;
          const inputId = `facet-${name}-${value}`;
          return (
            <li key={value}>
              <label
                htmlFor={inputId}
                className={[
                  "flex min-h-11 items-center gap-2 rounded-sm px-2 text-body-sm",
                  "focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[var(--color-focus-ring)]",
                  disabled
                    ? "cursor-not-allowed text-text-muted"
                    : "cursor-pointer text-text-primary hover:bg-surface-sunken",
                ].join(" ")}
              >
                <input
                  id={inputId}
                  type="checkbox"
                  checked={isSelected}
                  disabled={disabled}
                  onChange={() => onToggle(value)}
                  className="h-4 w-4 shrink-0 accent-[var(--color-brand)]"
                />
                <span className="min-w-0 flex-1 truncate">{formatValue(value)}</span>
                <span
                  className="shrink-0 text-caption tabular-nums text-text-muted"
                  aria-label={`${count} results`}
                >
                  {count}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
      </fieldset>
    </details>
  );
}
