import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { ErrorMessage, Spinner } from "@/components/Feedback";
import { SegmentedControl } from "@/components/SegmentedControl/SegmentedControl";
import { Sparkbars } from "@/components/Sparkbars";
import { StatCard } from "@/components/StatCard/StatCard";
import { WordCloud } from "@/components/WordCloud";
import { useCandidateInsights, useSearchCloud } from "@/viewmodels/useInsights";

const WINDOWS = [7, 30, 90, 365] as const;

const EMPTY_SEARCH_WARN = 0.3;

interface SearchRow {
  query: string;
  searches: number;
  searchers: number;
  found_nothing: number;
}

interface DimensionRow {
  value: string;
  views: number;
  saves: number;
  applications: number;
}

interface InstitutionRow {
  slug: string;
  name: string;
  views: number;
  saves: number;
  applications: number;
}

const panelHeading = "font-display text-heading-md font-semibold";
const hint = "mt-1 text-body-sm text-text-secondary";

export function CandidateInsights() {
  const [days, setDays] = useState<number>(30);
  const insights = useCandidateInsights(days);
  const cloud = useSearchCloud(days);

  if (insights.isLoading) return <Spinner label="Loading insights" />;
  if (insights.isError) {
    return <ErrorMessage error={insights.error} onRetry={() => void insights.refetch()} />;
  }

  const data = insights.data;
  if (!data) return null;
  const { overview } = data;

  const searchColumns: DataTableColumn<SearchRow>[] = [
    {
      key: "query",
      header: "Search",
      isRowHeader: true,
      cell: (row) => (
        <Link to={`/?q=${encodeURIComponent(row.query)}`} className="text-brand underline underline-offset-2 hover:decoration-2">
          {row.query}
        </Link>
      ),
    },
    { key: "searches", header: "Times", numeric: true, cell: (row) => row.searches },
    { key: "searchers", header: "People", numeric: true, cell: (row) => row.searchers },
    {
      key: "found-nothing",
      header: "Found nothing",
      numeric: true,
      cell: (row) => row.found_nothing,
    },
  ];

  const institutionColumns: DataTableColumn<InstitutionRow>[] = [
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
        <h1 className="font-display text-heading-xl font-bold">Candidate activity</h1>
        <SegmentedControl
          label="Time window"
          value={String(days)}
          onChange={(value) => setDays(Number(value))}
          options={WINDOWS.map((option) => ({ value: String(option), label: `${option}d` }))}
        />
      </header>

      <p className="text-body-sm text-text-secondary">
        Aggregates only. This screen answers what candidates are doing, never what any one
        candidate did.
      </p>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Active candidates" value={overview.active_candidates} />
        <StatCard label="Searches" value={overview.searches} />
        <StatCard
          label="Found nothing"
          value={`${Math.round(overview.empty_search_rate * 100)}%`}
          hint="Searches returning no results. A high share is a gap in the estate, not in the search."
          tone={overview.empty_search_rate > EMPTY_SEARCH_WARN ? "warn" : "default"}
        />
        <StatCard label="Job views" value={overview.job_views} />
        <StatCard label="Saves" value={overview.saves} />
        <StatCard label="Applications" value={overview.applications} />
        <StatCard
          label="View → save"
          value={`${Math.round(overview.view_to_save_rate * 100)}%`}
          hint="How often looking at a job leads to keeping it."
        />
        <StatCard
          label="Save → apply"
          value={`${Math.round(overview.save_to_apply_rate * 100)}%`}
          hint="How often a saved job becomes an application."
        />
      </section>

      <section>
        <h2 className={panelHeading}>What people search for</h2>
        {cloud.isLoading ? <Spinner label="Loading search terms" /> : null}
        {cloud.data ? (
          <div className="mt-3">
            <WordCloud terms={cloud.data.terms} maxOccurrences={cloud.data.max_occurrences} />
          </div>
        ) : null}
        <p className={hint}>Click a term to run that search yourself.</p>
      </section>

      <section>
        <h2 className={panelHeading}>Activity per day</h2>
        <div className="mt-3">
          <Sparkbars
            data={data.by_day.map((row) => ({
              label: String(row.day),
              value: Number(row.SEARCH ?? 0),
            }))}
            emptyMessage="No searches recorded in this window."
          />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className={panelHeading}>Most-run searches</h2>
          <p className={hint}>The top {data.limit}, busiest first.</p>
          <div className="mt-3">
            <DataTable<SearchRow>
              caption="Most-run searches"
              columns={searchColumns}
              rows={data.top_searches}
              rowKey={(row) => row.query}
              emptyTitle="No searches in this window"
              emptyBody="Nothing was searched for in this period."
            />
          </div>
        </section>

        <section className="space-y-4">
          <h2 className={panelHeading}>Where the interest is</h2>
          <DimensionTable title="Nation" rows={data.by_nation} />
          <DimensionTable title="Category" rows={data.by_category} />
        </section>
      </div>

      <section>
        <h2 className={panelHeading}>Institutions candidates engage with</h2>
        <p className={hint}>
          The top {data.limit} by activity — not the whole estate. For that, see Trends.
        </p>
        <div className="mt-3">
          <DataTable<InstitutionRow>
            caption="Institutions candidates engage with"
            columns={institutionColumns}
            rows={data.institutions}
            rowKey={(row) => row.slug}
            emptyTitle="No activity in this window"
            emptyBody="Nothing was viewed, saved or applied to in this period."
          />
        </div>
      </section>
    </div>
  );
}

function DimensionTable({ title, rows }: { title: string; rows: DimensionRow[] }) {
  if (rows.length === 0) return null;

  const columns: DataTableColumn<DimensionRow>[] = [
    { key: "value", header: title, isRowHeader: true, cell: (row) => row.value },
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
    <div>
      <h3 className="text-heading-sm font-semibold">{title}</h3>
      <div className="mt-2">
        <DataTable<DimensionRow>
          caption={`Engagement by ${title.toLowerCase()}`}
          columns={columns}
          rows={rows}
          rowKey={(row) => row.value}
        />
      </div>
    </div>
  );
}
