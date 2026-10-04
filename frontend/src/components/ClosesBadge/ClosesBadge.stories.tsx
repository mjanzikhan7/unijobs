import type { Meta, StoryObj } from "@storybook/react-vite";

import { ClosesBadge } from "./ClosesBadge";

function inDays(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

const meta: Meta<typeof ClosesBadge> = {
  title: "Primitives/ClosesBadge",
  component: ClosesBadge,
};

export default meta;
type Story = StoryObj<typeof ClosesBadge>;

export const Later: Story = { args: { value: inDays(21) } };
export const Urgent: Story = { args: { value: inDays(2) } };

export const Today: Story = { args: { value: inDays(0) } };

export const Closed: Story = { args: { value: inDays(-4) } };
export const NoDate: Story = { args: { value: null } };

export const AllStates: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-2">
      <ClosesBadge value={inDays(21)} />
      <ClosesBadge value={inDays(2)} />
      <ClosesBadge value={inDays(0)} />
      <ClosesBadge value={inDays(-4)} />
      <ClosesBadge value={null} />
    </div>
  ),
};
