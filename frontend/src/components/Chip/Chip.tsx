import type { ReactNode } from "react";

import type { BadgeTone } from "@/components/Badge/Badge";

export type ChipVariant = "solid" | "outline";

export interface ChipProps {
  tone?: BadgeTone;
  variant?: ChipVariant;
  children: ReactNode;
}

const solidTones: Record<BadgeTone, string> = {
  positive: "bg-success text-text-inverse",
  caution: "bg-warning text-text-inverse",
  negative: "bg-danger text-text-inverse",
  neutral: "bg-text-secondary text-text-inverse",
  unknown: "bg-[var(--color-unknown-text)] text-text-inverse",
};

const outlineTones: Record<BadgeTone, string> = {
  positive: "border-success text-success",
  caution: "border-warning text-warning",
  negative: "border-danger text-danger",
  neutral: "border-border-strong text-text-secondary",
  unknown: "border-[var(--color-unknown-text)] text-[var(--color-unknown-text)]",
};

export function Chip({ tone = "neutral", variant = "outline", children }: ChipProps) {
  const toneClasses = variant === "solid" ? solidTones[tone] : outlineTones[tone];
  const shape = variant === "solid" ? "border border-transparent" : "border bg-transparent";
  return (
    <span
      className={`inline-flex items-center rounded-sm px-2 py-0.5 text-caption font-medium ${shape} ${toneClasses}`}
      data-variant={variant}
    >
      {children}
    </span>
  );
}
