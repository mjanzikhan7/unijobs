import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CrawlRunningPip } from "./AdminNavBadges";

vi.mock("@/viewmodels/useActiveRun", () => ({
  useActiveRun: () => ({ data: { run: { id: 1 } } }),
}));

describe("CrawlRunningPip", () => {
  it("spins the radar icon while a run is active", () => {
    render(<CrawlRunningPip />);

    const pip = screen.getByLabelText("A crawl is running");
    const icon = pip.querySelector("svg");
    expect(icon?.getAttribute("class")).toContain("animate-spin");
  });
});
