import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CrawlLogPanel } from "./CrawlLogPanel";
import { renderWithProviders, stubFetch } from "@/test-utils";

function entry(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    level: "INFO",
    message: "started",
    extra: {},
    institution: null,
    institution_name: null,
    created_at: "2026-08-24T13:00:00Z",
    ...overrides,
  };
}

describe("CrawlLogPanel", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  it("says plainly that no run is selected, rather than an empty panel", () => {
    renderWithProviders(<CrawlLogPanel runId={null} />);

    expect(screen.getByText("No run selected.")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("says nothing has been logged yet when a run has an empty log", async () => {
    stubFetch({ "/logs/": [] });
    renderWithProviders(<CrawlLogPanel runId={7} />);

    expect(await screen.findByText("Nothing logged yet.")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("renders a line's message", async () => {
    stubFetch({ "/logs/": [entry({ message: "started crawl run 7 over 3 institutions" })] });
    renderWithProviders(<CrawlLogPanel runId={7} />);

    expect(await screen.findByText(/started crawl run 7 over 3 institutions/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("shows the level badge", async () => {
    stubFetch({ "/logs/": [entry({ level: "WARNING", message: "still attracts sponsorship?" })] });
    renderWithProviders(<CrawlLogPanel runId={7} />);

    expect(await screen.findByText("WARNING")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("attributes a line to its institution when it has one", async () => {
    stubFetch({
      "/logs/": [
        entry({ institution: 4, institution_name: "University of Bath", message: "crawled" }),
      ],
    });
    renderWithProviders(<CrawlLogPanel runId={7} />);

    expect(await screen.findByText(/University of Bath/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("renders a run-level line with no institution attribution at all", async () => {
    stubFetch({ "/logs/": [entry({ message: "Run 7 paused." })] });
    renderWithProviders(<CrawlLogPanel runId={7} />);

    const line = await screen.findByText(/Run 7 paused\./);
    expect(line.closest("li")?.querySelector("strong")).toBeNull();
    vi.useRealTimers();
  });
});
