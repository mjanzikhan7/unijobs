import { forwardRef } from "react";
import type { HTMLAttributes } from "react";

export type CardPadding = "sm" | "md" | "lg";

export type CardElement = "div" | "article" | "section" | "li";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padding?: CardPadding;
  interactive?: boolean;
  as?: CardElement;
}

const paddings: Record<CardPadding, string> = {
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { padding = "md", interactive = false, as = "div", className = "", ...rest },
  ref,
) {
  const Element = as as "div";
  const classes = [
    "rounded-md border border-border-subtle bg-surface shadow-xs",
    paddings[padding],
    interactive &&
      "transition-[box-shadow,transform] duration-[var(--duration-fast)] ease-[var(--ease-out)] " +
        "hover:-translate-y-0.5 hover:shadow-md focus-within:-translate-y-0.5 focus-within:shadow-md " +
        "motion-reduce:hover:translate-y-0 motion-reduce:focus-within:translate-y-0",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return <Element ref={ref} className={classes} {...rest} />;
});
