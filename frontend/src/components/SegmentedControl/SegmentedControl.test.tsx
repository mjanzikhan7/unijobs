import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { SegmentedControl } from "./SegmentedControl";

const windows = [
  { value: "7", label: "7d" },
  { value: "30", label: "30d" },
  { value: "90", label: "90d" },
];

function Harness({ initial = "30" }: { initial?: string }) {
  const [value, setValue] = useState(initial);
  return (
    <SegmentedControl label="Time window" options={windows} value={value} onChange={setValue} />
  );
}

describe("SegmentedControl", () => {
  it("exposes one group with one option checked", () => {
    render(<Harness />);

    expect(screen.getByRole("radiogroup", { name: "Time window" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "30d" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "7d" })).not.toBeChecked();
  });

  it("moves the selection when another segment is clicked", async () => {
    render(<Harness />);

    await userEvent.click(screen.getByRole("radio", { name: "90d" }));

    expect(screen.getByRole("radio", { name: "90d" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "30d" })).not.toBeChecked();
  });

  it("reports the chosen value, not the label", async () => {
    const onChange = vi.fn();
    render(
      <SegmentedControl label="Time window" options={windows} value="7" onChange={onChange} />,
    );

    await userEvent.click(screen.getByRole("radio", { name: "90d" }));

    expect(onChange).toHaveBeenCalledWith("90");
  });

  it("does not fire for a disabled segment", async () => {
    const onChange = vi.fn();
    render(
      <SegmentedControl
        label="Time window"
        options={[...windows, { value: "365", label: "365d", disabled: true }]}
        value="7"
        onChange={onChange}
      />,
    );

    await userEvent.click(screen.getByRole("radio", { name: "365d" }));

    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByRole("radio", { name: "365d" })).toBeDisabled();
  });

  it("keeps two controls on one page independent", async () => {
    render(
      <>
        <Harness initial="7" />
        <SegmentedControl
          label="Digest"
          name="digest"
          options={[
            { value: "daily", label: "Daily" },
            { value: "weekly", label: "Weekly" },
          ]}
          value="weekly"
          onChange={() => {}}
        />
      </>,
    );

    await userEvent.click(screen.getByRole("radio", { name: "90d" }));

    expect(screen.getByRole("radio", { name: "90d" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Weekly" })).toBeChecked();
  });

  it("contains its own absolutely-positioned radios", () => {
    render(<Harness />);

    expect(screen.getByRole("radiogroup").className).toContain("relative");
  });
});
