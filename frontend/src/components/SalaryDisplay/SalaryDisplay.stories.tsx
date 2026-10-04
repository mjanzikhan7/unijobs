import type { Meta, StoryObj } from "@storybook/react-vite";

import type { Screening } from "@/models/api/types";

import { SalaryDisplay } from "./SalaryDisplay";

const base: Screening = {
  sponsor_verdict: "CONFIRMED",
  threshold_verdict: "TARGET_BAND",
  ruleset_version: 1,
};

const meta: Meta<typeof SalaryDisplay> = {
  title: "Primitives/SalaryDisplay",
  component: SalaryDisplay,
};

export default meta;
type Story = StoryObj<typeof SalaryDisplay>;

export const ParsedRange: Story = {
  args: {
    screening: { ...base, salary_min: "38784", salary_max: "46049" },
    raw: "£38,784 to £46,049 per annum",
  },
};

export const FloorOnly: Story = {
  args: { screening: { ...base, salary_min: "38784" }, raw: "From £38,784 per annum" },
};

export const CeilingOnly: Story = {
  args: { screening: { ...base, salary_max: "46049" }, raw: "Up to £46,049 depending on skills" },
};

export const Unparseable: Story = {
  args: { screening: base, raw: "Competitive salary, dependent on experience" },
};

export const NotStated: Story = { args: { screening: base, raw: null } };

export const Small: Story = {
  args: {
    screening: { ...base, salary_min: "38784", salary_max: "46049" },
    raw: "£38,784 to £46,049 per annum",
    size: "sm",
  },
};
