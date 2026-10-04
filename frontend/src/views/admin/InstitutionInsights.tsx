import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { Input } from "@/components/Field/Input";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import { SegmentedControl } from "@/components/SegmentedControl/SegmentedControl";
import { Sparkbars } from "@/components/Sparkbars";
import { StatCard } from "@/components/StatCard/StatCard";
import { useInstitutionInsights } from "@/viewmodels/useInsights";

const WINDOWS = [7, 30, 90, 365] as const;

interface TrendRow {
  slug: string;
  name: string;
  posted: number;
  open_now: number;
  closed: number;
  withdrawn: number;
  views: number;
  saves: number;
  applications: number;
}

export function InstitutionInsights() {
  const [days, setDays] = useState<number>(90);
  const [term, setTerm] = useState("");
  const insights = useInstitutionInsights(days);

  if (insights.isLoading) return <Spinner label="Loading insights" />;
  if (insights.isError) {
    return <ErrorMessage error={insights.error} onRetry={() => void insights.refetch()} />;
  }

  const data = insights.data;
  if (!data) return null;

  const engagementBySlug = new Map(data.engagement.map((row) => [row.slug, row]));

  const needle = term.trim().toLowerCase();
  const filtered = needle
    ? data.institutions.filter((row) => row.name.toLowerCase().includes(needle))
    : data.institutions;
  const rows: TrendRow[] = filtered.map((row) => {
    const interest = engagementBySlug.get(row.slug);
    return {
      slug: row.slug,
      name: row.name,
      posted: row.posted,
      open_now: row.open_now,
      closed: row.closed,
      withdrawn: row.withdrawn,
      views: interest?.views ?? 0,
      saves: interest?.saves ?? 0,
      applications: interest?.applications ?? 0,
    };
  });
  const truncated = data.institutions.length >= data.limit;

  const columns: DataTableColumn<TrendRow>[] = [
    {
      key: "name",
      header: "Institution",
      isRowHeader: true,
      cell: (row) => (
        <Link to={`/institutions/${row.slug}`} className="text-brand underline underline-offset-2 hover:decoration-2">
          {row.name}
        </Link>
      ),
    },
    { key: "posted", header: "Posted", numeric: true, cell: (row) => row.posted },
    { key: "open", header: "Open", numeric: true, cell: (row) => row.open_now },
    { key: "closed", header: "Closed", numeric: true, cell: (row) => row.closed },
    { key: "withdrawn", header: "Withdrawn", numeric: true, cell: (row) => row.withdrawn },
    { key: "views", header: "Views", numeric: true, cell: (row) => row.views },
    { key: "saves", header: "Saves", numeric: true, cell: (row) => row.saves },
    {
      key: "applications",
      header: "Applications",
      numeric: true,
      cell: (row) => row.applications,
    },
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-heading-xl font-bold">Institution trends</h1>
        <SegmentedControl
          label="Time window"
          value={String(days)}
          onChange={(value) => setDays(Number(value))}
          options={WINDOWS.map((option) => ({ value: String(option), label: `${option}d` }))}
        />
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label="Vacancies first seen" value={data.totals.posted} />
        <StatCard label="Open right now" value={data.totals.open_now} />
        <StatCard label="Institutions posting" value={data.totals.institutions_posting} />
      </section>

      <section>
        <h2 className="font-display text-heading-md font-semibold">Vacancies first seen per day</h2>
        <div className="mt-3">
          <Sparkbars
            data={data.by_day.map((row) => ({ label: row.day, value: row.posted }))}
            emptyMessage="Nothing new in this window — which may mean nothing was posted, or that no crawl ran."
          />
        </div>
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="font-display text-heading-md font-semibold">
            Posting and interest, side by side
          </h2>
          <p className="mt-1 text-body-sm text-text-secondary">
            Posting comes from the vacancies themselves; interest comes from what candidates did. A
            row with vacancies and no interest is worth a look — so is the reverse.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="trend-filter" className="block text-body-sm font-medium">
              Filter
            </label>
            <Input
              id="trend-filter"
              type="search"
              placeholder="Institution name"
              value={term}
              onChange={(event) => setTerm(event.target.value)}
              className="mt-1"
            />
          </div>
          <span className="pb-3 text-body-sm tabular-nums text-text-secondary">
            {needle
              ? `${rows.length} of ${data.institutions.length} institutions`
              : `${data.institutions.length} institutions posted in this window`}
          </span>
        </div>

        {truncated ? (
          <Notice tone="warning">
            Showing the first {data.limit} institutions by volume. Narrow the window or filter by
            name to see the rest.
          </Notice>
        ) : null}

        <DataTable<TrendRow>
          caption="Posting and interest per institution"
          columns={columns}
          rows={rows}
          rowKey={(row) => row.slug}
          belowMd="scroll"
          emptyTitle="Nothing matches that filter"
          emptyBody="Clear the filter, or widen the time window."
        />
      </section>
    </div>
  );
}
