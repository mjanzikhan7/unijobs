import type { Meta, StoryObj } from "@storybook/react-vite";

import { StatCard } from "./StatCard";

const meta: Meta<typeof StatCard> = {
  title: "Primitives/StatCard",
  component: StatCard,
  args: { label: "Vacancies first seen", value: 1284 },
};

export default meta;
type Story = StoryObj<typeof StatCard>;

export const Default: Story = {};
export const WithHint: Story = { args: { hint: "In the last 30 days" } };

export const Warn: Story = {
  args: {
    label: "Searches that found nothing",
    value: "34%",
    tone: "warn",
    hint: "Above the 30% threshold",
  },
};

export const Loading: Story = { args: { loading: true } };

export const Row: Story = {
  render: () => (
    <div className="grid gap-4 sm:grid-cols-3">
      <StatCard label="Vacancies first seen" value={1284} />
      <StatCard label="Open right now" value={874} />
      <StatCard label="Searches that found nothing" value="34%" tone="warn" hint="Above 30%" />
    </div>
  ),
};
