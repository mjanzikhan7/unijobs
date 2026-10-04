import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UserAdmin } from "./UserAdmin";
import { paginate, renderWithProviders, stubFetch } from "@/test-utils";
import { urlOf } from "@/models/api/client";
import type { Role } from "@/viewmodels/auth";

let myRole: Role = "ADMIN";
let myUsername = "r.patel";

vi.mock("@/viewmodels/auth", () => ({
  useAuth: () => ({ user: { username: myUsername, role: myRole }, role: myRole }),
}));

function makeUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 2,
    username: "t.nakamura",
    email: "t.nakamura@example.com",
    role: "MANAGER",
    email_verified: true,
    is_active: true,
    date_joined: "2026-02-14T09:12:00Z",
    last_login: null,
    assigned_institutions: [],
    ...overrides,
  };
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("UserAdmin", () => {
  it("gives a manager a read-only page — no create form, no role controls", async () => {
    myRole = "MANAGER";
    myUsername = "t.nakamura";
    stubFetch({ "/users/": paginate([makeUser({ username: "a.morgan", role: "CANDIDATE" })]) });
    renderWithProviders(<UserAdmin />);

    await screen.findByText("a.morgan");
    expect(screen.queryByRole("button", { name: "Create account" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Role for a.morgan/)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/Changing them is an administrator.s job/);
  });

  it("shows 'you' instead of controls on the signed-in admin's own row", async () => {
    myRole = "ADMIN";
    myUsername = "r.patel";
    stubFetch({
      "/users/": paginate([
        makeUser({ id: 1, username: "r.patel", role: "ADMIN" }),
        makeUser({ id: 2, username: "t.nakamura", role: "MANAGER" }),
      ]),
    });
    renderWithProviders(<UserAdmin />);

    await screen.findByText("r.patel");
    expect(screen.queryByLabelText(/Role for r.patel/)).not.toBeInTheDocument();
    expect(screen.getAllByText("you")).toHaveLength(1);
    expect(screen.getByLabelText(/Role for t.nakamura/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Suspend" })).toBeInTheDocument();
  });

  it("flags an unverified email without hiding the address", async () => {
    myRole = "ADMIN";
    myUsername = "r.patel";
    stubFetch({
      "/users/": paginate([
        makeUser({
          id: 4,
          username: "l.duarte",
          email: "l.duarte@example.com",
          email_verified: false,
          is_active: false,
        }),
      ]),
    });
    renderWithProviders(<UserAdmin />);

    expect(await screen.findByText("unverified")).toBeInTheDocument();
    expect(screen.getByText(/l\.duarte@example\.com/)).toBeInTheDocument();
    expect(screen.getByText("suspended")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Restore" })).toBeInTheDocument();
  });

  it("suspends an active account, not restores it, when Suspend is pressed", async () => {
    myRole = "ADMIN";
    myUsername = "r.patel";
    stubFetch({ "/users/": paginate([makeUser({ id: 4, is_active: true })]) });
    renderWithProviders(<UserAdmin />);

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(makeUser()));
    await userEvent.click(await screen.findByRole("button", { name: "Suspend" }));

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/users/4/deactivate/");
  });

  it("creates an account and clears the form on success", async () => {
    myRole = "ADMIN";
    myUsername = "r.patel";
    stubFetch({ "/users/": paginate([]) });
    renderWithProviders(<UserAdmin />);

    await screen.findByRole("button", { name: "Create account" });
    await userEvent.type(screen.getByLabelText("Username"), "a.morgan");
    await userEvent.type(screen.getByLabelText("Email"), "a.morgan@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "a-strong-password");

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockImplementation(() => Promise.resolve(jsonResponse(makeUser({ username: "a.morgan" }))));
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/users/");
    expect(await screen.findByLabelText("Username")).toHaveValue("");
  });

  it("says nothing under Institutions for a non-recruiter", async () => {
    myRole = "ADMIN";
    myUsername = "r.patel";
    stubFetch({
      "/users/": paginate([makeUser({ id: 4, role: "MANAGER" })]),
      "/institutions/": paginate([]),
    });
    renderWithProviders(<UserAdmin />);

    await screen.findByText("t.nakamura");
    expect(
      screen.queryByLabelText(/Institutions assigned to t.nakamura/),
    ).not.toBeInTheDocument();
  });

  it("offers an admin an institution picker for a recruiter row", async () => {
    myRole = "ADMIN";
    myUsername = "r.patel";
    stubFetch({
      "/users/": paginate([
        makeUser({
          id: 5,
          username: "b.osei",
          role: "RECRUITER",
          assigned_institutions: [{ slug: "northgate", name: "Northgate University" }],
        }),
      ]),
      "/institutions/": paginate([
        { id: 1, slug: "northgate", name: "Northgate University" },
        { id: 2, slug: "southbridge", name: "Southbridge College" },
      ]),
    });
    renderWithProviders(<UserAdmin />);

    const picker = await screen.findByLabelText(/Institutions assigned to b.osei/);
    expect(picker).toHaveValue(["northgate"]);

    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse(makeUser({ id: 5, role: "RECRUITER" })));
    await userEvent.selectOptions(picker, ["southbridge"]);

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/users/5/set-institutions/");
  });
});
