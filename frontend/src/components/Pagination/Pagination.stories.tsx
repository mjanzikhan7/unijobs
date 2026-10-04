import type { Meta, StoryObj } from "@storybook/react-vite";

import { Pagination } from "./Pagination";

const meta: Meta<typeof Pagination> = {
  title: "Primitives/Pagination",
  component: Pagination,
  args: { page: 3, totalPages: 12, hasPrevious: true, hasNext: true, onChange: () => {} },
};

export default meta;
type Story = StoryObj<typeof Pagination>;

export const Middle: Story = {};
export const FirstPage: Story = { args: { page: 1, hasPrevious: false } };
export const LastPage: Story = { args: { page: 12, hasNext: false } };

export const SinglePage: Story = {
  args: { page: 1, totalPages: 1, hasPrevious: false, hasNext: false },
};
