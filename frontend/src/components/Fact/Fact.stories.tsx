import type { Meta, StoryObj } from "@storybook/react-vite";

import { Fact } from "./Fact";

const meta: Meta<typeof Fact> = {
  title: "Primitives/Fact",
  component: Fact,
  decorators: [(Story) => <dl className="max-w-xs"><Story /></dl>],
};

export default meta;
type Story = StoryObj<typeof Fact>;

export const Default: Story = { args: { label: "Grade", value: "Grade 8" } };
export const Missing: Story = { args: { label: "Registered as", value: null } };
export const Zero: Story = { args: { label: "Open vacancies", value: 0 } };
export const Danger: Story = { args: { label: "Salary band", value: "£38,784 — below the floor", danger: true } };

export const FactsGrid: StoryObj = {
  render: () => (
    <dl className="grid max-w-md grid-cols-2 gap-4">
      <Fact label="Salary as advertised" value="Grade 8: £47,940 - £57,120 per annum" />
      <Fact label="Salary parsed" value="£47,940 – £57,120" />
      <Fact label="Grade" value="Grade 8" />
      <Fact label="Contract" value="Permanent" />
      <Fact label="Registered as" value={null} />
    </dl>
  ),
};
