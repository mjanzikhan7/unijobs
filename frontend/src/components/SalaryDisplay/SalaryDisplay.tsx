import { salaryRange, truncate } from "@/utilities/format";
import type { Screening } from "@/models/api/types";

export type SalaryDisplaySize = "sm" | "md";

export interface SalaryDisplayProps {
  screening: Screening | null | undefined;
  raw: string | null | undefined;
  size?: SalaryDisplaySize;
}

const sizes: Record<SalaryDisplaySize, { parsed: string; raw: string }> = {
  sm: { parsed: "text-body-sm font-medium", raw: "text-caption" },
  md: { parsed: "text-body-lg font-medium", raw: "text-body-sm" },
};

const RAW_LIMIT = 60;

export function isPureRepunctuation(parsed: string, raw: string): boolean {
  if (/[a-zA-Z]/.test(raw)) return false;
  const digitGroups = (value: string) => value.match(/\d+/g) ?? [];
  const parsedGroups = digitGroups(parsed);
  const rawGroups = digitGroups(raw);
  if (parsedGroups.length === 0 || parsedGroups.length !== rawGroups.length) return false;
  return parsedGroups.every((group, index) => group === rawGroups[index]);
}

export function SalaryDisplay({ screening, raw, size = "md" }: SalaryDisplayProps) {
  const parsed = salaryRange(screening);
  const trimmedRaw = raw?.trim() ?? "";
  const unparsed = parsed === "—";
  const { parsed: parsedClass, raw: rawClass } = sizes[size];
  const showRaw = trimmedRaw !== "" && !(!unparsed && isPureRepunctuation(parsed, trimmedRaw));

  return (
    <p className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
      <span
        className={`tabular-nums ${unparsed ? "text-text-muted" : "text-text-primary"} ${parsedClass}`}
      >
        {unparsed ? (trimmedRaw ? "Not parsed" : "Salary not stated") : parsed}
      </span>
      {showRaw ? (
        <span className={`text-text-secondary ${rawClass}`} title={trimmedRaw}>
          {truncate(trimmedRaw, RAW_LIMIT)}
        </span>
      ) : null}
    </p>
  );
}
