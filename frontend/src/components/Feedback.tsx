import { useEffect } from "react";

import { Button } from "@/components/Button/Button";
import { ApiError } from "@/models/api/client";

interface SpinnerProps {
  label?: string;
  inline?: boolean;
}

export function Spinner({ label = "Loading", inline = false }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={
        inline
          ? "inline-flex items-center gap-2 text-caption text-text-muted"
          : "flex items-center justify-center gap-2 py-8 text-body-sm text-text-secondary"
      }
    >
      <span
        aria-hidden="true"
        className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none"
      />
      <span className={inline ? undefined : "sr-only"}>{label}</span>
    </div>
  );
}

export function ErrorMessage({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = describe(error);
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 rounded-md border border-danger bg-danger-bg px-4 py-3 text-body-sm text-danger"
    >
      <p className="min-w-0 flex-1">{message}</p>
      {onRetry ? (
        <Button size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function describe(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session has expired. Sign in again.";
    if (error.status === 403) return "You do not have access to that.";
    if (error.status === 404) return "That no longer exists.";
    if (error.status >= 500) return "The server had a problem. It has not lost anything.";
    return error.readableMessage;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

interface ToastProps {
  message: string | null;
  tone?: "info" | "error";
  onDismiss: () => void;
  timeoutMs?: number;
}

export function Toast({ message, tone = "info", onDismiss, timeoutMs = 5000 }: ToastProps) {
  useEffect(() => {
    if (!message || tone === "error") return;
    const timer = window.setTimeout(onDismiss, timeoutMs);
    return () => window.clearTimeout(timer);
  }, [message, tone, timeoutMs, onDismiss]);

  if (!message) return null;

  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`fixed bottom-4 left-1/2 z-40 flex max-w-[calc(100vw-2rem)] -translate-x-1/2 items-center gap-3 rounded-md border px-4 py-3 text-body-sm shadow-lg ${
        tone === "error"
          ? "border-danger bg-danger-bg text-danger"
          : "border-border-subtle bg-surface text-text-primary"
      }`}
    >
      <span>{message}</span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss"
        className="-my-1 shrink-0 rounded-xs px-2 py-1 text-body-lg leading-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  );
}
