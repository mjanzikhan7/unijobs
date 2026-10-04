import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FitRing, bandFor } from "./FitRing";

describe("bandFor", () => {
  it.each([
    [0, "low"],
    [44, "low"],
    [45, "medium"],
    [69, "medium"],
    [70, "high"],
    [100, "high"],
  ])("puts %i in the %s band", (score, band) => {
    expect(bandFor(score)).toBe(band);
  });
});

describe("FitRing", () => {
  it("always shows the number, not just the arc", () => {
    render(<FitRing score={62} />);
    expect(screen.getByText("62")).toBeInTheDocument();
  });

  it("distinguishes no profile from a score of zero", () => {
    const { rerender } = render(<FitRing score={null} />);
    expect(screen.getByText(/no candidate profile yet/i)).toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();

    rerender(<FitRing score={0} />);
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.queryByText(/no candidate profile yet/i)).not.toBeInTheDocument();
  });

  it("announces the band in words, so colour is never the only signal", () => {
    render(<FitRing score={88} />);
    expect(screen.getByText("Strong match: 88 out of 100")).toBeInTheDocument();
  });

  it("clamps a score outside 0–100 rather than drawing an over-full ring", () => {
    const { rerender } = render(<FitRing score={140} />);
    expect(screen.getByText("100")).toBeInTheDocument();

    rerender(<FitRing score={-20} />);
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("rounds a fractional score to a whole number", () => {
    render(<FitRing score={71.6} />);
    expect(screen.getByText("72")).toBeInTheDocument();
  });
});
