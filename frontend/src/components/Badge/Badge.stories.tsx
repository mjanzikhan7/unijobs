import type { Meta, StoryObj } from "@storybook/react-vite";

import { Badge, MissingBadge, SponsorBadge, ThresholdBadge } from "./Badge";

const meta: Meta<typeof Badge> = {
  title: "Primitives/Badge",
  component: Badge,
};

export default meta;
type Story = StoryObj<typeof Badge>;

export const Positive: Story = { args: { tone: "positive", children: "Sponsor confirmed" } };
export const Caution: Story = { args: { tone: "caution", children: "B-rated sponsor" } };
export const Negative: Story = { args: { tone: "negative", children: "No sponsor licence found" } };
export const Neutral: Story = { args: { tone: "neutral", children: "Withdrawn" } };
export const Unknown: Story = { args: { tone: "unknown", children: "⚠ Not screened" } };

export const AllSponsorVerdicts: StoryObj = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <SponsorBadge verdict="CONFIRMED" />
      <SponsorBadge verdict="CONFIRMED_VIA_PARENT" />
      <SponsorBadge verdict="B_RATED" />
      <SponsorBadge verdict="PROVISIONAL" />
      <SponsorBadge verdict="OTHER_ROUTE_ONLY" />
      <SponsorBadge verdict="NOT_FOUND" />
      <SponsorBadge verdict={null} />
      <SponsorBadge verdict="CONFIRMED" advertExcludes />
    </div>
  ),
};

export const AllThresholdVerdicts: StoryObj = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <ThresholdBadge verdict="TARGET_BAND" />
      <ThresholdBadge verdict="LATERAL_CONTINGENT" />
      <ThresholdBadge verdict="PAY_CUT" />
      <ThresholdBadge verdict="EXCLUDED_BELOW_FLOOR" />
      <ThresholdBadge verdict="SALARY_UNCLEAR" />
      <ThresholdBadge verdict={null} />
    </div>
  ),
};

export const MissingVerdict: StoryObj = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <MissingBadge kind="sponsor" />
      <MissingBadge kind="threshold" />
    </div>
  ),
};
