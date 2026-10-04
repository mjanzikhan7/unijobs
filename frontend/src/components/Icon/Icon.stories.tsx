import type { Meta, StoryObj } from "@storybook/react-vite";

import { Icon } from "./Icon";
import type { IconName } from "./Icon";

const ALL: IconName[] = [
  "jobs",
  "institutions",
  "saved",
  "pipeline",
  "cv",
  "account",
  "insights",
  "trends",
  "crawl",
  "review",
  "manage-jobs",
  "manage-institutions",
  "users",
  "thresholds",
  "menu",
  "close",
  "chevron-left",
  "chevron-right",
  "mail",
  "phone",
  "map-pin",
  "external-link",
];

const meta: Meta<typeof Icon> = {
  title: "Primitives/Icon",
  component: Icon,
  args: { name: "jobs" },
};

export default meta;
type Story = StoryObj<typeof Icon>;

export const Default: Story = {};

export const AllIcons: Story = {
  render: () => (
    <div className="grid grid-cols-6 gap-4 text-text-primary">
      {ALL.map((name) => (
        <div key={name} className="flex flex-col items-center gap-1 text-caption text-text-muted">
          <Icon name={name} className="h-6 w-6" />
          {name}
        </div>
      ))}
    </div>
  ),
};

export const CrawlActive: Story = {
  render: () => (
    <Icon name="crawl" className="h-6 w-6 text-success motion-safe:animate-spin" />
  ),
};
