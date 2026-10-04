import type { Meta, StoryObj } from "@storybook/react-vite";

import { Skeleton } from "./Skeleton";

const meta: Meta<typeof Skeleton> = {
  title: "Primitives/Skeleton",
  component: Skeleton,
};

export default meta;
type Story = StoryObj<typeof Skeleton>;

export const Line: Story = { args: { className: "h-4 w-full" } };
export const Title: Story = { args: { className: "h-5 w-3/5" } };
export const Avatar: Story = { args: { className: "h-11 w-11 rounded-full" } };
export const Badge: Story = { args: { className: "h-6 w-24 rounded-full" } };

export const JobCardShape: Story = {
  render: () => (
    <div className="max-w-md space-y-2 rounded-md border border-border-subtle bg-surface p-5">
      <Skeleton className="h-5 w-3/5" />
      <Skeleton className="h-4 w-2/5" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-6 w-24 rounded-full" />
    </div>
  ),
};
