import type { ReactNode } from "react";

import type { SponsorVerdict, ThresholdVerdict } from "@/models/api/types";
import { SPONSOR_LABELS, THRESHOLD_LABELS } from "@/utilities/format";

export type BadgeTone = "positive" | "caution" | "negative" | "neutral" | "unknown";

export interface BadgeProps {
  tone: BadgeTone;
  children: ReactNode;
  title?: string;
}

const toneClasses: Record<BadgeTone, string> = {
  positive: "text-success bg-success-bg",
  caution: "text-warning bg-warning-bg",
  negative: "text-danger bg-danger-bg",
  neutral: "text-text-secondary bg-surface-sunken",
  unknown: "text-[var(--color-unknown-text)] bg-[var(--color-unknown-bg)]",
};

export function Badge({ tone, children, title }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-micro font-semibold ${toneClasses[tone]}`}
      title={title}
      data-tone={tone}
    >
      {children}
    </span>
  );
}

const SPONSOR_TONES: Record<SponsorVerdict, BadgeTone> = {
  CONFIRMED: "positive",
  CONFIRMED_VIA_PARENT: "positive",
  B_RATED: "caution",
  PROVISIONAL: "caution",
  OTHER_ROUTE_ONLY: "negative",
  NOT_FOUND: "negative",
};

const THRESHOLD_TONES: Record<ThresholdVerdict, BadgeTone> = {
  TARGET_BAND: "positive",
  LATERAL_CONTINGENT: "caution",
  PAY_CUT: "negative",
  EXCLUDED_BELOW_FLOOR: "negative",
  SALARY_UNCLEAR: "unknown",
};

export function SponsorBadge({
  verdict,
  matchedName,
  advertExcludes,
}: {
  verdict: SponsorVerdict | null | undefined;
  matchedName?: string | null;
  advertExcludes?: boolean;
}) {
  if (!verdict) return <MissingBadge kind="sponsor" />;

  if (advertExcludes) {
    return (
      <Badge tone="negative" title="This advert rules sponsorship out in terms.">
        ⚠ Advert excludes sponsorship
      </Badge>
    );
  }

  const tone = SPONSOR_TONES[verdict];
  const title = matchedName ? `Matched to "${matchedName}" on the register` : undefined;
  return (
    <Badge tone={tone} title={title}>
      {SPONSOR_LABELS[verdict]}
    </Badge>
  );
}

export function ThresholdBadge({
  verdict,
  explanation,
}: {
  verdict: ThresholdVerdict | null | undefined;
  explanation?: string | null;
}) {
  if (!verdict) return <MissingBadge kind="threshold" />;
  return (
    <Badge tone={THRESHOLD_TONES[verdict]} title={explanation ?? undefined}>
      {THRESHOLD_LABELS[verdict]}
    </Badge>
  );
}

export function MissingBadge({ kind }: { kind: "sponsor" | "threshold" }) {
  return (
    <Badge
      tone="unknown"
      title={`This job has no ${kind} verdict. It has not been screened — do not treat it as cleared.`}
    >
      ⚠ Not screened
    </Badge>
  );
}
