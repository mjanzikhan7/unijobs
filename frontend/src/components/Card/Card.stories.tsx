import type { Meta, StoryObj } from "@storybook/react-vite";

import { Card } from "./Card";

const meta: Meta<typeof Card> = {
  title: "Primitives/Card",
  component: Card,
  args: {
    children: (
      <>
        <p className="text-heading-sm font-semibold text-text-primary">Northgate University</p>
        <p className="text-body-sm text-text-muted">Leeds · England · 64 open</p>
      </>
    ),
  },
};

export default meta;
type Story = StoryObj<typeof Card>;

export const Small: Story = { args: { padding: "sm" } };
export const Medium: Story = { args: { padding: "md" } };
export const Large: Story = { args: { padding: "lg" } };

export const Interactive: Story = { args: { interactive: true } };
