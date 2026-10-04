import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { JobCard } from "./JobCard";
import { makeJob, makeScreening, renderWithProviders } from "@/test-utils";

describe("JobCard", () => {
  it("always renders a sponsor badge", () => {
    renderWithProviders(<JobCard job={makeJob()} />);

    expect(screen.getByText(/Sponsor confirmed/)).toBeInTheDocument();
  });

  it("always renders a threshold badge", () => {
    renderWithProviders(<JobCard job={makeJob()} />);

    expect(screen.getByText(/Pay cut/)).toBeInTheDocument();
  });

  it("warns rather than staying silent when a job has no screening", () => {
    renderWithProviders(<JobCard job={makeJob({ screening: undefined })} />);

    expect(screen.getAllByText(/Not screened/)).toHaveLength(2);
  });

  it("keeps the advertised salary string beside the parsed range", () => {
    renderWithProviders(<JobCard job={makeJob()} />);

    expect(screen.getByText("£38,784 to £46,049 per annum")).toBeInTheDocument();
  });

  it("sets the salary in tabular numerals so columns align", () => {
    renderWithProviders(<JobCard job={makeJob()} />);

    expect(screen.getByText("£38,784 – £46,049").className).toContain("tabular-nums");
  });

  it("renders a ceiling-only salary as 'Up to', never as a starting figure", () => {
    const job = makeJob({
      screening: makeScreening({ salary_min: null, salary_max: "86500.00" }),
    });

    renderWithProviders(<JobCard job={job} />);

    expect(screen.getByText("Up to £86,500")).toBeInTheDocument();
  });

  it("shows the classified discipline beneath the institution", () => {
    renderWithProviders(<JobCard job={makeJob({ discipline: "PSYCHOLOGY" })} />);

    expect(screen.getByText("Psychology")).toBeInTheDocument();
  });

  it("says nothing when the classifier found nothing confident to say", () => {
    renderWithProviders(<JobCard job={makeJob({ discipline: "OTHER" })} />);

    expect(screen.queryByText("Other")).not.toBeInTheDocument();
  });

  it("flags a job that is no longer listed", () => {
    renderWithProviders(<JobCard job={makeJob({ status: "DISAPPEARED" })} />);

    expect(screen.getByText(/No longer listed/)).toBeInTheDocument();
  });

  it("links to the job's own page rather than to the employer", () => {
    renderWithProviders(<JobCard job={makeJob()} />);

    expect(screen.getByRole("link", { name: /Research Software Engineer/ })).toHaveAttribute(
      "href",
      "/jobs/1",
    );
  });

  it("offers to save a job", async () => {
    const onSave = vi.fn();
    renderWithProviders(<JobCard job={makeJob()} onSave={onSave} />);

    await userEvent.click(screen.getByRole("button", { name: /^Save/ }));

    expect(onSave).toHaveBeenCalledOnce();
  });

  it("reports its saved state to assistive technology", () => {
    renderWithProviders(<JobCard job={makeJob({ is_saved: true })} onSave={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Unsave/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("shows a countdown rather than a bare closing date", () => {
    vi.setSystemTime(new Date("2026-09-25T09:00:00Z"));

    renderWithProviders(<JobCard job={makeJob()} />);

    expect(screen.getByText("Closes in 5 days")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("says so when there is no closing date", () => {
    renderWithProviders(<JobCard job={makeJob({ closing_date: null })} />);

    expect(screen.getByText("No closing date")).toBeInTheDocument();
  });

  it("marks the focused card for keyboard navigation", () => {
    renderWithProviders(<JobCard job={makeJob()} isFocused />);

    expect(screen.getByTestId("job-card")).toHaveAttribute("aria-current", "true");
  });
});
