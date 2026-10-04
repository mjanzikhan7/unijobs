import { Skeleton } from "@/components/Skeleton/Skeleton";

export type StatCardTone = "default" | "warn";

export interface StatCardProps {
  label: string;
  value: number | string;
  hint?: string;
  tone?: StatCardTone;
  loading?: boolean;
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  loading = false,
}: StatCardProps) {
  const warn = tone === "warn";
  const border = warn ? "border-warning" : "border-border-subtle";

  return (
    <div className={`rounded-md border bg-surface p-5 shadow-xs ${border}`} data-tone={tone}>
      {loading ? (
        <Skeleton className="h-9 w-24" />
      ) : (
        <span
          className={`block font-display text-display-lg tabular-nums ${warn ? "text-warning" : "text-text-primary"}`}
        >
          {value}
        </span>
      )}
      <span className="mt-1 block text-body-sm text-text-secondary">{label}</span>
      {hint ? <span className="mt-1 block text-caption text-text-muted">{hint}</span> : null}
    </div>
  );
}
