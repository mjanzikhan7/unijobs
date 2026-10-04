import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type * as RouterModule from "react-router-dom";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ResetPassword } from "./ResetPassword";

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
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/reset-password/:uid/:token" element={<ResetPassword />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ResetPassword", () => {
  it("sends the uid and token from the URL, alongside the chosen password", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    renderAt("/reset-password/uid-abc/token-xyz");

    await userEvent.type(screen.getByLabelText("New password"), "a-new-strong-password");
    await userEvent.click(screen.getByRole("button", { name: "Set password" }));

    const [, options] = fetchSpy.mock.calls[0]!;
    const body = JSON.parse((options as RequestInit).body as string) as Record<string, string>;
    expect(body).toEqual({
      uid: "uid-abc",
      token: "token-xyz",
      password: "a-new-strong-password",
    });
  });

  it("returns to sign-in on success, since every device was just signed out", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    renderAt("/reset-password/uid-abc/token-xyz");

    await userEvent.type(screen.getByLabelText("New password"), "a-new-strong-password");
    await userEvent.click(screen.getByRole("button", { name: "Set password" }));

    await waitFor(() => expect(navigateSpy).toHaveBeenCalledWith("/login", { replace: true }));
  });

  it("shows the expired-link message and does not navigate on failure", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(
      jsonResponse({ detail: "That link did not work." }, 400),
    );
    renderAt("/reset-password/uid-abc/token-xyz");

    await userEvent.type(screen.getByLabelText("New password"), "a-new-strong-password");
    await userEvent.click(screen.getByRole("button", { name: "Set password" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(navigateSpy).not.toHaveBeenCalled();
  });
});
