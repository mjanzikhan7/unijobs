/* eslint-disable jsx-a11y/no-redundant-roles, jsx-a11y/no-interactive-element-to-noninteractive-role */
import type { ReactNode } from "react";

import { EmptyPanel } from "@/components/EmptyPanel/EmptyPanel";
import { Notice } from "@/components/Notice/Notice";
import { Skeleton } from "@/components/Skeleton/Skeleton";

export type SortDirection = "asc" | "desc";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  isRowHeader?: boolean;
  numeric?: boolean;
  sortable?: boolean;
}

export interface DataTableProps<T> {
  caption: string;
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  loading?: boolean;
  error?: ReactNode;
  emptyTitle?: string;
  emptyBody?: ReactNode;
  sort?: { key: string; direction: SortDirection };
  onSort?: (key: string) => void;
  rowAlarming?: (row: T) => boolean;
  belowMd?: "cards" | "scroll";
  stickyHeader?: boolean;
}

const SKELETON_ROWS = 5;

function ariaSort(
  column: DataTableColumn<unknown>,
  sort: DataTableProps<unknown>["sort"],
): "ascending" | "descending" | "none" | undefined {
  if (!column.sortable) return undefined;
  if (sort?.key !== column.key) return "none";
  return sort.direction === "asc" ? "ascending" : "descending";
}

export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  loading = false,
  error,
  emptyTitle = "Nothing to show",
  emptyBody = "No rows matched.",
  sort,
  onSort,
  rowAlarming,
  belowMd = "cards",
  stickyHeader = false,
}: DataTableProps<T>) {
  if (error) {
    return <Notice tone="danger">{error}</Notice>;
  }

  if (!loading && rows.length === 0) {
    return <EmptyPanel title={emptyTitle} body={emptyBody} />;
  }

  const sortedColumn = sort ? columns.find((column) => column.key === sort.key) : undefined;
  const fullCaption = sortedColumn
    ? `${caption}, sorted by ${sortedColumn.header.toLowerCase()} ${sort?.direction === "asc" ? "ascending" : "descending"}`
    : caption;

  const cards = belowMd === "cards";

  const table = (
    <table
      role="table"
      className={`w-full border-collapse text-body-sm ${cards ? "max-md:block" : ""}`}
    >
      <caption className="sr-only">{fullCaption}</caption>

      <thead role="rowgroup" className={cards ? "max-md:hidden" : ""}>
        <tr role="row" className="border-b border-border-strong">
          {columns.map((column) => (
            <th
              key={column.key}
              role="columnheader"
              scope="col"
              aria-sort={ariaSort(column as DataTableColumn<unknown>, sort)}
              className={[
                "px-3 py-2 text-caption font-semibold tracking-wide text-text-secondary uppercase",
                column.numeric ? "text-right" : "text-left",
                stickyHeader ? "sticky top-0 z-10 bg-surface" : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {column.sortable && onSort ? (
                <button
                  type="button"
                  onClick={() => onSort(column.key)}
                  className="inline-flex items-center gap-1 rounded-xs uppercase hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus-ring)]"
                >
                  {column.header}
                  <span aria-hidden="true" className="text-text-muted">
                    {sort?.key === column.key ? (sort.direction === "asc" ? "▲" : "▼") : "↕"}
                  </span>
                </button>
              ) : (
                column.header
              )}
            </th>
          ))}
        </tr>
      </thead>

      <tbody role="rowgroup" className={cards ? "max-md:block max-md:space-y-3" : ""}>
        {loading
          ? Array.from({ length: SKELETON_ROWS }, (_, index) => (
              <tr key={`skeleton-${index}`} role="row" className={cards ? "max-md:block" : ""}>
                {columns.map((column) => (
                  <td
                    key={column.key}
                    role="cell"
                    className={`px-3 py-3 ${cards ? "max-md:block" : ""}`}
                  >
                    <Skeleton className="h-4 w-4/5" />
                  </td>
                ))}
              </tr>
            ))
          : rows.map((row) => {
              const alarming = rowAlarming?.(row) ?? false;
              return (
                <tr
                  key={rowKey(row)}
                  role="row"
                  data-alarming={alarming || undefined}
                  className={[
                    "border-b border-border-subtle",
                    alarming ? "bg-danger-bg" : "hover:bg-surface-sunken",
                    cards
                      ? "max-md:block max-md:rounded-md max-md:border max-md:border-border-subtle max-md:bg-surface max-md:p-4"
                      : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  {columns.map((column) => {
                    const content = column.cell(row);
                    const shared = [
                      "px-3 py-3 align-middle",
                      column.numeric ? "text-right tabular-nums" : "text-left",
                      cards ? "max-md:flex max-md:justify-between max-md:gap-4 max-md:px-0" : "",
                    ]
                      .filter(Boolean)
                      .join(" ");

                    const label = (
                      <span className="text-caption text-text-muted md:hidden">
                        {column.header}
                      </span>
                    );

                    return column.isRowHeader ? (
                      <th
                        key={column.key}
                        role="rowheader"
                        scope="row"
                        className={`${shared} font-medium text-text-primary max-md:block max-md:pb-2 max-md:text-body`}
                      >
                        {content}
                      </th>
                    ) : (
                      <td key={column.key} role="cell" className={`${shared} text-text-secondary`}>
                        {label}
                        <span>{content}</span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
      </tbody>
    </table>
  );

  if (belowMd === "scroll") {
    return (
      <div className="overflow-x-auto" role="region" aria-label={caption} tabIndex={0}>
        {table}
      </div>
    );
  }

  return table;
}
