export interface TermChipGroupProps {
  field: string;
  label?: string;
  terms: string[];
  selected: string[];
  onToggle: (term: string) => void;
  emptyMessage?: string;
}

export function TermChipGroup({
  field,
  label,
  terms,
  selected,
  onToggle,
  emptyMessage = "Nothing found.",
}: TermChipGroupProps) {
  return (
    <fieldset>
      <legend className="text-overline font-semibold tracking-wide text-text-muted uppercase">
        {label ?? field}
      </legend>
      {terms.length === 0 ? (
        <p className="mt-1 text-body-sm text-text-muted">{emptyMessage}</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          {terms.map((term) => {
            const isSelected = selected.includes(term);
            return (
              <label
                key={term}
                className={[
                  "inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-full border px-3 text-body-sm",
                  "focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-[var(--color-focus-ring)]",
                  isSelected
                    ? "border-brand bg-brand-subtle text-brand"
                    : "border-border-strong bg-surface text-text-secondary",
                ].join(" ")}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onToggle(term)}
                  className="h-4 w-4 accent-[var(--color-brand)]"
                />
                {term}
              </label>
            );
          })}
        </div>
      )}
    </fieldset>
  );
}
