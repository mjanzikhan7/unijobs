import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { A11yProvider } from "@unijobs/a11y/react";
import { createNoopStorageAdapter } from "@unijobs/a11y/core";

import type * as AuthModule from "@/viewmodels/auth";
import type { Role } from "@/viewmodels/auth";

import { createTestStore, storeWrapper } from "@/test-utils";

import { AppShell } from "./AppShell";

const activeRun = vi.fn();
const reviewQueue = vi.fn();
const signOut = vi.fn();

vi.mock("@/viewmodels/useActiveRun", () => ({
  useActiveRun: () => {
    activeRun();
    return { data: undefined };
  },
}));

vi.mock("@/viewmodels/useInstitutions", () => ({
  useReviewQueue: () => {
    reviewQueue();
    return { data: [] };
  },
}));

let role: Role | null = "CANDIDATE";

vi.mock("@/viewmodels/auth", async (importOriginal) => {
  const actual = await importOriginal<typeof AuthModule>();
  return {
    ...actual,
    useAuth: () => ({
      user: { username: "a.morgan", role, email_verified: true },
      role,
      isStaff: role === "ADMIN" || role === "MANAGER",
      isLoading: false,
      signIn: vi.fn(),
      signOut,
    }),
  };
});

function renderShell(): void {
  const Store = storeWrapper(createTestStore());
  render(
    <A11yProvider options={{ storage: createNoopStorageAdapter() }}>
      <Store>
        <MemoryRouter initialEntries={["/"]}>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<p>Job search</p>} />
              <Route path="/saved" element={<p>Saved jobs</p>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </Store>
    </A11yProvider>,
  );
}

beforeEach(() => {
  role = "CANDIDATE";
  window.localStorage.clear();
  vi.clearAllMocks();
});

afterEach(() => {
  window.localStorage.clear();
});

describe("AppShell", () => {
  it("renders the routed screen through its outlet", () => {
    renderShell();
    expect(screen.getByText("Job search")).toBeInTheDocument();
  });

  it("keeps the skip link pointing at the main landmark", () => {
    renderShell();

    expect(screen.getByRole("link", { name: "Skip to content" })).toHaveAttribute("href", "#main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
  });

  it("states the promise this product is built around", () => {
    renderShell();
    expect(screen.getByText(/never submits anything to an employer/i)).toBeInTheDocument();
  });

  it("shows who is signed in and offers a way out", async () => {
    renderShell();

    expect(screen.getByText("a.morgan")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(signOut).toHaveBeenCalledOnce();
  });

  it("makes the signed-in name a link to the account screen", () => {
    renderShell();

    expect(screen.getByRole("link", { name: "a.morgan" })).toHaveAttribute("href", "/profile");
  });

  it("gives a candidate no operator destinations", () => {
    renderShell();

    expect(screen.getByRole("link", { name: "Jobs" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Crawl console" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
  });

  it("gives an admin the operator destinations", () => {
    role = "ADMIN";
    renderShell();

    expect(screen.getByRole("link", { name: /Crawl console/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Users" })).toBeInTheDocument();
  });

  it("never polls the operator endpoints for a candidate", () => {
    renderShell();

    expect(activeRun).not.toHaveBeenCalled();
    expect(reviewQueue).not.toHaveBeenCalled();
  });

  it("opens the mobile drawer, and closes it when a destination is followed", async () => {
    renderShell();

    expect(screen.queryByRole("button", { name: "Close navigation" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(await screen.findByRole("button", { name: "Close navigation" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("link", { name: "Saved" }));

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Close navigation" })).not.toBeInTheDocument(),
    );
  });

  it("hides the shell behind the open drawer, so focus cannot wander into it", async () => {
    renderShell();
    await userEvent.click(screen.getByRole("button", { name: "Open navigation" }));

    await waitFor(() =>
      expect(screen.getAllByRole("navigation", { name: "Primary" })).toHaveLength(1),
    );
  });

  it("returns focus to the hamburger after the drawer closes", async () => {
    renderShell();

    const hamburger = screen.getByRole("button", { name: "Open navigation" });
    await userEvent.click(hamburger);
    await userEvent.click(await screen.findByRole("button", { name: "Close navigation" }));

    await waitFor(() => expect(hamburger).toHaveFocus());
  });

  it("collapses the desktop sidebar and remembers the choice", async () => {
    renderShell();

    await userEvent.click(screen.getByRole("button", { name: "Collapse navigation" }));

    expect(screen.getByRole("button", { name: "Expand navigation" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(window.localStorage.getItem("sidebar-collapsed")).toBe("true");
  });

  it("starts collapsed when that is what was chosen last time", () => {
    window.localStorage.setItem("sidebar-collapsed", "true");
    renderShell();

    expect(screen.getByRole("button", { name: "Expand navigation" })).toBeInTheDocument();
  });
});
