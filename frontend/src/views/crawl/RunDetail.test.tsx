import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { RunDetail } from "./RunDetail";
import { renderWithProviders, stubFetch } from "@/test-utils";

function detail(overrides: Record<string, unknown> = {}) {
  return {
    id: 12,
    trigger: "MANUAL",
    status: "CANCELLED",
    is_active: false,
    started_at: "2026-08-24T09:00:00Z",
    finished_at: "2026-08-24T09:05:00Z",
    duration_seconds: 300,
    institutions_total: 3,
    institutions_done: 1,
    jobs_new: 0,
    jobs_updated: 0,
    jobs_closed: 0,
    error_detail: "",
    institution_results: [],
    retriable_count: 0,
    ...overrides,
  };
}

function diff() {
  return { run: detail(), new: [], changed: [], disappeared: [] };
}

function renderDetail(runDetail = detail()) {
  stubFetch({
    "/diff/": diff(),
    "/logs/": [],
    "/crawl-runs/12/": runDetail,
  });
  return renderWithProviders(
    <Routes>
      <Route path="/admin/crawl/:id" element={<RunDetail />} />
    </Routes>,
    { route: "/admin/crawl/12" },
  );
}

describe("RunDetail — restart", () => {
  it("offers a full restart on a finished run", async () => {
    renderDetail();

    expect(await screen.findByRole("button", { name: "Restart" })).toBeInTheDocument();
  });

  it("does not offer to retry failures when everything came back OK", async () => {
    renderDetail(detail({ retriable_count: 0 }));
    await screen.findByRole("button", { name: "Restart" });

    expect(screen.queryByText(/Retry \d+ failure/)).not.toBeInTheDocument();
  });

  it("offers to retry failures, with the count, when there are some", async () => {
    renderDetail(detail({ retriable_count: 2 }));

    expect(await screen.findByRole("button", { name: "Retry 2 failures" })).toBeInTheDocument();
  });

  it("uses the singular for exactly one failure", async () => {
    renderDetail(detail({ retriable_count: 1 }));

    expect(await screen.findByRole("button", { name: "Retry 1 failure" })).toBeInTheDocument();
  });

  it("hides every restart control while the run is still running", async () => {
    renderDetail(detail({ status: "RUNNING", is_active: true, retriable_count: 2 }));
    await screen.findByRole("heading", { name: "Run #12" });

    expect(screen.queryByRole("button", { name: "Restart" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Retry \d+ failure/)).not.toBeInTheDocument();
  });

  it("still offers to restart while the run is paused", async () => {
    renderDetail(detail({ status: "PAUSED", is_active: true }));

    expect(await screen.findByRole("button", { name: "Restart" })).toBeInTheDocument();
  });
});
