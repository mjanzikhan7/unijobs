import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ForgotPassword } from "./ForgotPassword";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ForgotPassword", () => {
  it("shows the non-revealing sent state after submitting", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Email"), "a.morgan@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByText("If that address has an account, a reset link is on its way.")).toBeInTheDocument();
    const [, options] = fetchSpy.mock.calls[0]!;
    expect(JSON.parse((options as RequestInit).body as string)).toEqual({
      email: "a.morgan@example.com",
    });
  });

  it("shows the sent state even when the server errors — never confirms non-existence either way", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ detail: "Server error." }, 500));
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Email"), "a.morgan@example.com");
    await userEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText(/reset link is on its way/)).not.toBeInTheDocument();
  });
});
