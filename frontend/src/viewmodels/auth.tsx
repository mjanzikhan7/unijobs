import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";
import { useDispatch } from "react-redux";

import { ApiError, forgetLegacyToken, request } from "@/models/api/client";
import { queryKeys } from "@/models/queryKeys";
import { useQuery } from "@/store/queries/useQuery";
import { signOutRequested, signedIn } from "@/store/session/sagas";

export type Role = "ADMIN" | "MANAGER" | "RECRUITER" | "CANDIDATE";

export interface CurrentUser {
  username: string;
  role: Role;
  email_verified: boolean;
  assigned_institutions: string[];
}

interface AuthValue {
  user: CurrentUser | null;
  role: Role | null;
  isStaff: boolean;
  assignedInstitutions: string[];
  isLoading: boolean;
  signIn: () => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function isStaffRole(role: Role | null | undefined): boolean {
  return role === "ADMIN" || role === "MANAGER";
}

async function fetchCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await request<CurrentUser>("/auth/me/");
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null;
    throw error;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const dispatch = useDispatch();

  useEffect(forgetLegacyToken, []);

  const me = useQuery({
    queryKey: queryKeys.me(),
    queryFn: fetchCurrentUser,
    staleTime: Infinity,
    retry: false,
  });

  const signIn = useCallback(() => {
    dispatch(signedIn());
  }, [dispatch]);

  const signOut = useCallback(
    () =>
      new Promise<void>((resolve) => {
        dispatch(signOutRequested(resolve));
      }),
    [dispatch],
  );

  const value = useMemo<AuthValue>(() => {
    const user = me.data ?? null;
    return {
      user,
      role: user?.role ?? null,
      isStaff: isStaffRole(user?.role),
      assignedInstitutions: user?.assigned_institutions ?? [],
      isLoading: me.isLoading,
      signIn,
      signOut,
    };
  }, [me.data, me.isLoading, signIn, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return value;
}
