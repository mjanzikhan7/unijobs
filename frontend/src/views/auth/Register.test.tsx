import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Register } from "./Register";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Register", () => {
  it("submits the three fields and shows the non-revealing sent state", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Username"), "a.morgan");
    await userEvent.type(screen.getByLabelText("Email"), "a.morgan@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "a-strong-password");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(/If that address can be registered/)).toBeInTheDocument();
    expect(screen.queryByText(/already/i)).not.toBeInTheDocument();

    const [, options] = fetchSpy.mock.calls[0]!;
    const body = JSON.parse((options as RequestInit).body as string) as Record<string, string>;
    expect(body).toEqual({
      username: "a.morgan",
      email: "a.morgan@example.com",
      password: "a-strong-password",
    });
  });

  it("shows a validation error and stays on the form", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(
      jsonResponse({ detail: "Validation failed.", errors: { password: ["Too short."] } }, 400),
    );
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Username"), "a.morgan");
    await userEvent.type(screen.getByLabelText("Email"), "a.morgan@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(/Too short/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
  });
});
