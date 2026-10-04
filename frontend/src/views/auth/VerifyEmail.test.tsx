import { StrictMode } from "react";
import { render, screen } from "@testing-library/react";
import type * as RouterModule from "react-router-dom";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { VerifyEmail } from "./VerifyEmail";

const navigateSpy = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof RouterModule>();
  return { ...actual, useNavigate: () => navigateSpy };
});

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
          <Route path="/verify-email/:token" element={<VerifyEmail />} />
        </Routes>
      </MemoryRouter>
    </StrictMode>,
  );
}

describe("VerifyEmail", () => {
  it("shows a spinner while confirming", () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockReturnValue(new Promise(() => undefined));
    renderAt("/verify-email/tok-1");

    expect(screen.getByRole("status")).toHaveTextContent("Confirming your address");
  });

  it("posts the token exactly once, even under StrictMode's double effect", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    renderAt("/verify-email/tok-1");

    await vi.waitUntil(() => navigateSpy.mock.calls.length > 0);
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("redirects to a signed-in login on success", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    renderAt("/verify-email/tok-1");

    await vi.waitUntil(() => navigateSpy.mock.calls.length > 0);
    expect(navigateSpy).toHaveBeenCalledWith("/login?verified=1", { replace: true });
  });

  it("shows the expired-link message on failure, with a way back in", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ detail: "Expired." }, 400));
    renderAt("/verify-email/tok-1");

    expect(await screen.findByText("That link did not work")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Register again" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });
});
