export interface SegmentedControlOption<T extends string> {
  value: T;
  label: string;
  disabled?: boolean;
}

export interface SegmentedControlProps<T extends string> {
  label: string;
  options: SegmentedControlOption<T>[];
  value: T;
  onChange: (value: T) => void;
  name?: string;
}

export function SegmentedControl<T extends string>({
  label,
  options,
  value,
  onChange,
  name,
}: SegmentedControlProps<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={label}
      className="relative inline-flex rounded-md border border-border-subtle bg-surface-sunken p-0.5"
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <label
            key={option.value}
            className={[
              "cursor-pointer rounded-sm px-3 py-1.5 text-body-sm font-medium select-none",
              "transition-colors duration-[var(--duration-fast)] ease-[var(--ease-out)]",
              "focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-brand",
              selected
                ? "bg-brand text-text-inverse shadow-xs"
                : "text-text-secondary hover:text-text-primary",
              option.disabled && "cursor-not-allowed opacity-50 hover:text-text-secondary",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <input
              type="radio"
              name={name ?? label}
              className="sr-only"
              checked={selected}
              disabled={option.disabled}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        );
      })}
    </div>
  );
}
