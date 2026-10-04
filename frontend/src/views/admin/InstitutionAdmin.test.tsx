import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { InstitutionAdmin } from "./InstitutionAdmin";
import { paginate, renderWithProviders, stubFetch } from "@/test-utils";
import type { Role } from "@/viewmodels/auth";
import type { Institution } from "@/models/api/types";

let myRole: Role = "ADMIN";
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ role: myRole }),
}));

function makeInstitution(overrides: Partial<Institution> = {}): Institution {
  return {
    id: 1,
    slug: "northgate",
    name: "Northgate University",
    platform: "STONEFISH",
    effective_platform: "Stonefish",
    open_jobs: 64,
    crawl_enabled: true,
    ...overrides,
  } as unknown as Institution;
}

function jsonErrorResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("InstitutionAdmin", () => {
  it("gives a manager crawl control but not add/delete/branding", async () => {
    myRole = "MANAGER";
    stubFetch({ "/institutions/": paginate([makeInstitution()]) });
    renderWithProviders(<InstitutionAdmin />);

    await screen.findByText("Northgate University");
    expect(screen.queryByRole("button", { name: "Add institution" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.getByText("admin only")).toBeInTheDocument();
    expect(screen.getByLabelText("Crawl Northgate University")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/administrator.s/);
  });

  it("gives an admin the full set of controls", async () => {
    myRole = "ADMIN";
    stubFetch({ "/institutions/": paginate([makeInstitution()]) });
    renderWithProviders(<InstitutionAdmin />);

    await screen.findByText("Northgate University");
    expect(screen.getByRole("button", { name: "Add institution" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Logo, banner, about" })).toBeInTheDocument();
  });

  it("opens the branding editor for the row named in ?edit=<slug>", async () => {
    myRole = "ADMIN";
    stubFetch({ "/institutions/": paginate([makeInstitution()]) });

    renderWithProviders(<InstitutionAdmin />, { route: "/admin/institutions?edit=northgate" });

    expect(await screen.findAllByText("Northgate University")).not.toHaveLength(0);
    expect(await screen.findByRole("button", { name: "Close" })).toBeInTheDocument();
  });

  it("shows the server's own refusal message when a delete is rejected", async () => {
    myRole = "ADMIN";
    stubFetch({ "/institutions/": paginate([makeInstitution()]) });
    renderWithProviders(<InstitutionAdmin />);

    await screen.findByText("Northgate University");
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(
      jsonErrorResponse(
        { detail: "This institution still has 64 jobs. Stop crawling it instead." },
        409,
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Delete" }));

    expect(
      await screen.findByText("This institution still has 64 jobs. Stop crawling it instead."),
    ).toBeInTheDocument();
  });

  it("opens the branding editor for one row at a time", async () => {
    myRole = "ADMIN";
    stubFetch({
      "/institutions/": paginate([
        makeInstitution({ id: 1, name: "Northgate University" }),
        makeInstitution({ id: 2, name: "Caldmore University", slug: "caldmore" }),
      ]),
    });
    renderWithProviders(<InstitutionAdmin />);

    await screen.findByText("Northgate University");
    const toggles = screen.getAllByRole("button", { name: "Logo, banner, about" });
    await userEvent.click(toggles[0]!);

    expect(screen.getByRole("button", { name: "Close" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Logo, banner, about" })).toHaveLength(1);
  });

  it("filters the table by name", async () => {
    myRole = "ADMIN";
    stubFetch({
      "/institutions/": paginate([
        makeInstitution({ id: 1, name: "Northgate University" }),
        makeInstitution({ id: 2, name: "Caldmore University", slug: "caldmore" }),
      ]),
    });
    renderWithProviders(<InstitutionAdmin />);

    await screen.findByText("Caldmore University");
    await userEvent.type(screen.getByLabelText("Filter"), "caldmore");

    expect(screen.queryByText("Northgate University")).not.toBeInTheDocument();
    expect(screen.getByText("Caldmore University")).toBeInTheDocument();
  });
});
