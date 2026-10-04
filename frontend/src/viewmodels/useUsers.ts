import { request } from "@/models/api/client";
import type { Paginated } from "@/models/api/types";
import type { Role } from "./auth";
import { queryKeys } from "@/models/queryKeys";
import { useMutation } from "@/store/mutations/useMutation";
import type { UseMutationResult } from "@/store/mutations/useMutation";
import { useQuery } from "@/store/queries/useQuery";
import type { UseQueryResult } from "@/store/queries/useQuery";

export interface AssignedInstitution {
  slug: string;
  name: string;
}

export interface ManagedUser {
  id: number;
  username: string;
  email: string;
  role: Role;
  email_verified: boolean;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
  assigned_institutions: AssignedInstitution[];
}

export function useUsers(): UseQueryResult<Paginated<ManagedUser>> {
  return useQuery({
    queryKey: queryKeys.users(),
    queryFn: () => request<Paginated<ManagedUser>>("/users/?page_size=200"),
  });
}

export function useCreateUser(): UseMutationResult<
  ManagedUser,
  Error,
  { username: string; email: string; password: string; role: Role }
> {
  return useMutation({
    mutationFn: (body) => request<ManagedUser>("/users/", { method: "POST", body }),
    invalidates: [queryKeys.users()],
  });
}

export function useSetRole(): UseMutationResult<ManagedUser, Error, { id: number; role: Role }> {
  return useMutation({
    mutationFn: ({ id, role }) =>
      request<ManagedUser>(`/users/${id}/set-role/`, { method: "POST", body: { role } }),
    invalidates: [queryKeys.users()],
  });
}

export function useSetInstitutions(): UseMutationResult<
  ManagedUser,
  Error,
  { id: number; institutions: string[] }
> {
  return useMutation({
    mutationFn: ({ id, institutions }) =>
      request<ManagedUser>(`/users/${id}/set-institutions/`, {
        method: "POST",
        body: { institutions },
      }),
    invalidates: [queryKeys.users()],
  });
}

export function useSetUserActive(): UseMutationResult<
  ManagedUser,
  Error,
  { id: number; active: boolean }
> {
  return useMutation({
    mutationFn: ({ id, active }) =>
      request<ManagedUser>(`/users/${id}/${active ? "reactivate" : "deactivate"}/`, {
        method: "POST",
      }),
    invalidates: [queryKeys.users()],
  });
}
