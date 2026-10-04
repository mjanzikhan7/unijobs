import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { SegmentedControl } from "./SegmentedControl";

const meta: Meta<typeof SegmentedControl> = {
  title: "Primitives/SegmentedControl",
  component: SegmentedControl,
};

export default meta;
type Story = StoryObj<typeof SegmentedControl>;

const windows = [
  { value: "7", label: "7d" },
  { value: "30", label: "30d" },
  { value: "90", label: "90d" },
  { value: "365", label: "365d" },
];

export const TimeWindow: Story = {
  render: function TimeWindowStory() {
    const [value, setValue] = useState("30");
    return (
      <SegmentedControl label="Time window" options={windows} value={value} onChange={setValue} />
    );
  },
};

export const TwoOptions: Story = {
  render: function TwoOptionsStory() {
    const [value, setValue] = useState("weekly");
    return (
      <SegmentedControl
        label="Digest"
        options={[
          { value: "daily", label: "Daily" },
          { value: "weekly", label: "Weekly" },
        ]}
        value={value}
        onChange={setValue}
      />
    );
  },
};

export const WithDisabledOption: Story = {
  render: function DisabledStory() {
    const [value, setValue] = useState("7");
    return (
      <SegmentedControl
        label="Time window"
        options={[...windows.slice(0, 3), { value: "365", label: "365d", disabled: true }]}
        value={value}
        onChange={setValue}
      />
    );
  },
};
