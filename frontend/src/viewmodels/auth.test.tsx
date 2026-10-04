import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "./auth";
import { urlOf } from "@/models/api/client";
import { selectQueryData } from "@/store/queries/slice";
import { createTestStore, seedQuery, storeWrapper } from "@/test-utils";

function Probe() {
  const { user, isLoading, signOut } = useAuth();
  return (
    <div>
      <span data-testid="username">{isLoading ? "loading" : (user?.username ?? "none")}</span>
      <button type="button" onClick={() => void signOut()}>
        Sign out
      </button>
    </div>
  );
}

function renderProbe() {
  const store = createTestStore();
  return {
    store,
    ...render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
      { wrapper: storeWrapper(store) },
    ),
  };
}

const ME = { username: "a.morgan", role: "CANDIDATE", email_verified: true, assigned_institutions: [] };

function serve(meStatus: number, logout: () => Promise<Response> = () => Promise.resolve(new Response(null, { status: 204 }))) {
  return vi.spyOn(globalThis, "fetch").mockClear().mockImplementation((input) => {
    if (urlOf(input).includes("/auth/logout/")) return logout();
    return Promise.resolve(
      meStatus === 200
        ? new Response(JSON.stringify(ME), { status: 200 })
        : new Response(JSON.stringify({ detail: "no" }), { status: meStatus }),
    );
  });
}

describe("AuthProvider", () => {
  it("loads the signed-in person from the session", async () => {
    serve(200);
    renderProbe();

    await waitFor(() => expect(screen.getByTestId("username")).toHaveTextContent("a.morgan"));
  });

  it("treats no session as signed out, not as an error", async () => {
    serve(403);
    renderProbe();

    await waitFor(() => expect(screen.getByTestId("username")).toHaveTextContent("none"));
  });

  it("forgets a token left in localStorage by an older version", async () => {
    localStorage.setItem("hejobs.token", "old-token");
    serve(403);
    renderProbe();

    await waitFor(() => expect(localStorage.getItem("hejobs.token")).toBeNull());
  });

  it("signs out on the server and locally", async () => {
    const fetchSpy = serve(200);
    renderProbe();
    await waitFor(() => expect(screen.getByTestId("username")).toHaveTextContent("a.morgan"));

    screen.getByRole("button", { name: /sign out/i }).click();

    await waitFor(() => expect(screen.getByTestId("username")).toHaveTextContent("none"));
    expect(fetchSpy.mock.calls.some(([url]) => urlOf(url).includes("/auth/logout/"))).toBe(true);
  });

  it("signs out locally even when the network itself fails", async () => {
    serve(200, () => Promise.reject(new TypeError("Failed to fetch")));
    renderProbe();
    await waitFor(() => expect(screen.getByTestId("username")).toHaveTextContent("a.morgan"));

    screen.getByRole("button", { name: /sign out/i }).click();

    await waitFor(() => expect(screen.getByTestId("username")).toHaveTextContent("none"));
  });

  it("drops the previous person's cached data on sign out", async () => {
    serve(200);
    const { store } = renderProbe();
    await waitFor(() => expect(screen.getByTestId("username")).toHaveTextContent("a.morgan"));
    seedQuery(store, ["saved-jobs"], { results: [{ id: 1 }] });

    screen.getByRole("button", { name: /sign out/i }).click();

    await waitFor(() => expect(selectQueryData(store.getState(), ["saved-jobs"])).toBeUndefined());
  });
});
