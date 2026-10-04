import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  useAccount,
  useChangePassword,
  useDeleteAccount,
  useDownloadMyData,
  useSetDigest,
  useUpdateAccount,
} from "./useAccount";
import { urlOf } from "@/models/api/client";
import { queryKeys } from "@/models/queryKeys";
import { createTestStore, isInvalidated, seedQuery, storeWrapper, stubFetch } from "@/test-utils";
import type { Account } from "./useAccount";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const account: Account = {
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
};

describe("useAccount", () => {
  it("fetches the signed-in account", async () => {
    stubFetch({ "/account/": account });
    const { result } = renderHook(() => useAccount(), { wrapper: storeWrapper() });

    await waitFor(() => expect(result.current.data?.username).toBe("a.morgan"));
  });
});

describe("useUpdateAccount", () => {
  it("invalidates the account and /auth/me/ caches on success, not just its own", async () => {
    vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse(account));
    const store = createTestStore();
    seedQuery(store, queryKeys.account());
    seedQuery(store, queryKeys.me());
    const { result } = renderHook(() => useUpdateAccount(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current.mutateAsync({ first_name: "Amara" });
    });

    expect(isInvalidated(store, queryKeys.account())).toBe(true);
    expect(isInvalidated(store, queryKeys.me())).toBe(true);
  });
});

describe("useChangePassword", () => {
  it("posts the change and stores nothing in the browser", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(jsonResponse({ detail: "Password updated." }));
    const { result } = renderHook(() => useChangePassword(), {
      wrapper: storeWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({
        current_password: "old-pass",
        new_password: "new-password-12345",
      });
    });

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toBe("/api/account/password/");
    expect(localStorage.length).toBe(0);
  });
});

describe("useSetDigest", () => {
  it("posts the chosen state to the digest endpoint", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(jsonResponse({}));
    const { result } = renderHook(() => useSetDigest(), { wrapper: storeWrapper() });

    await act(async () => {
      await result.current.mutateAsync(false);
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/account/digest/");
    const body = JSON.parse((options as RequestInit).body as string) as { digest_enabled: boolean };
    expect(body.digest_enabled).toBe(false);
  });
});

describe("useDeleteAccount", () => {
  it("sends the confirmation password with the delete request", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockClear().mockResolvedValue(new Response(null, { status: 204 }));
    const { result } = renderHook(() => useDeleteAccount(), {
      wrapper: storeWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync("current-password");
    });

    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(urlOf(url)).toContain("/account/");
    expect((options as RequestInit).method).toBe("DELETE");
    const body = JSON.parse((options as RequestInit).body as string) as { password: string };
    expect(body.password).toBe("current-password");
  });

  it("downloads the personal data export as a file", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockClear()
      .mockResolvedValue(new Response("{}", { status: 200 }));
    const store = createTestStore();
    const { result } = renderHook(() => useDownloadMyData(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current.mutateAsync();
    });

    expect(urlOf(fetchSpy.mock.calls[0]![0])).toBe("/api/account/export/");
  });
});
