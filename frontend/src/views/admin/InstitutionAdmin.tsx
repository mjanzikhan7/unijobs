import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "@/components/Button/Button";
import { DataTable } from "@/components/DataTable/DataTable";
import type { DataTableColumn } from "@/components/DataTable/DataTable";
import { Input } from "@/components/Field/Input";
import { ErrorMessage } from "@/components/Feedback";
import { Notice } from "@/components/Notice/Notice";
import { InstitutionBranding } from "@/views/admin/InstitutionBranding";
import { ApiError } from "@/models/api/client";
import type { Institution } from "@/models/api/types";
import { useAuth } from "@/viewmodels/auth";
import { useDeleteInstitution, useInstitutions, useUpdateInstitution } from "@/viewmodels/useInstitutions";

export function InstitutionAdmin() {
  const { role } = useAuth();
  const navigate = useNavigate();
  const institutions = useInstitutions();
  const update = useUpdateInstitution();
  const remove = useDeleteInstitution();

  const isAdmin = role === "ADMIN";
  const [term, setTerm] = useState("");
  const [chosenRow, setEditingBranding] = useState<number | null | undefined>(undefined);

  const [searchParams] = useSearchParams();
  const editSlug = searchParams.get("edit");
  const linkedRow = editSlug
    ? (institutions.data?.results.find((row) => row.slug === editSlug)?.id ?? null)
    : null;
  const editingBranding = chosenRow === undefined ? linkedRow : chosenRow;

  if (institutions.isError) {
    return <ErrorMessage error={institutions.error} onRetry={() => void institutions.refetch()} />;
  }

  const needle = term.trim().toLowerCase();
  const rows = (institutions.data?.results ?? []).filter(
    (row) => !needle || row.name.toLowerCase().includes(needle),
  );
  const refusal = [update.error, remove.error].find(
    (error): error is ApiError => error instanceof ApiError,
  );

  const columns: DataTableColumn<Institution>[] = [
    {
      key: "name",
      header: "Name",
      isRowHeader: true,
      cell: (row) => (
        <Link to={`/institutions/${row.slug}`} className="text-brand underline underline-offset-2 hover:decoration-2">
          {row.name}
        </Link>
      ),
    },
    {
      key: "platform",
      header: "Platform",
      cell: (row) => row.effective_platform ?? row.platform,
    },
    { key: "open", header: "Open jobs", numeric: true, cell: (row) => row.open_jobs ?? 0 },
    {
      key: "crawling",
      header: "Crawling",
      cell: (row) => (
        <>
          <label className="sr-only" htmlFor={`crawl-${row.id}`}>
            Crawl {row.name}
          </label>
          <input
            id={`crawl-${row.id}`}
            type="checkbox"
            checked={row.crawl_enabled}
            onChange={(event) =>
              update.mutate({ id: row.id, changes: { crawl_enabled: event.target.checked } })
            }
            className="h-5 w-5 accent-[var(--color-brand)]"
          />
        </>
      ),
    },
    {
      key: "branding",
      header: "Branding",
      cell: (row) =>
        isAdmin ? (
          <Button
            variant="quiet"
            size="sm"
            aria-expanded={editingBranding === row.id}
            onClick={() => setEditingBranding(editingBranding === row.id ? null : row.id)}
          >
            {editingBranding === row.id ? "Close" : "Logo, banner, about"}
          </Button>
        ) : (
          <span className="text-text-muted">admin only</span>
        ),
    },
    {
      key: "actions",
      header: "Actions",
      cell: (row) =>
        isAdmin ? (
          <Button
            variant="quiet"
            size="sm"
            onClick={() => remove.mutate(row.id)}
          >
            Delete
          </Button>
        ) : null,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="font-display text-heading-xl font-bold">Manage institutions</h1>
        {isAdmin ? (
          <Button variant="primary" onClick={() => void navigate("/admin/institutions/new")}>
            Add institution
          </Button>
        ) : null}
      </div>

      {!isAdmin ? (
        <Notice tone="info">
          You can change how an institution is crawled. Adding, removing and renaming are an
          administrator&rsquo;s.
        </Notice>
      ) : null}

      {refusal ? <Notice tone="warning">{refusal.message}</Notice> : null}

      <div>
        <label className="sr-only" htmlFor="institution-admin-filter">
          Filter
        </label>
        <Input
          id="institution-admin-filter"
          type="search"
          placeholder="Filter by name"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          className="max-w-xs"
        />
      </div>

      <DataTable<Institution>
        caption="Institutions"
        columns={columns}
        rows={rows}
        rowKey={(row) => row.id}
        loading={institutions.isLoading}
        emptyTitle="No institutions match"
        emptyBody="Clear the filter, or add one above."
      />

      {editingBranding !== null ? (
        <section>
          {rows
            .filter((row) => row.id === editingBranding)
            .map((row) => (
              <InstitutionBranding key={row.id} institution={row} />
            ))}
        </section>
      ) : null}
    </div>
  );
}
