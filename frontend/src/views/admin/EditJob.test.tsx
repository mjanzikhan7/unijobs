import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { EditJob } from "./EditJob";
import { makeJobDetail, renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";

function renderAt(id: number) {
  return renderWithProviders(
    <Routes>
      <Route path="/admin/jobs/:id/edit" element={<EditJob />} />
    </Routes>,
    { route: `/admin/jobs/${id}/edit` },
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("EditJob", () => {
  it("pre-fills the form from the job being edited", async () => {
    stubFetch({ "/jobs/": makeJobDetail({ id: 3, source: "MANUAL", title: "Lecturer in Physics" }) });
    renderAt(3);

    expect(await screen.findByLabelText("Title")).toHaveValue("Lecturer in Physics");
  });

  it("locks the institution and source URL rather than offering them as editable", async () => {
    stubFetch({
      "/jobs/": makeJobDetail({
        id: 3,
        source: "MANUAL",
        institution_name: "Northgate University",
        source_url: "https://northgate.ac.uk/vacancy/1",
      }),
    });
    renderAt(3);

    await screen.findByText("Northgate University");
    expect(screen.queryByLabelText("Institution")).not.toBeInTheDocument();
    expect(screen.getByText("https://northgate.ac.uk/vacancy/1")).toBeInTheDocument();
  });

  it("refuses to edit a crawled job", async () => {
    stubFetch({ "/jobs/": makeJobDetail({ id: 3, source: "PORTAL" }) });
    renderAt(3);

    expect(
      await screen.findByText(/This advert came from a crawl and is the employer.s text/),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Title")).not.toBeInTheDocument();
  });

  it("saves the edit and reports which URL it patched", async () => {
    stubFetch({ "/jobs/": makeJobDetail({ id: 3, source: "MANUAL", title: "Lecturer in Physics" }) });
    renderAt(3);

    const title = await screen.findByLabelText("Title");
    await userEvent.clear(title);
    await userEvent.type(title, "Senior Lecturer in Physics");

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse(makeJobDetail({ id: 3, source: "MANUAL" })));
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/jobs/3/");
  });

  it("asks for confirmation before deleting, and reports which job it deleted", async () => {
    stubFetch({ "/jobs/": makeJobDetail({ id: 3, source: "MANUAL" }) });
    renderAt(3);

    await userEvent.click(await screen.findByRole("button", { name: "Delete this job" }));
    expect(await screen.findByText("Delete this job?")).toBeInTheDocument();

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(new Response(null, { status: 204 }));
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/jobs/3/");
  });

  it("rejects a closing date before the posted date without submitting", async () => {
    stubFetch({
      "/jobs/": makeJobDetail({
        id: 3,
        source: "MANUAL",
        posted_date: "2026-09-10",
        closing_date: "2026-09-20",
      }),
    });
    renderAt(3);

    const closing = await screen.findByLabelText("Closing date");
    await userEvent.clear(closing);
    await userEvent.type(closing, "2026-09-01");

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear();
    const callsBeforeSave = fetchSpy.mock.calls.length;
    await userEvent.click(screen.getByRole("button", { name: "Save changes" }));

    expect(
      await screen.findByText("The closing date cannot be before the posted date."),
    ).toBeInTheDocument();
    expect(fetchSpy.mock.calls).toHaveLength(callsBeforeSave);
  });
});
