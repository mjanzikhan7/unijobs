import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AddJob } from "./AddJob";
import { paginate, renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";
import type { Role } from "@/viewmodels/auth";

let myRole: Role = "ADMIN";
let myAssigned: string[] = [];
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ role: myRole, assignedInstitutions: myAssigned }),
}));

const INSTITUTIONS = [
  { id: 1, slug: "northgate", name: "Northgate University" },
  { id: 2, slug: "southbridge", name: "Southbridge College" },
];

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("AddJob", () => {
  it("pre-fills the form from a successful read", async () => {
    myRole = "ADMIN";
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<AddJob />);

    await userEvent.type(screen.getByLabelText("Paste the advert URL"), "https://example.ac.uk/1");
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValueOnce(
      jsonResponse({
        extracted: true,
        draft: {
          source_url: "https://example.ac.uk/1",
          title: "Lecturer in Physics",
          department: "School of Science",
          salary_raw: "£45,000 to £52,000",
        },
      }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Read this page" }));

    expect(await screen.findByLabelText("Title")).toHaveValue("Lecturer in Physics");
    expect(screen.getByLabelText("Department")).toHaveValue("School of Science");
  });

  it("shows why nothing was read, without blocking the form", async () => {
    myRole = "ADMIN";
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<AddJob />);

    await userEvent.type(screen.getByLabelText("Paste the advert URL"), "https://example.ac.uk/1");
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValueOnce(
      jsonResponse({ extracted: false, reason: "the site refused the request", draft: {} }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Read this page" }));

    expect(await screen.findByText(/the site refused the request/)).toBeInTheDocument();
  });

  it("offers every institution to an admin", async () => {
    myRole = "ADMIN";
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<AddJob />);

    expect(await screen.findByRole("option", { name: "Northgate University" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Southbridge College" })).toBeInTheDocument();
  });

  it("narrows the institution picker to a recruiter's own", async () => {
    myRole = "RECRUITER";
    myAssigned = ["northgate"];
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<AddJob />);

    expect(await screen.findByRole("option", { name: "Northgate University" })).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: "Southbridge College" }),
    ).not.toBeInTheDocument();
    myRole = "ADMIN";
    myAssigned = [];
  });

  it("saves the job and reports which URL it posted to", async () => {
    myRole = "ADMIN";
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<AddJob />);

    await screen.findByRole("option", { name: "Northgate University" });
    await userEvent.selectOptions(screen.getByLabelText("Institution"), "northgate");
    await userEvent.type(screen.getByLabelText("Title"), "Lecturer in Physics");
    await userEvent.type(screen.getByLabelText("Source URL"), "https://example.ac.uk/vacancy/9");

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse({ id: 9 }, 201));
    await userEvent.click(screen.getByRole("button", { name: "Save job" }));

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/jobs/manual/");
  });
});
