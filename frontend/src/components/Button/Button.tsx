import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "quiet" | "cta" | "danger";
export type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const base =
  "inline-flex items-center justify-center gap-2 rounded-md border font-semibold " +
  "transition-colors duration-[var(--duration-fast)] ease-[var(--ease-out)] " +
  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 " +
  "focus-visible:outline-[var(--color-focus-ring)] " +
  "disabled:cursor-not-allowed disabled:opacity-50";

const sizes: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-body-sm",
  md: "h-11 px-4 text-body",
};

const variants: Record<ButtonVariant, string> = {
  secondary: "bg-surface text-text-primary border-border-strong hover:border-brand",
  primary: "bg-brand text-text-inverse border-brand hover:bg-brand-hover hover:border-brand-hover",
  quiet: "bg-transparent text-brand border-transparent hover:bg-brand-subtle",
  cta: "bg-cta text-text-inverse border-cta hover:bg-[var(--color-cta-hover)] hover:border-[var(--color-cta-hover)]",
  danger: "bg-danger text-text-inverse border-danger hover:opacity-90",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", className = "", type = "button", ...rest },
  ref,
) {
  const classes = [base, sizes[size], variants[variant], className].filter(Boolean).join(" ");
  return <button ref={ref} type={type} className={classes} {...rest} />;
});
