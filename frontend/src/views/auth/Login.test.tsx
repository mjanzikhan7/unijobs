import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type * as RouterModule from "react-router-dom";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Login } from "./Login";

const navigateSpy = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof RouterModule>();
  return { ...actual, useNavigate: () => navigateSpy };
});

const signInSpy = vi.fn();
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ signIn: signInSpy }),
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Login", () => {
  it("asks for a session cookie, so no token reaches JavaScript", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse({ username: "a.morgan" }));
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Login />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Username"), "a.morgan");
    await userEvent.type(screen.getByLabelText("Password"), "hunter2-hunter2");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    const body = JSON.parse((fetchSpy.mock.calls[0]![1] as RequestInit).body as string) as {
      session: boolean;
    };
    expect(body.session).toBe(true);
    expect(localStorage.length).toBe(0);
  });

  it("signs in and returns to the job list by default", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ token: "tok-1" }));
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Login />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Username"), "a.morgan");
    await userEvent.type(screen.getByLabelText("Password"), "hunter2-hunter2");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(signInSpy).toHaveBeenCalledWith();
    expect(navigateSpy).toHaveBeenCalledWith("/", { replace: true });
  });

  it("returns to the page that redirected here, not the job list", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ token: "tok-1" }));
    render(
      <MemoryRouter initialEntries={["/login?next=%2Fadmin%2Fcrawl"]}>
        <Login />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Username"), "r.patel");
    await userEvent.type(screen.getByLabelText("Password"), "hunter2-hunter2");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(navigateSpy).toHaveBeenCalledWith("/admin/crawl", { replace: true });
  });

  it("shows the server's error and never signs in on a rejected credential", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(
      jsonResponse({ detail: "Unable to log in with provided credentials." }, 400),
    );
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Login />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Username"), "a.morgan");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText(/Unable to log in/)).toBeInTheDocument();
    expect(signInSpy).not.toHaveBeenCalled();
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it("shows the confirmation notice when arriving with ?verified=1", () => {
    render(
      <MemoryRouter initialEntries={["/login?verified=1"]}>
        <Login />
      </MemoryRouter>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Address confirmed. Sign in to continue.");
  });

  it("disables the submit button while the request is in flight", async () => {
    let resolveRequest: (value: Response) => void = () => undefined;
    vi.spyOn(globalThis, "fetch").mockClear().mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Login />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText("Username"), "a.morgan");
    await userEvent.type(screen.getByLabelText("Password"), "hunter2-hunter2");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("button", { name: "Signing in…" })).toBeDisabled();
    resolveRequest(jsonResponse({ token: "tok-1" }));
  });

  it("never prints working credentials on the sign-in page", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Login />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/changeme/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/dev credentials/i)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/jkhan/i);
  });
});
