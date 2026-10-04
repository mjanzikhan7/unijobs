import type { Meta, StoryObj } from "@storybook/react-vite";

import { Select } from "./Select";

const meta: Meta<typeof Select> = {
  title: "Primitives/Field/Select",
  component: Select,
};

export default meta;
type Story = StoryObj<typeof Select>;

export const Default: Story = {
  render: () => (
    <Select aria-label="Role" defaultValue="CANDIDATE">
      <option value="ADMIN">ADMIN</option>
      <option value="MANAGER">MANAGER</option>
      <option value="CANDIDATE">CANDIDATE</option>
    </Select>
  ),
};

export const Disabled: Story = {
  render: () => (
    <Select aria-label="Role" disabled defaultValue="CANDIDATE">
      <option value="CANDIDATE">CANDIDATE</option>
    </Select>
  ),
};
