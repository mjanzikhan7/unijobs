import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { JobAdmin } from "./JobAdmin";
import { makeJob, renderWithProviders } from "@/test-utils";
import type * as UseJobsModule from "@/viewmodels/useJobs";
import type { Role } from "@/viewmodels/auth";

let myRole: Role = "ADMIN";
let myAssigned: string[] = [];
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ role: myRole, assignedInstitutions: myAssigned }),
}));

const requested: string[] = [];

vi.mock("@/viewmodels/useJobs", async (importOriginal) => {
  const actual = await importOriginal<typeof UseJobsModule>();
  return {
    ...actual,
    useJobs: (query: string) => {
      requested.push(query);
      const params = new URLSearchParams(query);
      const page = Number(params.get("page") ?? 1);
      const size = Number(params.get("page_size") ?? 25);
      const count = 2106;
      return {
        data: {
          count,
          page,
          total_pages: Math.ceil(count / size),
          next: page * size < count ? "next" : null,
          previous: page > 1 ? "prev" : null,
          results: Array.from({ length: size }, (_, index) =>
            makeJob({
              id: (page - 1) * size + index + 1,
              title: `Job ${index}`,
              source: "MANUAL",
            }),
          ),
        },
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      };
    },
    useWithdrawJob: () => ({ mutate: vi.fn(), error: null }),
    useReinstateJob: () => ({ mutate: vi.fn(), error: null }),
    useDeleteJob: () => ({ mutate: vi.fn(), error: null }),
  };
});

describe("JobAdmin", () => {
  beforeEach(() => {
    requested.length = 0;
    myRole = "ADMIN";
    myAssigned = [];
  });

  it("says how many it is showing out of how many there are", async () => {
    renderWithProviders(<JobAdmin />);

    expect(await screen.findByText(/Showing 50 of 2106 jobs/)).toBeInTheDocument();
  });

  it("offers pagination when there is more than one page", async () => {
    renderWithProviders(<JobAdmin />);

    expect(await screen.findByRole("button", { name: /next/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
  });

  it("asks the server for the next page", async () => {
    renderWithProviders(<JobAdmin />);

    await userEvent.click(await screen.findByRole("button", { name: /next/i }));

    await waitFor(() => expect(requested.at(-1)).toContain("page=2"));
  });

  it("returns to page one when a filter changes", async () => {
    renderWithProviders(<JobAdmin />);
    await userEvent.click(await screen.findByRole("button", { name: /next/i }));
    await waitFor(() => expect(requested.at(-1)).toContain("page=2"));

    await userEvent.selectOptions(screen.getByLabelText(/origin/i), "MANUAL");

    await waitFor(() => expect(requested.at(-1)).toContain("page=1"));
    expect(requested.at(-1)).toContain("source=MANUAL");
  });

  it("lets the page size be changed", async () => {
    renderWithProviders(<JobAdmin />);

    await userEvent.selectOptions(await screen.findByLabelText(/per page/i), "200");

    await waitFor(() => expect(requested.at(-1)).toContain("page_size=200"));
  });

  it("offers a way to add a job by hand", async () => {
    renderWithProviders(<JobAdmin />);

    expect(await screen.findByRole("button", { name: "Add job" })).toBeInTheDocument();
  });

  it("links each job added by hand to its own edit screen", async () => {
    renderWithProviders(<JobAdmin />);

    const edits = await screen.findAllByRole("link", { name: "Edit" });
    expect(edits[0]).toHaveAttribute("href", "/admin/jobs/1/edit");
  });

  it("scopes a recruiter's table to their own assigned institutions", async () => {
    myRole = "RECRUITER";
    myAssigned = ["northgate", "southbridge"];
    renderWithProviders(<JobAdmin />);

    await waitFor(() => {
      expect(requested.at(-1)).toContain("institution=northgate");
      expect(requested.at(-1)).toContain("institution=southbridge");
    });
  });
});
