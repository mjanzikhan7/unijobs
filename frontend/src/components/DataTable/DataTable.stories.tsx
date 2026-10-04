import type { Meta, StoryObj } from "@storybook/react-vite";

import { Badge } from "@/components/Badge/Badge";

import { DataTable } from "./DataTable";
import type { DataTableColumn } from "./DataTable";

interface Row {
  id: number;
  name: string;
  outcome: "OK" | "BLOCKED" | "ZERO_RESULTS";
  found: number;
  previously: number;
}

const rows: Row[] = [
  { id: 1, name: "University of Leeds", outcome: "OK", found: 42, previously: 39 },
  { id: 2, name: "Bangor University", outcome: "BLOCKED", found: 0, previously: 18 },
  { id: 3, name: "Royal Holloway", outcome: "ZERO_RESULTS", found: 0, previously: 24 },
  { id: 4, name: "University of Dundee", outcome: "OK", found: 31, previously: 30 },
];

const columns: DataTableColumn<Row>[] = [
  { key: "name", header: "Institution", cell: (row) => row.name, isRowHeader: true, sortable: true },
  {
    key: "outcome",
    header: "Outcome",
    cell: (row) => (
      <Badge tone={row.outcome === "OK" ? "positive" : "negative"}>{row.outcome}</Badge>
    ),
  },
  { key: "found", header: "Found", cell: (row) => row.found, numeric: true, sortable: true },
  { key: "previously", header: "Previously", cell: (row) => row.previously, numeric: true },
];

const meta: Meta<typeof DataTable<Row>> = {
  title: "Primitives/DataTable",
  component: DataTable,
  args: { caption: "Crawl console", columns, rows, rowKey: (row: Row) => row.id },
};

export default meta;
type Story = StoryObj<typeof DataTable<Row>>;

export const Default: Story = {};

export const Sorted: Story = {
  args: { sort: { key: "found", direction: "desc" }, onSort: () => {} },
};

export const WithAlarmingRows: Story = {
  args: { rowAlarming: (row: Row) => row.outcome !== "OK" },
};

export const Loading: Story = { args: { loading: true } };

export const Empty: Story = {
  args: {
    rows: [],
    emptyTitle: "No institutions yet",
    emptyBody: "Seed the register, then run a crawl to populate this table.",
  },
};

export const Error: Story = { args: { error: "Could not load the crawl console." } };

export const ScrollBelowMd: Story = { args: { belowMd: "scroll" } };
