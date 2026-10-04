import type { Meta, StoryObj } from "@storybook/react-vite";

import { FitRing } from "./FitRing";

const meta: Meta<typeof FitRing> = {
  title: "Primitives/FitRing",
  component: FitRing,
  args: { score: 72 },
};

export default meta;
type Story = StoryObj<typeof FitRing>;

export const High: Story = { args: { score: 88 } };
export const Medium: Story = { args: { score: 58 } };
export const Low: Story = { args: { score: 21 } };

export const ScoredZero: Story = { args: { score: 0 } };

export const NoProfile: Story = { args: { score: null } };

export const Sizes: Story = {
  render: () => (
    <div className="flex items-center gap-4">
      <FitRing score={82} size="sm" />
      <FitRing score={82} size="md" />
      <FitRing score={82} size="lg" />
    </div>
  ),
};
