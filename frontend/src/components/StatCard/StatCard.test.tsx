import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatCard } from "./StatCard";

describe("StatCard", () => {
  it("shows the figure and what it counts", () => {
    render(<StatCard label="Open right now" value={1_284} />);

    expect(screen.getByText("1284")).toBeInTheDocument();
    expect(screen.getByText("Open right now")).toBeInTheDocument();
  });

  it("renders a pre-formatted string untouched", () => {
    render(<StatCard label="Found nothing" value="34%" />);
    expect(screen.getByText("34%")).toBeInTheDocument();
  });

  it("omits the hint when there isn't one", () => {
    const { rerender } = render(<StatCard label="Open right now" value={12} />);
    expect(screen.queryByText(/searches/i)).not.toBeInTheDocument();

    rerender(<StatCard label="Open right now" value={12} hint="Across 4 searches" />);
    expect(screen.getByText("Across 4 searches")).toBeInTheDocument();
  });

  it("marks a warned card in the DOM, not by colour alone", () => {
    const { container } = render(
      <StatCard label="Found nothing" value="34%" tone="warn" hint="Above the 30% threshold" />,
    );

    expect(container.querySelector('[data-tone="warn"]')).toBeInTheDocument();
    expect(screen.getByText("Above the 30% threshold")).toBeInTheDocument();
  });

  it("keeps the label visible while the figure is still loading", () => {
    render(<StatCard label="Open right now" value={0} loading />);

    expect(screen.getByText("Open right now")).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });
});
