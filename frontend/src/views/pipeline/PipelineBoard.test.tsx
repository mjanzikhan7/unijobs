import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PipelineBoard } from "./PipelineBoard";
import { renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";
import type { Application } from "@/models/api/types";

function makeApplication(overrides: Partial<Application> = {}): Application {
  return {
    id: 1,
    status: "APPLIED",
    ghosted_flagged: false,
    next_action: null,
    next_action_due: null,
    applied_at: "2026-08-14T09:00:00Z",
    job_detail: {
      id: 1,
      title: "Senior Research Software Engineer",
      institution_name: "Northgate University",
    },
    ...overrides,
  } as unknown as Application;
}

function board(columns: { status: string; label: string; applications: Application[] }[]) {
  return { columns };
}

describe("PipelineBoard", () => {
  it("shows a loading state, then the columns", async () => {
    stubFetch({
      "/applications/board/": board([
        { status: "APPLIED", label: "Applied", applications: [makeApplication()] },
      ]),
    });
    renderWithProviders(<PipelineBoard />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading pipeline");
    expect(await screen.findByText("Senior Research Software Engineer")).toBeInTheDocument();
  });

  it("flags a ghosted application rather than moving it out of Applied", async () => {
    stubFetch({
      "/applications/board/": board([
        {
          status: "APPLIED",
          label: "Applied",
          applications: [makeApplication({ ghosted_flagged: true })],
        },
      ]),
    });
    renderWithProviders(<PipelineBoard />);

    expect(await screen.findByText("Possibly ghosted")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /Pipeline columns/ })).toHaveTextContent("Applied");
  });

  it("posts the new status when a card is moved via the keyboard-reachable select", async () => {
    stubFetch({
      "/applications/board/": board([
        { status: "APPLIED", label: "Applied", applications: [makeApplication()] },
        { status: "INTERVIEW", label: "Interview", applications: [] },
      ]),
    });
    renderWithProviders(<PipelineBoard />);

    const select = await screen.findByLabelText(/Move Senior Research Software Engineer/);
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(new Response(JSON.stringify(makeApplication()), { status: 200 }));
    await userEvent.selectOptions(select, "INTERVIEW");

    expect(fetchSpy).toHaveBeenCalled();
    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/applications/1/move/");
    const requestBody = JSON.parse((options as RequestInit).body as string) as { status: string };
    expect(requestBody.status).toBe("INTERVIEW");
  });

  it("shows the next action and its due date when the application has one", async () => {
    stubFetch({
      "/applications/board/": board([
        {
          status: "READY",
          label: "Ready",
          applications: [
            makeApplication({
              status: "READY",
              next_action: "Rewrite the personal statement",
              next_action_due: "2026-09-08",
            }),
          ],
        },
      ]),
    });
    renderWithProviders(<PipelineBoard />);

    expect(await screen.findByText(/Rewrite the personal statement/)).toBeInTheDocument();
  });

  it("shows an empty column with a zero count rather than hiding it", async () => {
    stubFetch({
      "/applications/board/": board([{ status: "OFFER", label: "Offer", applications: [] }]),
    });
    renderWithProviders(<PipelineBoard />);

    expect(await screen.findByText("Offer")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Offer, 0 applications" })).toBeInTheDocument();
  });

  it("offers every column in the mobile switcher, with its count", async () => {
    stubFetch({
      "/applications/board/": board([
        { status: "FOUND", label: "Found", applications: [] },
        { status: "APPLIED", label: "Applied", applications: [makeApplication()] },
        { status: "OFFER", label: "Offer", applications: [] },
      ]),
    });
    renderWithProviders(<PipelineBoard />);

    const group = await screen.findByRole("radiogroup", { name: "Show column" });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Applied 1" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Offer 0" })).toBeInTheDocument();
  });

  it("switches which column is shown on a narrow screen", async () => {
    stubFetch({
      "/applications/board/": board([
        { status: "FOUND", label: "Found", applications: [] },
        { status: "OFFER", label: "Offer", applications: [] },
      ]),
    });
    renderWithProviders(<PipelineBoard />);

    expect(await screen.findByRole("radio", { name: "Found 0" })).toBeChecked();

    await userEvent.click(screen.getByRole("radio", { name: "Offer 0" }));
    expect(screen.getByRole("radio", { name: "Offer 0" })).toBeChecked();
  });

  it("says an empty column is empty rather than leaving a blank space", async () => {
    stubFetch({
      "/applications/board/": board([{ status: "OFFER", label: "Offer", applications: [] }]),
    });
    renderWithProviders(<PipelineBoard />);

    expect(await screen.findByText("Nothing here yet")).toBeInTheDocument();
  });
});
