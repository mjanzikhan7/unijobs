import type { Meta, StoryObj } from "@storybook/react-vite";
import { MemoryRouter } from "react-router-dom";

import { navFor } from "@/components/nav";

import { Sidebar } from "./Sidebar";

const meta: Meta<typeof Sidebar> = {
  title: "Shell/Sidebar",
  component: Sidebar,
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/saved"]}>
        <div className="w-[264px] border-r border-border-subtle bg-surface px-2">
          <Story />
        </div>
      </MemoryRouter>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof Sidebar>;

export const Candidate: Story = { args: { items: navFor("CANDIDATE") } };

export const Manager: Story = { args: { items: navFor("MANAGER") } };

export const Admin: Story = { args: { items: navFor("ADMIN") } };

export const CollapsedRail: Story = {
  args: { items: navFor("ADMIN"), collapsed: true },
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/saved"]}>
        <div className="w-[72px] border-r border-border-subtle bg-surface px-2">
          <Story />
        </div>
      </MemoryRouter>
    ),
  ],
};
