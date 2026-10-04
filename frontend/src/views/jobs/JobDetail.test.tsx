import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { JobDetail } from "./JobDetail";
import { urlOf } from "@/models/api/client";
import { makeJobDetail, makeScreening, renderWithProviders, stubFetch } from "@/test-utils";

const DETAIL = makeJobDetail();

function renderDetail(detail = DETAIL, extraRoutes: Record<string, unknown> = {}) {
  stubFetch({ ...extraRoutes, "/jobs/": detail });
  return renderWithProviders(
    <Routes>
      <Route path="/jobs/:id" element={<JobDetail />} />
    </Routes>,
    { route: "/jobs/1" },
  );
}

const APPLICATION_RESPONSE = { id: 1, job: DETAIL.id, status: "APPLIED" };

describe("JobDetail", () => {
  beforeEach(() => {
    stubFetch({ "/jobs/": DETAIL });
  });

  it("renders the vacancy", async () => {
    renderDetail();

    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(
      "Research Software Engineer",
    );
  });

  it("points the apply link at the employer's own posting", async () => {
    renderDetail();

    const link = await screen.findByRole("link", { name: /Apply on the employer/ });

    expect(link).toHaveAttribute("href", DETAIL.apply_url);
  });

  it("opens the apply link in a new tab", async () => {
    renderDetail();

    const link = await screen.findByRole("link", { name: /Apply on the employer/ });

    expect(link).toHaveAttribute("target", "_blank");
  });

  it("denies the opened page a handle on this one", async () => {
    renderDetail();

    const link = await screen.findByRole("link", { name: /Apply on the employer/ });

    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("offers applying as a link, never as a form submission", async () => {
    renderDetail();
    await screen.findByRole("link", { name: /Apply on the employer/ });

    expect(document.querySelector("form")).toBeNull();
  });

  it("offers a way back to the results", async () => {
    renderDetail();

    expect(await screen.findByRole("button", { name: /Back to results/ })).toBeInTheDocument();
  });

  it("links the institution name to its own page", async () => {
    renderDetail();

    const link = await screen.findByRole("link", { name: DETAIL.institution_name });
    expect(link).toHaveAttribute("href", `/institutions/${DETAIL.institution_slug}`);
  });

  it("shows the platform's own category as a tag when it has one", async () => {
    renderDetail(makeJobDetail({ category: "Academic" }));

    expect(await screen.findByText("Academic")).toBeInTheDocument();
  });

  it("says nothing about a category the platform never gave", async () => {
    renderDetail(makeJobDetail({ category: "" }));

    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByText("Advert information")).not.toBeInTheDocument();
  });

  it("carries both verdicts", async () => {
    renderDetail();

    await screen.findByRole("heading", { level: 1 });

    expect(screen.getByText(/Sponsor confirmed/)).toBeInTheDocument();
    expect(screen.getByText(/Pay cut/)).toBeInTheDocument();
  });

  it("keeps exactly one Apply link and one copy of each verdict in the tree", async () => {
    renderDetail();

    await screen.findByRole("heading", { level: 1 });

    expect(screen.getAllByRole("link", { name: /Apply on the employer/ })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Save" })).toHaveLength(1);
    expect(screen.getAllByText(/Sponsor confirmed/)).toHaveLength(1);
  });

  it("warns when the vacancy is no longer listed rather than hiding it", async () => {
    renderDetail(makeJobDetail({ status: "DISAPPEARED" }));

    expect(await screen.findByText(/No longer listed/)).toBeInTheDocument();
  });

  it("shows the raw salary string beside the parsed verdict", async () => {
    renderDetail(
      makeJobDetail({
        salary_raw: "£38,784 to £46,049 per annum",
        screening: makeScreening({ threshold_verdict: "SALARY_UNCLEAR", salary_min: null }),
      }),
    );

    expect(await screen.findByText("£38,784 to £46,049 per annum")).toBeInTheDocument();
  });

  it("names the classified discipline among the facts", async () => {
    renderDetail(makeJobDetail({ discipline: "PSYCHOLOGY" }));

    expect(await screen.findByText("Psychology")).toBeInTheDocument();
  });

  it("says nothing when the classifier found nothing confident to say", async () => {
    renderDetail(makeJobDetail({ discipline: "OTHER" }));

    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByText("Other")).not.toBeInTheDocument();
  });

  describe("the Closing fact", () => {
    beforeEach(() => {
      vi.setSystemTime(new Date("2026-09-20T09:00:00Z"));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("reads in red when the closing date is today", async () => {
      renderDetail(makeJobDetail({ closing_date: "2026-09-20" }));

      const value = await screen.findByText("Closes today");

      expect(value).toHaveClass("text-danger");
    });

    it("does not read as danger for a closing date further out", async () => {
      renderDetail(makeJobDetail({ closing_date: "2026-09-25" }));

      const value = await screen.findByText("Closes in 5 days");

      expect(value).not.toHaveClass("text-danger");
    });
  });

  describe("clicking Apply", () => {
    it("does not mark the job Applied by itself — it asks first", async () => {
      const user = userEvent.setup();
      renderDetail();
      const link = await screen.findByRole("link", { name: /Apply on the employer/ });

      await user.click(link);

      expect(
        await screen.findByRole("heading", { name: /Did you apply to this job/ }),
      ).toBeInTheDocument();
      expect(globalThis.fetch).not.toHaveBeenCalledWith(
        expect.stringContaining("/applications/"),
        expect.anything(),
      );
    });

    it("creates a FOUND application when the candidate says not yet", async () => {
      const user = userEvent.setup();
      renderDetail(DETAIL, { "/applications/": APPLICATION_RESPONSE });
      await user.click(await screen.findByRole("link", { name: /Apply on the employer/ }));

      await user.click(await screen.findByRole("button", { name: /Not yet/ }));

      await waitFor(() => {
        const [, requestBody] = lastRequestTo("/applications/");
        expect(requestBody).toMatchObject({ job: DETAIL.id, status: "FOUND" });
      });
    });

    it("creates an APPLIED application when the candidate confirms", async () => {
      const user = userEvent.setup();
      renderDetail(DETAIL, { "/applications/": APPLICATION_RESPONSE });
      await user.click(await screen.findByRole("link", { name: /Apply on the employer/ }));

      await user.click(await screen.findByRole("button", { name: /Yes, mark Applied/ }));

      await waitFor(() => {
        const [, requestBody] = lastRequestTo("/applications/");
        expect(requestBody).toMatchObject({ job: DETAIL.id, status: "APPLIED" });
      });
    });

    it("moves the existing pipeline entry instead of creating a second one", async () => {
      const user = userEvent.setup();
      renderDetail(makeJobDetail({ application_id: 42, application_status: "FOUND" }), {
        "/applications/42/move/": APPLICATION_RESPONSE,
        "/applications/": APPLICATION_RESPONSE,
      });
      await user.click(await screen.findByRole("link", { name: /Apply on the employer/ }));

      await user.click(await screen.findByRole("button", { name: /Yes, mark Applied/ }));

      await waitFor(() => {
        const [, requestBody] = lastRequestTo("/applications/42/move/");
        expect(requestBody).toMatchObject({ status: "APPLIED" });
      });
    });

    it("closes the dialog once a decision is recorded", async () => {
      const user = userEvent.setup();
      renderDetail(DETAIL, { "/applications/": APPLICATION_RESPONSE });
      await user.click(await screen.findByRole("link", { name: /Apply on the employer/ }));
      await user.click(await screen.findByRole("button", { name: /Not yet/ }));

      await waitFor(() => {
        expect(screen.queryByRole("heading", { name: /Did you apply to this job/ })).toBeNull();
      });
    });
  });
});

function lastRequestTo(fragment: string): [string, unknown] {
  const calls = vi.mocked(globalThis.fetch).mock.calls;
  const call = [...calls].reverse().find(([input]) => urlOf(input).includes(fragment));
  if (!call) throw new Error(`No request was made to ${fragment}`);
  const [input, init] = call;
  const body = init && "body" in init && typeof init.body === "string" ? JSON.parse(init.body) : null;
  return [urlOf(input), body];
}
