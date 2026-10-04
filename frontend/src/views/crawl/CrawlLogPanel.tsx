import { useEffect, useRef } from "react";

import { Badge } from "@/components/Badge/Badge";
import type { BadgeTone } from "@/components/Badge/Badge";
import { formatTime } from "@/utilities/format";
import { useRunLogs } from "@/viewmodels/useRunLogs";

const LEVEL_TONE: Record<string, BadgeTone> = {
  INFO: "neutral",
  WARNING: "caution",
  ERROR: "negative",
};

interface CrawlLogPanelProps {
  runId: number | null;
  maxVisible?: number;
}

const emptyLine = "rounded-md bg-surface-sunken px-3 py-4 text-body-sm text-text-muted";

export function CrawlLogPanel({ runId, maxVisible = 200 }: CrawlLogPanelProps) {
  const { entries, isLoading } = useRunLogs(runId);
  const listRef = useRef<HTMLOListElement>(null);

  const visible = entries.slice(-maxVisible);

  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const atBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 40;
    if (atBottom) list.scrollTop = list.scrollHeight;
  }, [entries.length]);

  if (runId === null) {
    return (
      <p className={emptyLine} role="status">
        No run selected.
      </p>
    );
  }

  if (isLoading && entries.length === 0) {
    return (
      <p className={emptyLine} role="status">
        Loading the log…
      </p>
    );
  }

  if (entries.length === 0) {
    return (
      <p className={emptyLine} role="status">
        Nothing logged yet.
      </p>
    );
  }

  return (
    <ol
      ref={listRef}
      aria-label={`Log for run ${runId}`}
      aria-live="polite"
      className="max-h-80 overflow-y-auto rounded-md border border-border-subtle bg-surface-sunken p-3 font-mono text-caption"
    >
      {visible.map((entry) => {
        const level = entry.level ?? "INFO";
        const tone = LEVEL_TONE[level] ?? "neutral";
        return (
          <li key={entry.id} className="flex flex-wrap items-baseline gap-2 py-0.5">
            <span className="shrink-0 tabular-nums text-text-muted">
              {formatTime(entry.created_at)}
            </span>
            <Badge tone={tone}>{level}</Badge>
            <span className="min-w-0 flex-1 text-text-secondary">
              {entry.institution_name ? (
                <strong className="text-text-primary">{entry.institution_name}: </strong>
              ) : null}
              {entry.message}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
