import type { Meta, StoryObj } from "@storybook/react-vite";

import { Button } from "./Button";

const meta: Meta<typeof Button> = {
  title: "Primitives/Button",
  component: Button,
  args: { children: "Run search" },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Secondary: Story = { args: { variant: "secondary" } };
export const Primary: Story = { args: { variant: "primary", children: "Save changes" } };
export const Quiet: Story = { args: { variant: "quiet", children: "Cancel" } };

export const CTA: Story = { args: { variant: "cta", children: "Apply on the employer's site" } };

export const Disabled: Story = { args: { variant: "primary", disabled: true, children: "Save" } };

export const Small: Story = { args: { size: "sm", children: "Withdraw" } };

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-3">
      <Button variant="secondary">Secondary</Button>
      <Button variant="primary">Primary</Button>
      <Button variant="quiet">Quiet</Button>
      <Button variant="cta">CTA</Button>
      <Button variant="primary" disabled>
        Disabled
      </Button>
    </div>
  ),
};
