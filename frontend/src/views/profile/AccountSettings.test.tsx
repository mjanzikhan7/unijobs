import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type * as RouterModule from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AccountSettings } from "./AccountSettings";
import { renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";

const navigateSpy = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof RouterModule>();
  return { ...actual, useNavigate: () => navigateSpy };
});

const signOutSpy = vi.fn();
vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ signOut: signOutSpy }),
}));

function account(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    username: "a.morgan",
    email: "a.morgan@example.com",
    first_name: "Amara",
    last_name: "Morgan",
    role: "CANDIDATE",
    email_verified: true,
    digest_enabled: true,
    pending_email: "",
    date_joined: "2026-01-08T10:00:00Z",
    ...overrides,
  };
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderPage() {
  return renderWithProviders(<AccountSettings />);
}

describe("AccountSettings", () => {
  it("opens only one row's edit form at a time", async () => {
    stubFetch({ "/account/": account() });
    renderPage();

    await userEvent.click((await screen.findAllByRole("button", { name: "Edit" }))[0]!);
    expect(screen.getByLabelText("New email")).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("button", { name: "Edit" })[2]!);
    expect(screen.queryByLabelText("New email")).not.toBeInTheDocument();
    expect(screen.getByLabelText("First name")).toBeInTheDocument();
  });

  it("submits only the email field when changing the address", async () => {
    stubFetch({ "/account/": account() });
    renderPage();

    await userEvent.click((await screen.findAllByRole("button", { name: "Edit" }))[0]!);
    const emailInput = screen.getByLabelText("New email");
    await userEvent.clear(emailInput);
    await userEvent.type(emailInput, "a.morgan+new@example.com");

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(account()));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/account/");
    expect(JSON.parse((options as RequestInit).body as string)).toEqual({
      email: "a.morgan+new@example.com",
    });
  });

  it("shows which address is still in force while a change is pending", async () => {
    stubFetch({ "/account/": account({ pending_email: "a.morgan+new@example.com" }) });
    renderPage();

    expect(await screen.findByText("a.morgan+new@example.com")).toBeInTheDocument();
    expect(screen.getByText(/this account still uses/i)).toBeInTheDocument();
  });

  it("flags an unconfirmed email without hiding the address", async () => {
    stubFetch({ "/account/": account({ email_verified: false }) });
    renderPage();

    expect(await screen.findByText("Unconfirmed")).toBeInTheDocument();
    expect(screen.getByText(/a\.morgan@example\.com/)).toBeInTheDocument();
  });

  it("sends both password fields and warns that other devices are signed out", async () => {
    stubFetch({ "/account/": account() });
    renderPage();

    await userEvent.click((await screen.findAllByRole("button", { name: "Edit" }))[1]!);
    await userEvent.type(screen.getByLabelText("Current password"), "old-password-123");
    await userEvent.type(screen.getByLabelText("New password"), "new-password-456");
    expect(screen.getByText(/Other devices are signed out/)).toBeInTheDocument();

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({ token: "t" }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    const [, options] = fetchSpy.mock.calls[0]!;
    expect(JSON.parse((options as RequestInit).body as string)).toEqual({
      current_password: "old-password-123",
      new_password: "new-password-456",
    });
  });

  it("never offers to edit the role — that is an administrator's action", async () => {
    stubFetch({ "/account/": account() });
    renderPage();

    await screen.findByText("CANDIDATE");
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(3);
  });

  it("posts an explicit true or false for the digest, never inferred", async () => {
    stubFetch({ "/account/": account({ digest_enabled: true }) });
    renderPage();

    const no = await screen.findByRole("radio", { name: "No" });
    expect(no).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Yes" })).toBeChecked();

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    await userEvent.click(no);

    const [, options] = fetchSpy.mock.calls[0]!;
    expect(JSON.parse((options as RequestInit).body as string)).toEqual({ digest_enabled: false });
  });

  it("requires the current password before deleting, then signs out and returns to /login", async () => {
    stubFetch({ "/account/": account() });
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Delete account" }));
    expect(screen.getByRole("alert")).toHaveTextContent("This cannot be undone");

    await userEvent.type(screen.getByLabelText("Confirm your password"), "current-password");
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(new Response(null, { status: 204 }));
    await userEvent.click(screen.getByRole("button", { name: "Delete my account" }));

    await vi.waitUntil(() => signOutSpy.mock.calls.length > 0);
    expect(navigateSpy).toHaveBeenCalledWith("/login", { replace: true });
  });

  it("cancels the delete confirmation without touching the network", async () => {
    stubFetch({ "/account/": account() });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear();
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Delete account" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByLabelText("Confirm your password")).not.toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(1);
  });

  it("signs out on the Sign out button", async () => {
    stubFetch({ "/account/": account() });
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(signOutSpy).toHaveBeenCalled();
  });
});
