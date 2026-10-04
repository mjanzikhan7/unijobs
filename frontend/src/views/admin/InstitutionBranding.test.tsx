import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { InstitutionBranding } from "./InstitutionBranding";
import { renderWithProviders } from "@/test-utils";
import { urlOf } from "@/models/api/client";
import type { Institution } from "@/models/api/types";

function makeInstitution(overrides: Partial<Institution> = {}): Institution {
  return {
    id: 7,
    slug: "royal-thames",
    name: "Royal Thames Conservatoire",
    city: "London",
    nation: "ENGLAND",
    open_jobs: 6,
    logo_url: null,
    banner_url: null,
    description: "",
    ...overrides,
  } as Institution;
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("InstitutionBranding", () => {
  it("says an empty slot is empty, rather than leaving a blank space", () => {
    renderWithProviders(<InstitutionBranding institution={makeInstitution()} />);

    expect(screen.getAllByText(/None yet/)).toHaveLength(2);
    expect(screen.getByText(/the monogram is used instead/)).toBeInTheDocument();
  });

  it("shows the existing images when present", () => {
    renderWithProviders(
      <InstitutionBranding
        institution={makeInstitution({
          logo_url: "https://cdn.test/logo.png",
          banner_url: "https://cdn.test/banner.png",
        })}
      />,
    );
    expect(screen.queryByText("None yet")).not.toBeInTheDocument();
  });

  it("uploads a logo as soon as it is chosen, not on a separate save", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(makeInstitution()));
    renderWithProviders(<InstitutionBranding institution={makeInstitution()} />);

    const file = new File(["binary"], "logo.png", { type: "image/png" });
    const input = screen.getByLabelText("Upload a logo for Royal Thames Conservatoire");
    await userEvent.upload(input, file);

    expect(fetchSpy).toHaveBeenCalled();
    const [url] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/institutions/7/media/");
  });

  it("saves the description only when the form is submitted", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(makeInstitution()));
    renderWithProviders(<InstitutionBranding institution={makeInstitution()} />);

    const textarea = screen.getByLabelText("About this institution");
    await userEvent.type(textarea, "A conservatoire in London.");
    expect(fetchSpy).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Save about & contact details" }));
    expect(fetchSpy).toHaveBeenCalled();
  });

  it("submits the contact details alongside the description in one save", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(makeInstitution()));
    renderWithProviders(<InstitutionBranding institution={makeInstitution()} />);

    await userEvent.type(screen.getByLabelText("Contact email"), "careers@royal-thames.ac.uk");
    await userEvent.type(screen.getByLabelText("Contact phone"), "020 0000 0000");
    await userEvent.type(screen.getByLabelText("Postal address"), "Thames Embankment, London");
    await userEvent.click(screen.getByRole("button", { name: "Save about & contact details" }));

    const [, options] = fetchSpy.mock.calls[0]!;
    const body = JSON.parse((options as RequestInit).body as string) as Record<string, string>;
    expect(body.contact_email).toBe("careers@royal-thames.ac.uk");
    expect(body.contact_phone).toBe("020 0000 0000");
    expect(body.address).toBe("Thames Embankment, London");
  });

  it("pre-fills the contact fields from the institution already stored", () => {
    renderWithProviders(
      <InstitutionBranding
        institution={makeInstitution({
          contact_email: "careers@royal-thames.ac.uk",
          contact_phone: "020 0000 0000",
          address: "Thames Embankment, London",
        })}
      />,
    );

    expect(screen.getByLabelText("Contact email")).toHaveValue("careers@royal-thames.ac.uk");
    expect(screen.getByLabelText("Contact phone")).toHaveValue("020 0000 0000");
    expect(screen.getByLabelText("Postal address")).toHaveValue("Thames Embankment, London");
  });
});
