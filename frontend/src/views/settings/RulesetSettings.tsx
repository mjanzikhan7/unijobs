import { useMemo, useState } from "react";

import { Button } from "@/components/Button/Button";
import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { Input } from "@/components/Field/Input";
import { ErrorMessage, Spinner, Toast } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import type { RulesetFigure } from "@/models/api/types";
import { formatDate, humanise, money } from "@/utilities/format";
import { useCreateRuleset, useRescreen, useRulesets } from "@/viewmodels/useRulesets";

const fieldLabel = "block text-body-sm font-medium text-text-primary";

export function RulesetSettings() {
  const rulesets = useRulesets();
  const createRuleset = useCreateRuleset();
  const rescreen = useRescreen();
  const [toast, setToast] = useState<{ message: string; tone: "info" | "error" } | null>(null);
  const [draft, setDraft] = useState<Record<string, string> | null>(null);
  const [verifiedAt, setVerifiedAt] = useState(() => new Date().toISOString().slice(0, 10));
  const [sourceUrl, setSourceUrl] = useState("");

  const active = useMemo(
    () => (rulesets.data?.results ?? []).find((row) => row.is_active) ?? null,
    [rulesets.data],
  );

  if (rulesets.isLoading) return <Spinner label="Loading rulesets" />;
  if (rulesets.isError) {
    return <ErrorMessage error={rulesets.error} onRetry={() => void rulesets.refetch()} />;
  }
  if (!active) {
    return (
      <EmptyPanel
        title="No ruleset has been loaded"
        body={
          <>
            Screening cannot run without one. Load the figures with{" "}
            <code className="rounded-xs bg-surface-sunken px-1 font-mono">make seed</code>.
          </>
        }
      />
    );
  }

  const figures = active.figures ?? [];
  const values = draft ?? Object.fromEntries(figures.map((f) => [f.key, String(f.value)]));

  const onCreate = () => {
    if (!sourceUrl) {
      setToast({ message: "A source URL is required — a figure needs provenance.", tone: "error" });
      return;
    }
    createRuleset.mutate(
      {
        name: `Figures verified ${verifiedAt}`,
        effective_from: verifiedAt,
        verified_at: verifiedAt,
        source_url: sourceUrl,
        activate: true,
        figures: values,
      },
      {
        onSuccess: (created) => {
          setDraft(null);
          setToast({ message: `Created ruleset v${created.version}.`, tone: "info" });
        },
        onError: () => setToast({ message: "Could not create that ruleset.", tone: "error" }),
      },
    );
  };

  const columns: DataTableColumn<RulesetFigure>[] = [
    {
      key: "figure",
      header: "Figure",
      isRowHeader: true,
      cell: (figure) => humanise(figure.key.replace(/_/g, " ")),
    },
    { key: "in-force", header: "In force", numeric: true, cell: (figure) => money(figure.value) },
    {
      key: "new-value",
      header: "New value",
      numeric: true,
      cell: (figure) => (
        <>
          <label className="sr-only" htmlFor={`figure-${figure.key}`}>
            New value for {figure.key}
          </label>
          <Input
            id={`figure-${figure.key}`}
            type="number"
            step={100}
            value={values[figure.key] ?? ""}
            onChange={(event) => setDraft({ ...values, [figure.key]: event.target.value })}
            className="h-9 w-32 text-right tabular-nums"
          />
        </>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-narrow space-y-4">
      <h1 className="font-display text-heading-xl font-bold">Threshold figures</h1>

      <p className="text-body-sm text-text-secondary">
        In force: <strong className="text-text-primary">v{active.version}</strong> — {active.name}.
        Verified {formatDate(active.verified_at)} against{" "}
        <a
          href={active.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand underline underline-offset-2 hover:decoration-2"
        >
          the source ↗
        </a>
        .
      </p>

      <Notice tone="info">
        Editing here creates a new version. The one in force is never changed, so every stored
        verdict stays explainable by the rules that produced it.
      </Notice>

      <DataTable<RulesetFigure>
        caption="Threshold figures in the active ruleset"
        columns={columns}
        rows={figures}
        rowKey={(figure) => figure.key}
        emptyTitle="This ruleset has no figures"
        emptyBody="Nothing can be screened against it. Re-seed, or create a version with figures."
      />

      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="ruleset-verified" className={fieldLabel}>
            Verified on
          </label>
          <Input
            id="ruleset-verified"
            type="date"
            value={verifiedAt}
            onChange={(event) => setVerifiedAt(event.target.value)}
            className="mt-1"
          />
        </div>

        <div className="min-w-64 flex-1">
          <label htmlFor="ruleset-source" className={fieldLabel}>
            Source URL
          </label>
          <Input
            id="ruleset-source"
            type="url"
            value={sourceUrl}
            placeholder="https://www.gov.uk/…"
            onChange={(event) => setSourceUrl(event.target.value)}
            className="mt-1"
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="primary"
          onClick={onCreate}
          disabled={createRuleset.isPending || draft === null}
        >
          Create new version
        </Button>
        <Button
          disabled={rescreen.isPending}
          onClick={() =>
            rescreen.mutate(active.id, {
              onSuccess: (result) =>
                setToast({
                  message: `Re-screened ${result.screened} jobs; ${result.changed} verdicts changed.`,
                  tone: "info",
                }),
            })
          }
        >
          {rescreen.isPending ? "Re-screening…" : "Re-screen everything"}
        </Button>
        <p className="text-caption text-text-muted">
          Re-screening makes no network calls — nothing is re-crawled.
        </p>
      </div>

      <section>
        <h2 className="font-display text-heading-md font-semibold">Previous versions</h2>
        <ul className="mt-2 space-y-1 text-body-sm text-text-secondary">
          {(rulesets.data?.results ?? []).map((row) => (
            <li key={row.id}>
              v{row.version} — {row.name} · verified {formatDate(row.verified_at)}
              {row.is_active ? (
                <strong className="text-text-primary"> · in force</strong>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <Toast message={toast?.message ?? null} tone={toast?.tone} onDismiss={() => setToast(null)} />
    </div>
  );
}
