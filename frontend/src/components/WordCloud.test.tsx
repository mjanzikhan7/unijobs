import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import type { ReactElement } from "react";

import { WordCloud } from "./WordCloud";

function renderCloud(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("WordCloud", () => {
  it("renders a link per term, carrying its count as accessible text", () => {
    renderCloud(
      <WordCloud
        terms={[{ term: "research software engineer", occurrences: 312, searchers: 88 }]}
        maxOccurrences={312}
      />,
    );

    const link = screen.getByRole("link", { name: /research software engineer/ });
    expect(link).toHaveTextContent("312 searches by 88 people");
    expect(link).toHaveAttribute("href", "/?q=research%20software%20engineer");
  });

  it("sizes the top term at the maximum and a much smaller one well below it", () => {
    renderCloud(
      <WordCloud
        terms={[
          { term: "big term", occurrences: 100, searchers: 40 },
          { term: "small term", occurrences: 1, searchers: 1 },
        ]}
        maxOccurrences={100}
      />,
    );

    const big = screen.getByRole("link", { name: /big term/ });
    const small = screen.getByRole("link", { name: /small term/ });
    expect(big.style.fontSize).toBe("2.6rem");
    const smallSize = Number.parseFloat(small.style.fontSize);
    expect(smallSize).toBeGreaterThanOrEqual(0.85);
    expect(smallSize).toBeLessThan(1.2);
  });

  it("does not divide by zero when every occurrence count is zero", () => {
    renderCloud(<WordCloud terms={[{ term: "quiet", occurrences: 0, searchers: 0 }]} maxOccurrences={0} />);
    expect(screen.getByRole("link", { name: /quiet/ }).style.fontSize).toBe("0.85rem");
  });

  it("shows the empty state when there are no terms", () => {
    renderCloud(<WordCloud terms={[]} maxOccurrences={0} />);
    expect(screen.getByRole("status")).toHaveTextContent("Nothing searched yet in this window.");
  });
});
