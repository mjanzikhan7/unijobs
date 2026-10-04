import type { Meta, StoryObj } from "@storybook/react-vite";

import { Notice } from "./Notice";

const meta: Meta<typeof Notice> = {
  title: "Primitives/Notice",
  component: Notice,
};

export default meta;
type Story = StoryObj<typeof Notice>;

export const Info: Story = {
  args: {
    tone: "info",
    children:
      "Editing here creates a new version. The one in force is never changed, so every stored verdict stays explainable by the rules that produced it.",
  },
};

export const Warning: Story = {
  args: {
    tone: "warning",
    children:
      "This advert came from a crawl and is the employer's text. The next crawl would overwrite an edit and recreate a deletion.",
  },
};

export const Danger: Story = {
  args: {
    tone: "danger",
    children:
      "This institution still has 64 jobs. Deleting it would remove every candidate's saved copies and application history.",
  },
};

export const WithQuote: Story = {
  args: {
    tone: "danger",
    children: "This advert rules sponsorship out in its own terms.",
    quote: "Visa sponsorship is not available for this role.",
  },
};
