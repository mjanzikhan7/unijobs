import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { InstitutionDetail } from "./InstitutionDetail";
import { makeJob, paginate, renderWithProviders, stubFetch } from "@/test-utils";
import type { Institution } from "@/models/api/types";
import type { Role } from "@/viewmodels/auth";

let myRole: Role | null = "CANDIDATE";
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ role: myRole }),
}));

function makeInstitution(overrides: Partial<Institution> = {}): Institution {
  return {
    id: 1,
    slug: "northgate",
    name: "Northgate University",
    city: "Leeds",
    nation: "ENGLAND",
    institution_type: "University",
    open_jobs: 64,
    logo_url: null,
    banner_url: null,
    description: "",
    careers_url: null,
    sponsor_match: { verdict: "Sponsor confirmed", registered_legal_name: "NORTHGATE UNIVERSITY" },
    ...overrides,
  } as unknown as Institution;
}

function renderAtSlug(slug: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/institutions/:slug" element={<InstitutionDetail />} />
    </Routes>,
    { route: `/institutions/${slug}` },
  );
}

describe("InstitutionDetail", () => {
  it("shows the vacancy count from the jobs endpoint, not a stale field on the institution", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([makeInstitution()]),
      "/jobs/": paginate([makeJob()]),
    });
    renderAtSlug("northgate");

    expect(await screen.findByText("Northgate University")).toBeInTheDocument();
    expect(await screen.findByText("1")).toBeInTheDocument();
  });

  it("shows a real not-found panel for a slug matching no institution", async () => {
    stubFetch({
      "/institutions/?slug=ghost": paginate([]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("ghost");

    expect(await screen.findByText("No institution with that name.")).toBeInTheDocument();
  });

  it("shows the sponsor verdict and registered legal name when known", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([makeInstitution()]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("northgate");

    expect(await screen.findByText("Sponsor confirmed")).toBeInTheDocument();
    expect(screen.getByText("NORTHGATE UNIVERSITY")).toBeInTheDocument();
  });

  it("shows an empty message rather than a blank section when nothing is open", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([makeInstitution()]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("northgate");

    expect(await screen.findByText("Nothing open here at the moment")).toBeInTheDocument();
  });

  it("shows the contact card when any contact detail is set", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([
        makeInstitution({
          contact_email: "careers@northgate.ac.uk",
          contact_phone: "0113 000 0000",
          address: "Northgate Campus, Leeds",
        }),
      ]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("northgate");

    expect(await screen.findByRole("region", { name: "Contact" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "careers@northgate.ac.uk" })).toHaveAttribute(
      "href",
      "mailto:careers@northgate.ac.uk",
    );
    expect(screen.getByRole("link", { name: "0113 000 0000" })).toHaveAttribute(
      "href",
      "tel:01130000000",
    );
    expect(screen.getByText("Northgate Campus, Leeds")).toBeInTheDocument();
  });

  it("omits the contact card entirely when nothing has been entered", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([makeInstitution()]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("northgate");

    await screen.findByText("Northgate University");
    expect(screen.queryByRole("region", { name: "Contact" })).not.toBeInTheDocument();
  });

  it("shows a flat brand band rather than nothing when there is no banner", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([makeInstitution({ banner_url: null })]),
      "/jobs/": paginate([]),
    });
    const { container } = renderAtSlug("northgate");

    await screen.findByText("Northgate University");
    expect(container.querySelector("img")).not.toBeInTheDocument();
  });

  it("shows the real banner image once one has been uploaded", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([
        makeInstitution({ banner_url: "https://example.test/banner.png" }),
      ]),
      "/jobs/": paginate([]),
    });
    const { container } = renderAtSlug("northgate");

    await screen.findByText("Northgate University");
    expect(container.querySelector("img")).toHaveAttribute(
      "src",
      "https://example.test/banner.png",
    );
  });

  it("shows the About section only when a description has been written", async () => {
    stubFetch({
      "/institutions/?slug=northgate": paginate([
        makeInstitution({ description: "A research-intensive university in the north." }),
      ]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("northgate");

    expect(await screen.findByRole("heading", { name: "About" })).toBeInTheDocument();
    expect(screen.getByText("A research-intensive university in the north.")).toBeInTheDocument();
  });

  it("offers an admin the door to Manage institutions, deep-linked to this row", async () => {
    myRole = "ADMIN";
    stubFetch({
      "/institutions/?slug=northgate": paginate([makeInstitution()]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("northgate");

    expect(
      await screen.findByRole("link", { name: /Edit banner, logo, about/ }),
    ).toHaveAttribute("href", "/admin/institutions?edit=northgate");
    myRole = "CANDIDATE";
  });

  it("says nothing about editing to anyone who isn't an admin", async () => {
    myRole = "MANAGER";
    stubFetch({
      "/institutions/?slug=northgate": paginate([makeInstitution()]),
      "/jobs/": paginate([]),
    });
    renderAtSlug("northgate");

    await screen.findByText("Northgate University");
    expect(screen.queryByRole("link", { name: /Edit banner, logo, about/ })).not.toBeInTheDocument();
    myRole = "CANDIDATE";
  });
});
