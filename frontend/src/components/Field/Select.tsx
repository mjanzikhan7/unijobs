import { forwardRef } from "react";
import type { SelectHTMLAttributes } from "react";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className = "", children, ...rest },
  ref,
) {
  const classes = [
    "h-11 w-full rounded-sm border border-border-strong bg-surface px-3 text-body text-text-primary",
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
    "disabled:cursor-not-allowed disabled:opacity-50",
    className,
  ].join(" ");

  return (
    <select ref={ref} className={classes} {...rest}>
      {children}
    </select>
  );
});
