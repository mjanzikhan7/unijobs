import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Notice } from "./Notice";

describe("Notice", () => {
  it("renders its message", () => {
    render(<Notice tone="info">Editing here creates a new version.</Notice>);
    expect(screen.getByText("Editing here creates a new version.")).toBeInTheDocument();
  });

  it("uses role=alert for a danger notice, so it interrupts a screen reader", () => {
    render(<Notice tone="danger">This institution still has 64 jobs.</Notice>);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("uses role=status, not alert, for info and warning — they should not interrupt", () => {
    render(<Notice tone="warning">The next crawl would overwrite an edit.</Notice>);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders the quote as a blockquote when given one", () => {
    render(
      <Notice tone="danger" quote="We do not sponsor this role.">
        This advert rules sponsorship out in terms.
      </Notice>,
    );
    expect(screen.getByText("We do not sponsor this role.").tagName).toBe("BLOCKQUOTE");
  });

  it("renders no blockquote when no quote is given", () => {
    const { container } = render(<Notice tone="info">Plain notice.</Notice>);
    expect(container.querySelector("blockquote")).not.toBeInTheDocument();
  });
});
