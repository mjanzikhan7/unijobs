import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MyInstitution } from "./MyInstitution";
import { paginate, renderWithProviders, stubFetch } from "@/test-utils";

let myAssigned: string[] = ["northgate"];
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ assignedInstitutions: myAssigned }),
}));

const INSTITUTIONS = [
  { id: 1, slug: "northgate", name: "Northgate University" },
  { id: 2, slug: "southbridge", name: "Southbridge College" },
];

describe("MyInstitution", () => {
  it("shows only the recruiter's own assigned institution", async () => {
    myAssigned = ["northgate"];
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<MyInstitution />);

    expect(await screen.findByText("Northgate University")).toBeInTheDocument();
    expect(screen.queryByText("Southbridge College")).not.toBeInTheDocument();
  });

  it("shows a card per institution when assigned more than one", async () => {
    myAssigned = ["northgate", "southbridge"];
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<MyInstitution />);

    expect(await screen.findByText("Northgate University")).toBeInTheDocument();
    expect(screen.getByText("Southbridge College")).toBeInTheDocument();
  });

  it("tells an unassigned recruiter to ask an admin, rather than showing nothing", async () => {
    myAssigned = [];
    stubFetch({ "/institutions/": paginate(INSTITUTIONS) });
    renderWithProviders(<MyInstitution />);

    expect(await screen.findByText("Nothing assigned yet")).toBeInTheDocument();
  });
});
