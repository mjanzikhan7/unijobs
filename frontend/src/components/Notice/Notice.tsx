import type { ReactNode } from "react";

export type NoticeTone = "info" | "warning" | "danger";

export interface NoticeProps {
  tone: NoticeTone;
  children: ReactNode;
  quote?: ReactNode;
}

const toneClasses: Record<NoticeTone, string> = {
  info: "border-[var(--color-info-text)]/30 bg-info-bg text-[var(--color-info-text)]",
  warning: "border-warning/30 bg-warning-bg text-warning",
  danger: "border-danger/30 bg-danger-bg text-danger",
};

const icon: Record<NoticeTone, string> = {
  info: "ⓘ",
  warning: "⚠",
  danger: "⚠",
};

export function Notice({ tone, children, quote }: NoticeProps) {
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={`flex gap-3 rounded-md border px-4 py-3 text-body-sm ${toneClasses[tone]}`}
    >
      <span aria-hidden="true" className="shrink-0">
        {icon[tone]}
      </span>
      <div className="space-y-2">
        <p>{children}</p>
        {quote ? (
          <blockquote className="border-l-2 border-current/40 pl-3 italic opacity-90">
            {quote}
          </blockquote>
        ) : null}
      </div>
    </div>
  );
}
