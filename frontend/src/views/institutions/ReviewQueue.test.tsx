import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewQueue } from "./ReviewQueue";
import { renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";
import type { Institution } from "@/models/api/types";

function makeInstitution(overrides: Partial<Institution> = {}): Institution {
  return {
    id: 5,
    slug: "royal-thames",
    name: "Royal Thames Conservatoire",
    city: "London",
    nation: "ENGLAND",
    careers_url: "https://royalthames.example/careers",
    sponsor_match: { candidates: [] } as unknown as Institution["sponsor_match"],
    ...overrides,
  } as unknown as Institution;
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ReviewQueue", () => {
  it("shows the empty state when every institution has a confirmed verdict", async () => {
    stubFetch({ "/institutions/review-queue/": [] });
    renderWithProviders(<ReviewQueue />);

    expect(await screen.findByText(/Nothing to review/)).toBeInTheDocument();
  });

  it("shows the matcher's suggested candidates with their similarity", async () => {
    stubFetch({
      "/institutions/review-queue/": [
        makeInstitution({
          sponsor_match: {
            candidates: [
              {
                organisation_name: "ROYAL THAMES CONSERVATOIRE OF MUSIC AND DRAMA",
                town_city: "London",
                type_rating: "Worker (A rating)",
                similarity: 0.87,
              },
            ],
          } as unknown as Institution["sponsor_match"],
        }),
      ],
    });
    renderWithProviders(<ReviewQueue />);

    expect(
      await screen.findByText("ROYAL THAMES CONSERVATOIRE OF MUSIC AND DRAMA"),
    ).toBeInTheDocument();
    expect(screen.getByText("87% similar")).toBeInTheDocument();
  });

  it("says nothing resembles the name when the matcher found no candidates", async () => {
    stubFetch({ "/institutions/review-queue/": [makeInstitution()] });
    renderWithProviders(<ReviewQueue />);

    expect(await screen.findByText(/Nothing on the register resembles this name/)).toBeInTheDocument();
  });

  it("disables Save decision until a candidate is chosen or the verdict is 'not found'", async () => {
    stubFetch({
      "/institutions/review-queue/": [
        makeInstitution({
          sponsor_match: { candidates: [] } as unknown as Institution["sponsor_match"],
        }),
      ],
    });
    renderWithProviders(<ReviewQueue />);

    expect(await screen.findByRole("button", { name: "Save decision" })).toBeDisabled();
  });

  it("enables Save decision once a suggested candidate is picked, and posts it", async () => {
    stubFetch({
      "/institutions/review-queue/": [
        makeInstitution({
          sponsor_match: {
            candidates: [{ organisation_name: "ROYAL THAMES CONSERVATOIRE", similarity: 0.87 }],
          } as unknown as Institution["sponsor_match"],
        }),
      ],
    });
    renderWithProviders(<ReviewQueue />);

    const radio = await screen.findByRole("radio", { name: /ROYAL THAMES CONSERVATOIRE/ });
    await userEvent.click(radio);
    expect(screen.getByRole("button", { name: "Save decision" })).toBeEnabled();

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockImplementation(() => Promise.resolve(jsonResponse([])));
    await userEvent.click(screen.getByRole("button", { name: "Save decision" }));

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/institutions/5/resolve-sponsor/");
    const body = JSON.parse((options as RequestInit).body as string) as Record<string, string>;
    expect(body.registered_legal_name).toBe("ROYAL THAMES CONSERVATOIRE");
    expect(body.verdict).toBe("CONFIRMED");
    expect(await screen.findByText(/Recorded a verdict for Royal Thames Conservatoire/)).toBeInTheDocument();
  });

  it("records 'not on the register' without requiring a chosen candidate", async () => {
    stubFetch({ "/institutions/review-queue/": [makeInstitution()] });
    renderWithProviders(<ReviewQueue />);

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(makeInstitution()));
    await userEvent.click(await screen.findByRole("button", { name: "Not on the register" }));

    const [, options] = fetchSpy.mock.calls[0]!;
    const body = JSON.parse((options as RequestInit).body as string) as Record<string, string>;
    expect(body.verdict).toBe("NOT_FOUND");
    expect(body.registered_legal_name).toBe("");
  });

  it("only searches the register once at least three characters are typed", async () => {
    stubFetch({ "/institutions/review-queue/": [makeInstitution()] });
    renderWithProviders(<ReviewQueue />);

    const search = await screen.findByLabelText("Search the register directly");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse([]));
    await userEvent.type(search, "uk");
    expect(fetchSpy).not.toHaveBeenCalled();

    await userEvent.type(search, "r");
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("register-search/?q=ukr");
  });

  it("switches the verdict to 'sponsored via parent' when a register-search result is picked", async () => {
    stubFetch({ "/institutions/review-queue/": [makeInstitution()] });
    renderWithProviders(<ReviewQueue />);

    const search = await screen.findByLabelText("Search the register directly");
    vi.spyOn(globalThis, "fetch").mockClear().mockImplementation(() =>
      Promise.resolve(
        jsonResponse([{ organisation_name: "UK RESEARCH AND INNOVATION", similarity: 1 }]),
      ),
    );
    await userEvent.type(search, "UK Research");

    const radio = await screen.findByRole("radio", { name: /UK RESEARCH AND INNOVATION/ });
    await userEvent.click(radio);

    expect(screen.getByRole("combobox", { name: "Verdict" })).toHaveValue("CONFIRMED_VIA_PARENT");
  });
});
