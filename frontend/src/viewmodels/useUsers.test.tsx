import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useCreateUser, useSetRole, useSetUserActive, useUsers } from "./useUsers";
import { urlOf } from "@/models/api/client";
import { paginate, storeWrapper } from "@/test-utils";
import type { ManagedUser } from "./useUsers";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const user: ManagedUser = {
  id: 2,
  username: "t.nakamura",
  email: "t.nakamura@example.com",
  role: "MANAGER",
  email_verified: true,
  is_active: true,
  date_joined: "2026-02-14T09:12:00Z",
  last_login: null,
  assigned_institutions: [],
};

describe("useUsers", () => {
  it("fetches the full account list at once, not paginated", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(paginate([user])));
    const { result } = renderHook(() => useUsers(), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.data?.results).toHaveLength(1));
    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("page_size=200");
  });
});

describe("useCreateUser", () => {
  it("posts the new account's fields, role included", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(user));
    const { result } = renderHook(() => useCreateUser(), {
      wrapper: storeWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({
        username: "t.nakamura",
        email: "t.nakamura@example.com",
        password: "a-strong-password",
        role: "MANAGER",
      });
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/users/");
    expect((options as RequestInit).method).toBe("POST");
    const body = JSON.parse((options as RequestInit).body as string) as { role: string };
    expect(body.role).toBe("MANAGER");
  });
});

describe("useSetRole", () => {
  it("posts the chosen role to the set-role action", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(user));
    const { result } = renderHook(() => useSetRole(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync({ id: 2, role: "ADMIN" });
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/users/2/set-role/");
    const body = JSON.parse((options as RequestInit).body as string) as { role: string };
    expect(body.role).toBe("ADMIN");
  });
});

describe("useSetUserActive", () => {
  it("calls reactivate when turning a suspended account back on", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(user));
    const { result } = renderHook(() => useSetUserActive(), {
      wrapper: storeWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ id: 4, active: true });
    });

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toContain("/users/4/reactivate/");
  });

  it("calls deactivate when suspending an active account — never the reverse", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(user));
    const { result } = renderHook(() => useSetUserActive(), {
      wrapper: storeWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ id: 4, active: false });
    });

    const url = urlOf(fetchSpy.mock.calls[0]![0]);
    expect(url).toContain("/users/4/deactivate/");
    expect(url).not.toContain("reactivate");
  });
});
