import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DataTable } from "./DataTable";
import type { DataTableColumn } from "./DataTable";

interface Row {
  id: number;
  name: string;
  outcome: string;
  found: number;
}

const rows: Row[] = [
  { id: 1, name: "University of Leeds", outcome: "OK", found: 42 },
  { id: 2, name: "Bangor University", outcome: "BLOCKED", found: 0 },
];

const columns: DataTableColumn<Row>[] = [
  { key: "name", header: "Institution", cell: (row) => row.name, isRowHeader: true, sortable: true },
  { key: "outcome", header: "Outcome", cell: (row) => row.outcome },
  { key: "found", header: "Found", cell: (row) => row.found, numeric: true, sortable: true },
];

function renderTable(props: Partial<React.ComponentProps<typeof DataTable<Row>>> = {}) {
  return render(
    <DataTable<Row>
      caption="Crawl console"
      columns={columns}
      rows={rows}
      rowKey={(row) => row.id}
      {...props}
    />,
  );
}

describe("DataTable", () => {
  it("stays a table to assistive technology even where display is overridden", () => {
    renderTable();

    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    expect(within(table).getAllByRole("rowheader")).toHaveLength(2);
  });

  it("names the row by its row header, not by an arbitrary first cell", () => {
    renderTable();
    expect(screen.getByRole("rowheader", { name: "University of Leeds" })).toBeInTheDocument();
  });

  it("states the sort order in the caption, so the row order is never unexplained", () => {
    renderTable({ sort: { key: "found", direction: "desc" }, onSort: vi.fn() });
    expect(screen.getByText("Crawl console, sorted by found descending")).toBeInTheDocument();
  });

  it("falls back to the bare caption when nothing is sorted", () => {
    renderTable();
    expect(screen.getByText("Crawl console")).toBeInTheDocument();
  });

  it("marks the sorted column for assistive technology", () => {
    renderTable({ sort: { key: "found", direction: "asc" }, onSort: vi.fn() });

    expect(screen.getByRole("columnheader", { name: /Found/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
    expect(screen.getByRole("columnheader", { name: /Institution/ })).toHaveAttribute(
      "aria-sort",
      "none",
    );
  });

  it("leaves a non-sortable column with no sort state at all", () => {
    renderTable({ sort: { key: "found", direction: "asc" }, onSort: vi.fn() });
    expect(screen.getByRole("columnheader", { name: "Outcome" })).not.toHaveAttribute("aria-sort");
  });

  it("reports which column was asked for", async () => {
    const onSort = vi.fn();
    renderTable({ onSort });

    await userEvent.click(screen.getByRole("button", { name: /Institution/ }));
    expect(onSort).toHaveBeenCalledWith("name");
  });

  it("renders headers as plain text when there is no sort handler to call", () => {
    renderTable();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("flags an alarming row in the DOM rather than by tint alone", () => {
    renderTable({ rowAlarming: (row) => row.outcome !== "OK" });

    const flagged = screen.getAllByRole("row").filter((row) => row.dataset.alarming === "true");
    expect(flagged).toHaveLength(1);
    expect(within(flagged[0]!).getByText("Bangor University")).toBeInTheDocument();
  });

  it("shows placeholder rows while loading, and no real data", () => {
    renderTable({ loading: true });

    expect(screen.queryByText("University of Leeds")).not.toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(6);
  });

  it("replaces the whole table with an empty panel when there are no rows", () => {
    renderTable({ rows: [], emptyTitle: "No institutions", emptyBody: "Seed the register first." });

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "No institutions" })).toBeInTheDocument();
  });

  it("does not show the empty panel while rows are still loading", () => {
    renderTable({ rows: [], loading: true });
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("replaces the table with an alert on error — a half-loaded table is worse than none", () => {
    renderTable({ error: "Could not load the console." });

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load the console.");
  });

  it("wraps a scroll-mode table in a keyboard-reachable region", () => {
    renderTable({ belowMd: "scroll" });

    const region = screen.getByRole("region", { name: "Crawl console" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(within(region).getByRole("table")).toBeInTheDocument();
  });

  it("labels every cell in card mode, since the header row is off screen there", () => {
    renderTable();
    expect(screen.getAllByText("Outcome")).toHaveLength(3);
    expect(screen.getAllByText("Found")).toHaveLength(3);
  });
});
