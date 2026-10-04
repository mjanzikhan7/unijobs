import type { Meta, StoryObj } from "@storybook/react-vite";

import { Button } from "@/components/Button/Button";

import { EmptyPanel } from "./EmptyPanel";

const meta: Meta<typeof EmptyPanel> = {
  title: "Primitives/EmptyPanel",
  component: EmptyPanel,
};

export default meta;
type Story = StoryObj<typeof EmptyPanel>;

export const NothingCrawledYet: Story = {
  args: {
    title: "No vacancies yet",
    body: "Nothing has been crawled into this view. Start a crawl from the console to populate it.",
  },
};

export const FilteredToNothing: Story = {
  args: {
    title: "No jobs match these filters",
    body: "Minimum fitness (70) is the most restrictive filter you have on.",
    action: (
      <>
        <Button>Clear minimum fitness</Button>
        <Button variant="quiet">Clear all 4 filters</Button>
      </>
    ),
  },
};

export const WithIcon: Story = {
  args: {
    icon: (
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="11" cy="11" r="7" strokeWidth="2" />
        <path d="m16.5 16.5 4 4" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
    title: "No saved jobs",
    body: "Jobs you save from the search results will collect here.",
    action: <Button variant="primary">Search vacancies</Button>,
  },
};
