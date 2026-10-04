import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CandidateProfile } from "./CandidateProfile";
import { paginate, renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";

const suggestions = {
  skills: ["Python", "Kubernetes"],
  domains: ["research computing"],
  seniority: ["senior"],
  projects: [],
  education: [],
  years_experience: 6,
  missing: [],
};

function makeCV(overrides: Record<string, unknown> = {}) {
  return {
    id: 3,
    original_filename: "cv.pdf",
    content_type: "application/pdf",
    byte_size: 1000,
    suggestions,
    applied_at: null,
    uploaded_at: "2026-09-01T09:00:00Z",
    ...overrides,
  };
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("CandidateProfile", () => {
  it("shows the empty state when there is no active profile yet", async () => {
    stubFetch({ "/profiles/": paginate([]), "/cvs/": paginate([]) });
    renderWithProviders(<CandidateProfile />);

    expect(await screen.findByText(/No profile yet/)).toBeInTheDocument();
  });

  it("shows the active profile's facts", async () => {
    stubFetch({
      "/profiles/": paginate([
        {
          id: 1,
          is_active: true,
          skills: ["Python"],
          domains: [],
          seniority: [],
          projects: [],
          education: [],
          years_experience: 6,
        },
      ]),
      "/cvs/": paginate([]),
    });
    renderWithProviders(<CandidateProfile />);

    expect(await screen.findByText("Python")).toBeInTheDocument();
  });

  it("seeds the confirmation draft from an unapplied CV's suggestions", async () => {
    stubFetch({ "/profiles/": paginate([]), "/cvs/": paginate([makeCV()]) });
    renderWithProviders(<CandidateProfile />);

    expect(await screen.findByText("What we found")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
  });

  it("does not show a draft for a CV whose suggestions were already applied", async () => {
    stubFetch({
      "/profiles/": paginate([]),
      "/cvs/": paginate([makeCV({ applied_at: "2026-09-02T09:00:00Z" })]),
    });
    renderWithProviders(<CandidateProfile />);

    await screen.findByText(/No profile yet/);
    expect(screen.queryByText("What we found")).not.toBeInTheDocument();
  });

  it("drops an unticked term from what gets submitted", async () => {
    stubFetch({ "/profiles/": paginate([]), "/cvs/": paginate([makeCV()]) });
    renderWithProviders(<CandidateProfile />);

    await screen.findByText("Python");
    await userEvent.click(screen.getByRole("checkbox", { name: "Python" }));

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    await userEvent.click(screen.getByRole("button", { name: "Add these to my profile" }));

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/cvs/3/apply_to_profile/");
    const body = JSON.parse((options as RequestInit).body as string) as { skills: string[] };
    expect(body.skills).toEqual(["Kubernetes"]);
  });

  it("disables the confirm button while there is no CV to apply", async () => {
    stubFetch({ "/profiles/": paginate([]), "/cvs/": paginate([]) });
    renderWithProviders(<CandidateProfile />);

    await screen.findByText(/No profile yet/);
    expect(screen.queryByRole("button", { name: "Add these to my profile" })).not.toBeInTheDocument();
  });
});
