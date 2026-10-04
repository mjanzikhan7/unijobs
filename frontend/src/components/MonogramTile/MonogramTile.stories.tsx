import type { Meta, StoryObj } from "@storybook/react-vite";

import { MonogramTile } from "./MonogramTile";

const meta: Meta<typeof MonogramTile> = {
  title: "Primitives/MonogramTile",
  component: MonogramTile,
  args: { name: "Northgate University" },
};

export default meta;
type Story = StoryObj<typeof MonogramTile>;

export const Default: Story = {};

export const Sizes: Story = {
  render: () => (
    <div className="flex items-center gap-3">
      <MonogramTile name="Northgate University" size="sm" />
      <MonogramTile name="Northgate University" size="md" />
      <MonogramTile name="Northgate University" size="lg" />
    </div>
  ),
};

export const RealNames: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-3">
      {[
        "University of Test",
        "The Open University",
        "Brackenfield Institute of Technology",
        "Royal Holloway, University of London",
        "Cranfield",
      ].map((name) => (
        <span key={name} className="flex items-center gap-2 text-body-sm">
          <MonogramTile name={name} />
          {name}
        </span>
      ))}
    </div>
  ),
};
