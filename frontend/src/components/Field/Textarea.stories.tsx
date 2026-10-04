import type { Meta, StoryObj } from "@storybook/react-vite";

import { Textarea } from "./Textarea";

const meta: Meta<typeof Textarea> = {
  title: "Primitives/Field/Textarea",
  component: Textarea,
  args: { placeholder: "Shown on the institution's page. Plain text — line breaks are kept." },
};

export default meta;
type Story = StoryObj<typeof Textarea>;

export const Default: Story = {};
export const TenRows: Story = { args: { rows: 10 } };
export const Error: Story = { args: { error: true } };
