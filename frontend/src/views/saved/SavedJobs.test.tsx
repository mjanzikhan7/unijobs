import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SavedJobs } from "./SavedJobs";
import { makeJobDetail, paginate, renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";
import type { SavedJob } from "@/models/api/types";

function makeSaved(overrides: Partial<SavedJob> = {}): SavedJob {
  return {
    id: 1,
    job: 1,
    job_detail: makeJobDetail(),
    tags: [],
    created_at: "2026-08-20T09:00:00Z",
    ...overrides,
  } as SavedJob;
}

describe("SavedJobs", () => {
  it("shows a loading state, then the list", async () => {
    stubFetch({ "/saved-jobs/": paginate([makeSaved()]) });
    renderWithProviders(<SavedJobs />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading saved jobs");
    expect(await screen.findByText("Research Software Engineer")).toBeInTheDocument();
  });

  it("shows the empty state with the keyboard hint when nothing is saved", async () => {
    stubFetch({ "/saved-jobs/": paginate([]) });
    renderWithProviders(<SavedJobs />);

    expect(await screen.findByText(/Nothing saved yet/)).toBeInTheDocument();
  });

  it("flags a saved job whose vacancy disappeared, rather than dropping the row", async () => {
    stubFetch({
      "/saved-jobs/": paginate([
        makeSaved({ job_detail: makeJobDetail({ status: "DISAPPEARED" }) }),
      ]),
    });
    renderWithProviders(<SavedJobs />);

    expect(await screen.findAllByText("No longer listed")).toHaveLength(2);
    expect(screen.getByText("Research Software Engineer")).toBeInTheDocument();
  });

  it("shows the tags a saved job carries", async () => {
    stubFetch({ "/saved-jobs/": paginate([makeSaved({ tags: ["stretch"] })]) });
    renderWithProviders(<SavedJobs />);

    expect(await screen.findByText("stretch")).toBeInTheDocument();
  });

  it("deletes the saved row by its own id when Remove is pressed", async () => {
    stubFetch({ "/saved-jobs/": paginate([makeSaved({ id: 7 })]) });
    renderWithProviders(<SavedJobs />);

    const removeButton = await screen.findByRole("button", { name: "Remove" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(new Response(null, { status: 204 }));
    await userEvent.click(removeButton);

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/saved-jobs/7/");
    expect((options as RequestInit).method).toBe("DELETE");
  });

  it("shows an error with a retry option when the list fails to load", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Server error." }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );
    renderWithProviders(<SavedJobs />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
