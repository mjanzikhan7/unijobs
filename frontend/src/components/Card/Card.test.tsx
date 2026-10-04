import { createRef } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card } from "./Card";

describe("Card", () => {
  it("renders its children", () => {
    render(<Card>Northgate University</Card>);
    expect(screen.getByText("Northgate University")).toBeInTheDocument();
  });

  it("forwards a ref to the underlying element", () => {
    const ref = createRef<HTMLDivElement>();
    render(<Card ref={ref}>content</Card>);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });

  it("merges a caller className rather than replacing the base styles", () => {
    render(<Card className="max-w-md">content</Card>);
    const card = screen.getByText("content");
    expect(card.className).toContain("max-w-md");
    expect(card.className).toContain("border-border-subtle");
  });
});

describe("Card as", () => {
  it("defaults to a plain container with no role of its own", () => {
    const { container } = render(<Card>Body</Card>);
    expect(container.firstElementChild?.tagName).toBe("DIV");
  });

  it("renders as an article for a card that stands alone out of context", () => {
    render(<Card as="article">A vacancy</Card>);
    expect(screen.getByRole("article")).toHaveTextContent("A vacancy");
  });

  it("renders as a list item without losing the card styling", () => {
    const { container } = render(
      <ul>
        <Card as="li">A row</Card>
      </ul>,
    );

    const item = container.querySelector("li");
    expect(item).toBeInTheDocument();
    expect(item?.className).toContain("rounded-md");
  });
});
