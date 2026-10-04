import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CandidateInsights } from "./CandidateInsights";
import { renderWithProviders, stubFetch } from "@/test-utils";

function overview(overrides: Record<string, number> = {}) {
  return {
    active_candidates: 214,
    searches: 4187,
    empty_search_rate: 0.12,
    job_views: 9612,
    saves: 1188,
    applications: 402,
    view_to_save_rate: 0.18,
    save_to_apply_rate: 0.41,
    ...overrides,
  };
}

function payload(overrides: Record<string, unknown> = {}) {
  return {
    days: 30,
    limit: 20,
    overview: overview(),
    by_day: [{ day: "2026-09-01", SEARCH: 120 }],
    top_searches: [
      { query: "research software engineer", searches: 312, searchers: 88, found_nothing: 12 },
    ],
    by_nation: [{ value: "England", views: 100, saves: 10, applications: 2 }],
    by_category: [],
    institutions: [
      { slug: "northgate", name: "Northgate University", views: 1412, saves: 188, applications: 71 },
    ],
    ...overrides,
  };
}

const cloud = { days: 30, max_occurrences: 312, terms: [{ term: "devops", occurrences: 40, searchers: 20 }] };

describe("CandidateInsights", () => {
  it("does not flag 'found nothing' as a warning below the 30% threshold", async () => {
    stubFetch({
      "/insights/candidates/": payload({ overview: overview({ empty_search_rate: 0.12 }) }),
      "/insights/search-cloud/": cloud,
    });
    renderWithProviders(<CandidateInsights />);

    const value = await screen.findByText("12%");
    expect(value.closest("[data-tone]")).toHaveAttribute("data-tone", "default");
  });

  it("flags 'found nothing' as a warning once it crosses the 30% threshold", async () => {
    stubFetch({
      "/insights/candidates/": payload({ overview: overview({ empty_search_rate: 0.335 }) }),
      "/insights/search-cloud/": cloud,
    });
    renderWithProviders(<CandidateInsights />);

    const value = await screen.findByText("34%");
    expect(value.closest("[data-tone]")).toHaveAttribute("data-tone", "warn");
  });

  it("renders every aggregate stat", async () => {
    stubFetch({ "/insights/candidates/": payload(), "/insights/search-cloud/": cloud });
    renderWithProviders(<CandidateInsights />);

    expect(await screen.findByText("214")).toBeInTheDocument();
    expect(screen.getByText("4187")).toBeInTheDocument();
    expect(screen.getByText("9612")).toBeInTheDocument();
    expect(screen.getByText("1188")).toBeInTheDocument();
    expect(screen.getByText("402")).toBeInTheDocument();
  });

  it("shows the most-run searches and the institutions candidates engage with", async () => {
    stubFetch({ "/insights/candidates/": payload(), "/insights/search-cloud/": cloud });
    renderWithProviders(<CandidateInsights />);

    expect(await screen.findByText("research software engineer")).toBeInTheDocument();
    expect(screen.getByText("Northgate University")).toBeInTheDocument();
  });

  it("renders the search-term cloud from its own endpoint", async () => {
    stubFetch({ "/insights/candidates/": payload(), "/insights/search-cloud/": cloud });
    renderWithProviders(<CandidateInsights />);

    expect(await screen.findByText("devops")).toBeInTheDocument();
  });

  it("omits a dimension table entirely when that dimension has no rows", async () => {
    stubFetch({
      "/insights/candidates/": payload({ by_category: [] }),
      "/insights/search-cloud/": cloud,
    });
    renderWithProviders(<CandidateInsights />);

    await screen.findByText("Northgate University");
    expect(screen.queryByText("Category")).not.toBeInTheDocument();
  });

  it("switches the time window on click", async () => {
    stubFetch({ "/insights/candidates/": payload(), "/insights/search-cloud/": cloud });
    renderWithProviders(<CandidateInsights />);

    await screen.findByText("Northgate University");
    await userEvent.click(screen.getByRole("radio", { name: "7d" }));

    expect(await screen.findByRole("radio", { name: "7d" })).toBeChecked();
  });
});
