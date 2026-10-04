import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Sparkbars } from "./Sparkbars";

describe("Sparkbars", () => {
  it("renders a bar per point, tallest first scaled to 100%", () => {
    render(
      <Sparkbars
        data={[
          { label: "2026-09-01", value: 4 },
          { label: "2026-09-02", value: 8 },
        ]}
      />,
    );

    expect(screen.getByText("2026-09-01: 4")).toBeInTheDocument();
    expect(screen.getByText("2026-09-02: 8")).toBeInTheDocument();
  });

  it("gives even a zero-value bar a visible sliver, not a collapsed one", () => {
    render(
      <Sparkbars
        data={[
          { label: "day 1", value: 0 },
          { label: "day 2", value: 10 },
        ]}
      />,
    );

    const bar = screen.getByTitle("day 1: 0");
    expect(bar).toHaveStyle({ height: "2%" });
  });

  it("shows the empty message when there is no data", () => {
    render(<Sparkbars data={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent("Nothing recorded in this window.");
  });

  it("shows the empty message when every value is zero", () => {
    render(<Sparkbars data={[{ label: "day 1", value: 0 }]} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("accepts a custom empty message", () => {
    render(<Sparkbars data={[]} emptyMessage="No searches recorded in this window." />);
    expect(screen.getByText("No searches recorded in this window.")).toBeInTheDocument();
  });
});
