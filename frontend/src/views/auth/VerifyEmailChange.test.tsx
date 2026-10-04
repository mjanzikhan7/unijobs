import { StrictMode } from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { VerifyEmailChange } from "./VerifyEmailChange";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderAt(path: string) {
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/verify-email-change/:token" element={<VerifyEmailChange />} />
        </Routes>
      </MemoryRouter>
    </StrictMode>,
  );
}

describe("VerifyEmailChange", () => {
  it("shows a spinner while confirming", () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockReturnValue(new Promise(() => undefined));
    renderAt("/verify-email-change/tok-1");

    expect(screen.getByRole("status")).toHaveTextContent("Confirming your new address");
  });

  it("posts the token exactly once, even under StrictMode's double effect", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    renderAt("/verify-email-change/tok-1");

    await screen.findByText("Address updated");
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("confirms the update without ever printing an email address", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    const { container } = renderAt("/verify-email-change/tok-1");

    await screen.findByText("Address updated");
    expect(container.textContent).not.toMatch(/@/);
  });

  it("shows the failure message, reassuring that the old address still works", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ detail: "Expired." }, 400));
    renderAt("/verify-email-change/tok-1");

    expect(await screen.findByText("That link did not work")).toBeInTheDocument();
    expect(screen.getByText(/still uses its previous address/)).toBeInTheDocument();
  });
});
