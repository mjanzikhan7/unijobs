import { request } from "@/models/api/client";

export async function signInWithPassword(username: string, password: string): Promise<void> {
  await request("/auth/login/", { method: "POST", body: { username, password, session: true } });
}

export async function registerAccount(fields: {
  username: string;
  email: string;
  password: string;
}): Promise<void> {
  await request("/auth/register/", { method: "POST", body: fields });
}

export async function verifyEmail(token: string | undefined): Promise<void> {
  await request("/auth/verify-email/", { method: "POST", body: { token } });
}

export async function confirmEmailChange(token: string | undefined): Promise<void> {
  await request("/account/confirm-email/", { method: "POST", body: { token } });
}

export async function requestPasswordReset(email: string): Promise<void> {
  await request("/auth/password-reset/", { method: "POST", body: { email } });
}

export async function confirmPasswordReset(fields: {
  uid: string | undefined;
  token: string | undefined;
  password: string;
}): Promise<void> {
  await request("/auth/password-reset/confirm/", { method: "POST", body: fields });
}
