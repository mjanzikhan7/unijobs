import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { JobList } from "./JobList";
import { urlOf } from "@/models/api/client";
import { makeJob, paginate, renderWithProviders, stubFetch } from "@/test-utils";

const FACETS = {
  total: 2,
  facets: {
    sponsor_verdict: [
      { value: "CONFIRMED", count: 2 },
      { value: "NOT_FOUND", count: 0 },
    ],
    nation: [{ value: "ENGLAND", count: 2 }],
    discipline: [{ value: "PSYCHOLOGY", count: 2 }],
  },
};

const JOBS = [
  makeJob({ id: 1, title: "Research Software Engineer" }),
  makeJob({ id: 2, title: "Lecturer in Data Science", source_url: "https://jobs.test.ac.uk/2" }),
];

describe("JobList", () => {
  beforeEach(() => {
    stubFetch({
      "/jobs/facets/": FACETS,
      "/institutions/": paginate([]),
      "/jobs/": paginate(JOBS),
    });
  });

  it("lists the vacancies it was given", async () => {
    renderWithProviders(<JobList />);

    expect(await screen.findByText("Research Software Engineer")).toBeInTheDocument();
  });

  it("reports how many there are", async () => {
    renderWithProviders(<JobList />);

    expect(await screen.findByText("2 vacancies")).toBeInTheDocument();
  });

  it("offers the facets the server returned", async () => {
    renderWithProviders(<JobList />);

    expect(await screen.findByRole("group", { name: "Sponsorship" })).toBeInTheDocument();
  });

  it("disables a facet that would return nothing", async () => {
    renderWithProviders(<JobList />);

    expect(await screen.findByRole("checkbox", { name: /Not found/i })).toBeDisabled();
  });

  it("offers the discipline browse grid, open by default", async () => {
    renderWithProviders(<JobList />);

    const browse = await screen.findByRole("group", { name: "Browse by discipline" });
    expect(browse).toHaveAttribute("open");
  });

  it("collapses the browse grid once a discipline filter is already on", async () => {
    renderWithProviders(<JobList />, { route: "/?discipline=PSYCHOLOGY" });
    await screen.findByText("Research Software Engineer");

    expect(screen.getByRole("group", { name: "Browse by discipline" })).not.toHaveAttribute("open");
  });

  it("offers no clear button until a search has actually been submitted", async () => {
    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    expect(screen.queryByRole("button", { name: "Clear search" })).not.toBeInTheDocument();
  });

  it("clears a submitted search term and empties the search box", async () => {
    renderWithProviders(<JobList />, { route: "/?q=engineer" });
    await screen.findByText("Research Software Engineer");

    await userEvent.click(await screen.findByRole("button", { name: "Clear search" }));

    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(screen.queryByRole("button", { name: "Clear search" })).not.toBeInTheDocument();
  });

  it("focuses the search box on /", async () => {
    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    await userEvent.keyboard("/");

    expect(screen.getByRole("searchbox")).toHaveFocus();
  });

  it("shows a loading indicator while a search is in flight, without hiding the old results", async () => {
    let releaseSearchResponse: (() => void) | undefined;
    const searchHeld = new Promise<void>((resolve) => {
      releaseSearchResponse = resolve;
    });
    vi.spyOn(globalThis, "fetch").mockClear().mockImplementation(async (input: RequestInfo | URL) => {
      const url = urlOf(input);
      const respond = (body: unknown) =>
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      if (url.includes("/jobs/facets/")) return respond(FACETS);
      if (url.includes("/institutions/")) return respond(paginate([]));
      if (url.includes("/jobs/") && url.includes("q=engineer")) {
        await searchHeld;
        return respond(paginate([JOBS[0]!]));
      }
      if (url.includes("/jobs/")) return respond(paginate(JOBS));
      throw new Error(`Unstubbed request to ${url}`);
    });

    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    await userEvent.type(screen.getByRole("searchbox"), "engineer{Enter}");

    expect(await screen.findByText("Searching…")).toBeInTheDocument();
    expect(screen.getByText("Lecturer in Data Science")).toBeInTheDocument();

    releaseSearchResponse?.();

    await waitFor(() => expect(screen.queryByText("Searching…")).not.toBeInTheDocument());
  });

  it("moves focus down the list on j", async () => {
    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    await userEvent.keyboard("j");

    await waitFor(() =>
      expect(screen.getAllByTestId("job-card")[0]).toHaveAttribute("aria-current", "true"),
    );
  });

  it("moves focus back up the list on k", async () => {
    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    await userEvent.keyboard("jj");
    await userEvent.keyboard("k");

    await waitFor(() =>
      expect(screen.getAllByTestId("job-card")[0]).toHaveAttribute("aria-current", "true"),
    );
  });

  it("types into the search box rather than navigating when it has focus", async () => {
    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");
    const search = screen.getByRole("searchbox");

    await userEvent.click(search);
    await userEvent.type(search, "jk");

    expect(search).toHaveValue("jk");
  });

  it("leaves the list unfocused while the search box is being typed into", async () => {
    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    await userEvent.type(screen.getByRole("searchbox"), "jjj");

    expect(screen.getAllByTestId("job-card")[0]).not.toHaveAttribute("aria-current");
  });

  it("names the most restrictive filter when nothing matches", async () => {
    stubFetch({
      "/jobs/facets/": { total: 0, facets: {} },
      "/institutions/": paginate([]),
      "/jobs/": paginate([]),
    });

    renderWithProviders(<JobList />, { route: "/?min_fitness=95&nation=WALES" });

    const heading = await screen.findByRole("heading", { name: /No jobs match these filters/ });

    expect(heading.parentElement).toHaveTextContent(/Minimum fitness/);
  });

  it("offers to clear that filter", async () => {
    stubFetch({
      "/jobs/facets/": { total: 0, facets: {} },
      "/institutions/": paginate([]),
      "/jobs/": paginate([]),
    });

    renderWithProviders(<JobList />, { route: "/?min_fitness=95" });

    expect(await screen.findByRole("button", { name: /Clear minimum fitness/i })).toBeInTheDocument();
  });

  it("restores the exact view from a pasted URL", async () => {
    renderWithProviders(<JobList />, { route: "/?q=engineer&order=-salary" });

    await screen.findByText("Research Software Engineer");

    expect(screen.getByRole("combobox", { name: /Sort by/i })).toHaveValue("-salary");
  });

  it("carries the active filters into the request", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockClear();
    renderWithProviders(<JobList />, { route: "/?nation=SCOTLAND" });
    await screen.findByText("Research Software Engineer");

    const urls = spy.mock.calls.map((call) => urlOf(call[0]));

    expect(urls.some((url) => url.includes("/jobs/?nation=SCOTLAND"))).toBe(true);
  });

  it("asks for facets under the same filters as the list", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockClear();
    renderWithProviders(<JobList />, { route: "/?nation=SCOTLAND" });
    await screen.findByText("Research Software Engineer");

    const urls = spy.mock.calls.map((call) => urlOf(call[0]));

    expect(urls.some((url) => url.includes("/jobs/facets/?nation=SCOTLAND"))).toBe(true);
  });

  it("rolls an optimistic save back when the server refuses", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockImplementation((input: RequestInfo | URL) => {
      const url = urlOf(input);
      if (url.includes("/saved-jobs/")) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: "Already saved.", code: "invalid" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      const body = url.includes("/facets/")
        ? FACETS
        : url.includes("/institutions/")
          ? paginate([])
          : paginate(JOBS);
      return Promise.resolve(
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    await userEvent.click(screen.getAllByRole("button", { name: /^Save Research/ })[0] as HTMLElement);

    expect(await screen.findByText(/Could not save that job/)).toBeInTheDocument();
  });

  it("shows the shortcut help", async () => {
    renderWithProviders(<JobList />);
    await screen.findByText("Research Software Engineer");

    expect(screen.getByText("Keyboard shortcuts")).toBeInTheDocument();
  });
});
