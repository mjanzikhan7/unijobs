import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { InstitutionInsights } from "./InstitutionInsights";
import { renderWithProviders, stubFetch } from "@/test-utils";

function payload(overrides: Record<string, unknown> = {}) {
  return {
    days: 90,
    limit: 500,
    totals: { posted: 3841, open_now: 1284, institutions_posting: 152 },
    by_day: [{ day: "2026-09-01", posted: 12 }],
    institutions: [
      { slug: "northgate", name: "Northgate University", posted: 188, open_now: 64, closed: 118, withdrawn: 6 },
    ],
    engagement: [{ slug: "northgate", name: "Northgate University", views: 1412, saves: 188, applications: 71 }],
    ...overrides,
  };
}

describe("InstitutionInsights", () => {
  it("joins posting and engagement rows by slug", async () => {
    stubFetch({ "/insights/institutions/": payload() });
    renderWithProviders(<InstitutionInsights />);

    expect(await screen.findByText("1412")).toBeInTheDocument();
  });

  it("shows zero interest for a posting row with no matching engagement row, rather than crashing", async () => {
    stubFetch({
      "/insights/institutions/": payload({
        institutions: [
          { slug: "no-interest", name: "Quiet College", posted: 5, open_now: 2, closed: 3, withdrawn: 0 },
        ],
        engagement: [],
      }),
    });
    renderWithProviders(<InstitutionInsights />);

    expect(await screen.findByText("Quiet College")).toBeInTheDocument();
  });

  it("shows the truncation notice only when the server actually hit its limit", async () => {
    stubFetch({ "/insights/institutions/": payload({ limit: 1 }) });
    renderWithProviders(<InstitutionInsights />);

    expect(await screen.findByText(/Showing the first 1 institutions/)).toBeInTheDocument();
  });

  it("hides the truncation notice when nothing was cut off", async () => {
    stubFetch({ "/insights/institutions/": payload({ limit: 500 }) });
    renderWithProviders(<InstitutionInsights />);

    await screen.findByText("Northgate University");
    expect(screen.queryByText(/Showing the first/)).not.toBeInTheDocument();
  });

  it("filters the table by name without a second request", async () => {
    stubFetch({
      "/insights/institutions/": payload({
        institutions: [
          { slug: "northgate", name: "Northgate University", posted: 188, open_now: 64, closed: 118, withdrawn: 6 },
          { slug: "caldmore", name: "Caldmore University", posted: 88, open_now: 29, closed: 58, withdrawn: 1 },
        ],
      }),
    });
    renderWithProviders(<InstitutionInsights />);

    await screen.findByText("Caldmore University");
    await userEvent.type(screen.getByLabelText("Filter"), "caldmore");

    expect(screen.queryByText("Northgate University")).not.toBeInTheDocument();
    expect(screen.getByText("Caldmore University")).toBeInTheDocument();
  });

  it("shows a row saying nothing matches, rather than an empty table", async () => {
    stubFetch({ "/insights/institutions/": payload() });
    renderWithProviders(<InstitutionInsights />);

    await screen.findByText("Northgate University");
    await userEvent.type(screen.getByLabelText("Filter"), "quantum");

    expect(await screen.findByText("Nothing matches that filter")).toBeInTheDocument();
  });

  it("switches the time window on click", async () => {
    stubFetch({ "/insights/institutions/": payload() });
    renderWithProviders(<InstitutionInsights />);

    await screen.findByText("Northgate University");
    await userEvent.click(screen.getByRole("radio", { name: "7d" }));

    await waitFor(() => expect(screen.getByRole("radio", { name: "7d" })).toBeChecked());
  });
});
