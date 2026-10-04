import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { error = false, className = "", ...rest },
  ref,
) {
  const classes = [
    "h-11 w-full rounded-sm border bg-surface px-3 text-body text-text-primary",
    "placeholder:text-text-muted",
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
    "disabled:cursor-not-allowed disabled:opacity-50",
    error ? "border-danger" : "border-border-strong",
    className,
  ].join(" ");

  return <input ref={ref} className={classes} aria-invalid={error || undefined} {...rest} />;
});
