import type { Meta, StoryObj } from "@storybook/react-vite";

import { FileInput } from "./FileInput";

const meta: Meta<typeof FileInput> = {
  title: "Primitives/Field/FileInput",
  component: FileInput,
  args: { id: "logo", label: "Upload a logo", onFileChange: () => {} },
};

export default meta;
type Story = StoryObj<typeof FileInput>;

export const Default: Story = {};
export const CustomLabel: Story = { args: { buttonLabel: "Choose logo" } };
export const WithAFileChosen: Story = { args: { fileName: "northgate-logo.png" } };
export const Disabled: Story = { args: { disabled: true, fileName: "northgate-logo.png" } };
