import { forwardRef } from "react";
import type { TextareaHTMLAttributes } from "react";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { error = false, className = "", rows = 6, ...rest },
  ref,
) {
  const classes = [
    "w-full resize-y rounded-sm border bg-surface px-3 py-2 text-body text-text-primary",
    "placeholder:text-text-muted",
    "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]",
    "disabled:cursor-not-allowed disabled:opacity-50",
    error ? "border-danger" : "border-border-strong",
    className,
  ].join(" ");

  return (
    <textarea ref={ref} rows={rows} className={classes} aria-invalid={error || undefined} {...rest} />
  );
});
