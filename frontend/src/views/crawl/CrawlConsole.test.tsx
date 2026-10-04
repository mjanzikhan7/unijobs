import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { CrawlConsole } from "./CrawlConsole";
import { urlOf } from "@/models/api/client";
import { paginate, renderWithProviders, stubFetch } from "@/test-utils";

const INSTITUTIONS = paginate([
  {
    id: 1,
    slug: "university-of-bath",
    name: "University of Bath",
    nation: "ENGLAND",
    city: "Bath",
    institution_type: "RUSSELL_GROUP",
    ranking: null,
    website: "https://bath.ac.uk",
    careers_url: "https://bath.ac.uk/jobs",
    platform: "STONEFISH",
    adapter_override: "",
    effective_platform: "STONEFISH",
    crawl_enabled: true,
    notes: "",
    sponsor_match: null,
    last_crawl: null,
    open_jobs: 0,
  },
]);

function runAt(status: string) {
  return {
    run: {
      id: 12,
      status,
      trigger: "MANUAL",
      is_active: status === "RUNNING" || status === "PAUSED",
      started_at: "2026-08-24T09:00:00Z",
      finished_at: null,
      duration_seconds: null,
      institutions_total: 167,
      institutions_done: 40,
      jobs_new: 3,
      jobs_updated: 1,
      jobs_closed: 0,
      error_detail: "",
    },
  };
}

function renderConsole(activeRun: unknown) {
  stubFetch({
    "/institutions/": INSTITUTIONS,
    "/crawl-runs/active/": activeRun,
    "/crawl-runs/12/logs/": [],
    "/crawl-runs/": paginate([]),
  });
  return renderWithProviders(<CrawlConsole />);
}

describe("CrawlConsole — run controls", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows Pause and Stop, but not Resume, while a run is RUNNING", async () => {
    renderConsole(runAt("RUNNING"));

    expect(await screen.findByRole("button", { name: "Pause" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume" })).not.toBeInTheDocument();
  });

  it("shows Resume and Stop, but not Pause, while a run is PAUSED", async () => {
    renderConsole(runAt("PAUSED"));

    expect(await screen.findByRole("button", { name: "Resume" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
  });

  it("shows none of the run controls when nothing is active", async () => {
    renderConsole({ run: null });
    await screen.findByText("University of Bath");

    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stop" })).not.toBeInTheDocument();
  });

  it("re-enables Run crawl once the active run clears", async () => {
    renderConsole({ run: null });
    await screen.findByText("University of Bath");

    expect(screen.getByRole("button", { name: "Run crawl" })).toBeEnabled();
  });

  it("links the active run to its page under /admin/crawl", async () => {
    renderConsole(runAt("RUNNING"));

    expect(await screen.findByRole("link", { name: "#12" })).toHaveAttribute(
      "href",
      "/admin/crawl/12",
    );
  });

  it("disables Run crawl while a run is active", async () => {
    renderConsole(runAt("RUNNING"));

    expect(await screen.findByRole("button", { name: "Crawl in progress" })).toBeDisabled();
  });

  it("pausing calls the run's pause action", async () => {
    stubFetch({
      "/institutions/": INSTITUTIONS,
      "/crawl-runs/active/": runAt("RUNNING"),
      "/crawl-runs/12/logs/": [],
      "/crawl-runs/": paginate([]),
    });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockImplementation((input) => {
      const url = urlOf(input);
      if (url.includes("/pause/")) {
        return Promise.resolve(
          new Response(JSON.stringify(runAt("PAUSED").run), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.includes("/institutions/")) {
        return Promise.resolve(
          new Response(JSON.stringify(INSTITUTIONS), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.includes("/logs/")) {
        return Promise.resolve(
          new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }),
        );
      }
      if (url.includes("/crawl-runs/active/")) {
        return Promise.resolve(
          new Response(JSON.stringify(runAt("RUNNING")), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify(paginate([])), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });
    renderWithProviders(<CrawlConsole />);

    const pause = await screen.findByRole("button", { name: "Pause" });
    await userEvent.click(pause);

    await waitFor(() =>
      expect(fetchSpy.mock.calls.some((call) => urlOf(call[0]).includes("/crawl-runs/12/pause/"))).toBe(
        true,
      ),
    );
  });
});

const RANKED_OK = {
  id: 1,
  slug: "well-ranked-fine",
  name: "Well-Ranked Fine University",
  nation: "ENGLAND",
  city: "Bath",
  institution_type: "RUSSELL_GROUP",
  ranking: 5,
  website: "https://example.ac.uk",
  careers_url: "https://example.ac.uk/jobs",
  platform: "STONEFISH",
  adapter_override: "",
  effective_platform: "STONEFISH",
  crawl_enabled: true,
  notes: "",
  sponsor_match: null,
  last_crawl: {
    run_id: 1,
    outcome: "OK",
    adapter: "STONEFISH",
    strategy: "HTTP",
    vacancies_found: 10,
    previous_vacancies_found: 10,
    dropped_to_zero: false,
    fallback_fired: false,
    error_class: "",
    error_detail: "",
    started_at: "2026-08-24T09:00:00Z",
    duration_ms: 100,
  },
  open_jobs: 10,
};

const UNRANKED_BROKEN = {
  ...RANKED_OK,
  id: 2,
  slug: "unranked-broken",
  name: "Unranked Broken College",
  ranking: null,
  last_crawl: {
    ...RANKED_OK.last_crawl,
    run_id: 2,
    outcome: "OK",
    vacancies_found: 0,
    previous_vacancies_found: 40,
    dropped_to_zero: true,
  },
  open_jobs: 0,
};

describe("CrawlConsole — sort order", () => {
  function renderSortableConsole() {
    stubFetch({
      "/institutions/": paginate([RANKED_OK, UNRANKED_BROKEN]),
      "/crawl-runs/active/": { run: null },
      "/crawl-runs/": paginate([]),
    });
    return renderWithProviders(<CrawlConsole />);
  }

  function rowNames() {
    return screen.getAllByRole("row").slice(1).map((row) => row.textContent ?? "");
  }

  it("defaults to ranking order, with the unranked institution last", async () => {
    renderSortableConsole();
    await screen.findByText("Well-Ranked Fine University");

    const [first, second] = rowNames();
    expect(first).toContain("Well-Ranked Fine University");
    expect(second).toContain("Unranked Broken College");
  });

  it("re-sorts by attention required when that option is chosen", async () => {
    renderSortableConsole();
    await screen.findByText("Well-Ranked Fine University");

    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "attention");

    const [first, second] = rowNames();
    expect(first).toContain("Unranked Broken College");
    expect(second).toContain("Well-Ranked Fine University");
  });
});
