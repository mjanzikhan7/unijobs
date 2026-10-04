import { downloadFile, request } from "@/models/api/client";
import type { Role } from "./auth";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export interface Account {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  email_verified: boolean;
  digest_enabled: boolean;
  pending_email: string;
  date_joined: string;
}

export function useAccount(): UseQueryResult<Account> {
  return useQuery({
    queryKey: queryKeys.account(),
    queryFn: () => request<Account>("/account/"),
  });
}

export function useUpdateAccount(): UseMutationResult<
  Account,
  Error,
  Partial<Pick<Account, "email" | "first_name" | "last_name">>
> {
  return useMutation({
    mutationFn: (body) => request<Account>("/account/", { method: "PATCH", body }),
    invalidates: [
      queryKeys.account(),
      queryKeys.me(),
    ],
  });
}

export function useChangePassword(): UseMutationResult<
  { detail: string },
  Error,
  { current_password: string; new_password: string }
> {
  return useMutation({
    mutationFn: (body) =>
      request<{ detail: string }>("/account/password/", { method: "POST", body }),
  });
}

export function useSetDigest(): UseMutationResult<unknown, Error, boolean> {
  return useMutation({
    mutationFn: (enabled) =>
      request("/account/digest/", { method: "POST", body: { digest_enabled: enabled } }),
    invalidates: [queryKeys.account()],
  });
}

export function useDeleteAccount(): UseMutationResult<void, Error, string> {
  return useMutation({
    mutationFn: (password) =>
      request<void>("/account/", { method: "DELETE", body: { password } }),
  });
}

export function useDownloadMyData(): UseMutationResult<void, Error, void> {
  return useMutation({
    mutationFn: () => {
      const today = new Date().toISOString().slice(0, 10);
      return downloadFile("/account/export/", `unijobs-my-data-${today}.json`);
    },
  });
}
