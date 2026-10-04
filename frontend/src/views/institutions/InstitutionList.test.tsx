import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { InstitutionList } from "./InstitutionList";
import { paginate, renderWithProviders, stubFetch } from "@/test-utils";
import type { Institution } from "@/models/api/types";

function makeInstitution(overrides: Partial<Institution> = {}): Institution {
  return {
    id: 1,
    slug: "northgate",
    name: "Northgate University",
    city: "Leeds",
    nation: "ENGLAND",
    open_jobs: 64,
    ...overrides,
  } as Institution;
}

describe("InstitutionList", () => {
  it("sorts by open vacancies, most first, ties broken by name", async () => {
    stubFetch({
      "/institutions/": paginate([
        makeInstitution({ id: 1, name: "Caldmore University", open_jobs: 10 }),
        makeInstitution({ id: 2, name: "Northgate University", open_jobs: 64 }),
        makeInstitution({ id: 3, name: "Aldwyn College", open_jobs: 10 }),
      ]),
    });
    renderWithProviders(<InstitutionList />);

    const names = (await screen.findAllByRole("link")).map((el) => el.textContent);
    expect(names).toEqual(["Northgate University", "Aldwyn College", "Caldmore University"]);
  });

  it("filters by name or city, case-insensitively", async () => {
    stubFetch({
      "/institutions/": paginate([
        makeInstitution({ id: 1, name: "Northgate University", city: "Leeds" }),
        makeInstitution({ id: 2, name: "Caldmore University", city: "Norwich" }),
      ]),
    });
    renderWithProviders(<InstitutionList />);

    await screen.findByText("Northgate University");
    await userEvent.type(screen.getByLabelText("Filter institutions"), "norwich");

    expect(screen.queryByText("Northgate University")).not.toBeInTheDocument();
    expect(screen.getByText("Caldmore University")).toBeInTheDocument();
  });

  it("shows a named empty state when the filter matches nothing", async () => {
    stubFetch({ "/institutions/": paginate([makeInstitution()]) });
    renderWithProviders(<InstitutionList />);

    await screen.findByText("Northgate University");
    await userEvent.type(screen.getByLabelText("Filter institutions"), "quantum");

    expect(await screen.findByRole("status")).toHaveTextContent(
      /No institutions match.*Nothing matched “quantum”/s,
    );
  });

  it("shows a loading state while the list is in flight", () => {
    stubFetch({ "/institutions/": paginate([]) });
    renderWithProviders(<InstitutionList />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading institutions");
  });
});
