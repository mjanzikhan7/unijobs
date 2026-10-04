import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AddInstitution } from "./AddInstitution";
import { renderWithProviders } from "@/test-utils";
import { urlOf } from "@/models/api/client";
import type { Role } from "@/viewmodels/auth";

let myRole: Role = "ADMIN";
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ role: myRole }),
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("AddInstitution", () => {
  it("refuses anyone but an administrator", async () => {
    myRole = "MANAGER";
    renderWithProviders(<AddInstitution />);

    expect(
      await screen.findByText("Only an administrator can add an institution."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
    myRole = "ADMIN";
  });

  it("sends the filled-in fields, trimmed, and a blank ranking as null", async () => {
    renderWithProviders(<AddInstitution />);

    await userEvent.type(screen.getByLabelText("Name"), "  Northgate University  ");
    await userEvent.type(screen.getByLabelText("Careers URL"), "https://northgate.ac.uk/jobs");

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse({ id: 9, slug: "northgate-university" }, 201));
    await userEvent.click(screen.getByRole("button", { name: "Add institution" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const [input, init] = fetchSpy.mock.calls[0]!;
    expect(urlOf(input)).toContain("/institutions/");
    const body = JSON.parse((init as RequestInit).body as string) as Record<string, unknown>;
    expect(body).toMatchObject({
      name: "Northgate University",
      careers_url: "https://northgate.ac.uk/jobs",
      ranking: null,
      crawl_enabled: true,
    });
  });

  it("uploads a chosen logo once the institution has been created", async () => {
    renderWithProviders(<AddInstitution />);

    await userEvent.type(screen.getByLabelText("Name"), "Northgate University");
    const logo = new File(["logo"], "logo.png", { type: "image/png" });
    await userEvent.upload(screen.getByLabelText("Upload a logo"), logo);

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockImplementation((input) =>
      Promise.resolve(
        urlOf(input).includes("/media/")
          ? jsonResponse({ id: 9 }, 200)
          : jsonResponse({ id: 9, slug: "northgate-university" }, 201),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Add institution" }));

    await waitFor(() =>
      expect(fetchSpy.mock.calls.some(([input]) => urlOf(input).includes("/institutions/9/media/"))).toBe(
        true,
      ),
    );
  });

  it("does not upload anything when no logo or banner was chosen", async () => {
    renderWithProviders(<AddInstitution />);

    await userEvent.type(screen.getByLabelText("Name"), "Northgate University");

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse({ id: 9, slug: "northgate-university" }, 201));
    await userEvent.click(screen.getByRole("button", { name: "Add institution" }));

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    expect(urlOf(fetchSpy.mock.calls[0]![0])).not.toContain("/media/");
  });
});
