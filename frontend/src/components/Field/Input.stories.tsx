import type { Meta, StoryObj } from "@storybook/react-vite";

import { Input } from "./Input";

const meta: Meta<typeof Input> = {
  title: "Primitives/Field/Input",
  component: Input,
  args: { placeholder: "e.g. UK Research and Innovation" },
};

export default meta;
type Story = StoryObj<typeof Input>;

export const Default: Story = {};
export const WithValue: Story = { args: { defaultValue: "a.morgan@example.com" } };
export const Error: Story = { args: { error: true, defaultValue: "not-an-email" } };
export const Disabled: Story = { args: { disabled: true, defaultValue: "a.morgan@example.com" } };
