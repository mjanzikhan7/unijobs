import type { ReactNode } from "react";

export interface EmptyPanelProps {
  icon?: ReactNode;
  title: string;
  body: ReactNode;
  action?: ReactNode;
}

export function EmptyPanel({ icon, title, body, action }: EmptyPanelProps) {
  return (
    <div
      role="status"
      className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border-subtle bg-surface-sunken px-6 py-10 text-center"
    >
      {icon ? (
        <span aria-hidden="true" className="text-text-muted">
          {icon}
        </span>
      ) : null}
      <h2 className="font-display text-heading-sm text-text-primary">{title}</h2>
      <p className="max-w-prose text-body-sm text-text-secondary">{body}</p>
      {action ? <div className="mt-1 flex flex-wrap justify-center gap-2">{action}</div> : null}
    </div>
  );
}
