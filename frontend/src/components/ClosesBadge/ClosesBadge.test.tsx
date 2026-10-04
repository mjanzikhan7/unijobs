import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ClosesBadge, urgencyOf } from "./ClosesBadge";

describe("urgencyOf", () => {
  const today = new Date("2026-09-20T09:00:00Z");

  it.each([
    [null, "none"],
    ["2026-09-10", "closed"],
    ["2026-09-20", "today"],
    ["2026-09-21", "urgent"],
    ["2026-09-23", "urgent"],
    ["2026-09-24", "later"],
  ])("reads %s as %s", (value, expected) => {
    expect(urgencyOf(value, today)).toBe(expected);
  });
});

describe("ClosesBadge", () => {
  beforeEach(() => {
    vi.setSystemTime(new Date("2026-09-20T09:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows a countdown rather than a bare date", () => {
    render(<ClosesBadge value="2026-09-25" />);

    expect(screen.getByText("Closes in 5 days")).toBeInTheDocument();
  });

  it("says so when there is no closing date, and does not mark it urgent", () => {
    render(<ClosesBadge value={null} />);

    expect(screen.getByText("No closing date")).toHaveAttribute("data-urgency", "none");
  });

  it("marks a closing date within 3 days as urgent", () => {
    render(<ClosesBadge value="2026-09-22" />);

    expect(screen.getByText("Closes in 2 days")).toHaveAttribute("data-urgency", "urgent");
  });

  it("gives a closing date of today its own, louder tone rather than the usual urgent one", () => {
    render(<ClosesBadge value="2026-09-20" />);

    const badge = screen.getByText("Closes today");
    expect(badge).toHaveAttribute("data-urgency", "today");
    expect(badge.className).toContain("text-body-sm");
    expect(badge.className).toContain("font-extrabold");
  });

  it("does not mark a closing date further out as urgent", () => {
    render(<ClosesBadge value="2026-09-30" />);

    expect(screen.getByText("Closes in 10 days")).toHaveAttribute("data-urgency", "later");
  });

  it("marks a date that has already passed as closed, not urgent", () => {
    render(<ClosesBadge value="2026-09-10" />);

    expect(screen.getByText("Closed")).toHaveAttribute("data-urgency", "closed");
  });

  it("carries the exact date as a tooltip", () => {
    render(<ClosesBadge value="2026-09-25" />);

    expect(screen.getByText("Closes in 5 days")).toHaveAttribute("title", "25 Sept 2026");
  });
});
