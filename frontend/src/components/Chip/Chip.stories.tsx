import type { Meta, StoryObj } from "@storybook/react-vite";

import { Chip } from "./Chip";

const meta: Meta<typeof Chip> = {
  title: "Primitives/Chip",
  component: Chip,
};

export default meta;
type Story = StoryObj<typeof Chip>;

export const OutlineNeutral: Story = { args: { children: "Permanent" } };
export const SolidPositive: Story = { args: { tone: "positive", variant: "solid", children: "Hybrid" } };

export const JobCardAttributes: StoryObj = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <Chip variant="outline">Permanent</Chip>
      <Chip variant="outline">Full time</Chip>
      <Chip tone="positive" variant="solid">
        Hybrid
      </Chip>
    </div>
  ),
};
