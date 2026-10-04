import { closingLabel, daysUntil, formatDate } from "@/utilities/format";

export type ClosesUrgency = "none" | "later" | "urgent" | "today" | "closed";

export function urgencyOf(value: string | null | undefined, today = new Date()): ClosesUrgency {
  const days = daysUntil(value, today);
  if (days === null) return "none";
  if (days < 0) return "closed";
  if (days === 0) return "today";
  return days <= 3 ? "urgent" : "later";
}

const styles: Record<ClosesUrgency, string> = {
  none: "bg-surface-sunken text-text-muted px-2.5 py-1 text-micro font-semibold",
  later: "bg-surface-sunken text-text-secondary px-2.5 py-1 text-micro font-semibold",
  urgent: "bg-danger-bg text-danger px-2.5 py-1 text-micro font-semibold",
  today: "bg-danger-bg text-danger px-3 py-1.5 text-body-sm font-extrabold",
  closed: "bg-surface-sunken text-text-muted px-2.5 py-1 text-micro font-semibold line-through",
};

export function ClosesBadge({ value }: { value: string | null | undefined }) {
  const urgency = urgencyOf(value);

  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full whitespace-nowrap ${styles[urgency]}`}
      data-urgency={urgency}
      title={value ? formatDate(value) : undefined}
    >
      {closingLabel(value)}
    </span>
  );
}
