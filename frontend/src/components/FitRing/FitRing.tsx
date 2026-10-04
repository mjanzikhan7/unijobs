import type { CSSProperties } from "react";

import { matchBands } from "@/styles/tokens";

import styles from "./FitRing.module.css";

export type FitRingSize = "sm" | "md" | "lg";

export interface FitRingProps {
  score: number | null | undefined;
  size?: FitRingSize;
}

type Band = (typeof matchBands)[number]["band"];

type RingVars = CSSProperties & {
  "--sweep": number;
  "--fit-arc": string;
  "--fit-thickness": string;
};

const sizes: Record<FitRingSize, { box: string; thickness: string; text: string }> = {
  sm: { box: "h-10 w-10", thickness: "4px", text: "text-caption" },
  md: { box: "h-14 w-14", thickness: "5px", text: "text-body-sm" },
  lg: { box: "h-20 w-20", thickness: "7px", text: "text-heading-sm" },
};

const bandArc: Record<Band, string> = {
  low: "var(--color-match-low-text)",
  medium: "var(--color-match-medium-text)",
  high: "var(--color-match-high-text)",
};

const bandText: Record<Band, string> = {
  low: "text-[var(--color-match-low-text)]",
  medium: "text-[var(--color-match-medium-text)]",
  high: "text-[var(--color-match-high-text)]",
};

const bandLabel: Record<Band, string> = {
  low: "Low match",
  medium: "Medium match",
  high: "Strong match",
};

export function bandFor(score: number): Band {
  const matched = matchBands.find((entry) => score >= entry.min);
  return matched ? matched.band : "low";
}

export function FitRing({ score, size = "md" }: FitRingProps) {
  const { box, thickness, text } = sizes[size];

  const unscored = score === null || score === undefined;
  const clamped = unscored ? 0 : Math.max(0, Math.min(100, Math.round(score)));
  const band = bandFor(clamped);

  const label = unscored
    ? "Match not scored — no candidate profile yet"
    : `${bandLabel[band]}: ${clamped} out of 100`;

  const vars: RingVars = {
    "--sweep": unscored ? 0 : clamped,
    "--fit-arc": unscored ? "transparent" : bandArc[band],
    "--fit-thickness": thickness,
  };

  return (
    <span
      className={`relative inline-flex shrink-0 items-center justify-center rounded-full ${box} ${styles.ring}`}
      style={vars}
      data-band={unscored ? "none" : band}
      title={unscored ? "No profile yet — add one to see how well you match" : label}
    >
      <span
        className={`relative z-10 font-medium tabular-nums ${unscored ? "text-text-muted" : bandText[band]} ${text}`}
        aria-hidden="true"
      >
        {unscored ? "—" : clamped}
      </span>
      <span className="sr-only">{label}</span>
    </span>
  );
}
