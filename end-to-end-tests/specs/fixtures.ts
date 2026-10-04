import { test as base, expect, request as apiRequest } from "@playwright/test";
import type { Cookie, Page } from "@playwright/test";

export const API = process.env.E2E_API_URL ?? "http://localhost:8000";
const PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password";

export const CANDIDATE = "e2e-candidate";
export const ADMIN = "e2e-admin";

const cachedTokens = new Map<string, Promise<string>>();

export function fetchToken(username: string = CANDIDATE): Promise<string> {
  let token = cachedTokens.get(username);
  if (!token) {
    token = requestToken(username);
    cachedTokens.set(username, token);
  }
  return token;
}

async function requestToken(username: string): Promise<string> {
  const response = await fetch(`${API}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password: PASSWORD }),
  });
  if (!response.ok) {
    throw new Error(
      `Could not sign in as ${username} (HTTP ${response.status}). Create the test users ` +
        `first: manage.py seed_test_users`,
    );
  }
  const body = (await response.json()) as { token: string };
  return body.token;
}

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";
const cachedSessions = new Map<string, Promise<Cookie[]>>();

function sessionCookies(username: string): Promise<Cookie[]> {
  let cookies = cachedSessions.get(username);
  if (!cookies) {
    cookies = (async () => {
      const context = await apiRequest.newContext({ baseURL: BASE_URL });
      const response = await context.post("/api/auth/login/", {
        data: { username, password: PASSWORD, session: true },
      });
      if (!response.ok()) {
        throw new Error(
          `Could not start a session as ${username} (HTTP ${response.status()}). ` +
            "Create the test users first: manage.py seed_test_users",
        );
      }
      const state = await context.storageState();
      await context.dispose();
      return state.cookies;
    })();
    cachedSessions.set(username, cookies);
  }
  return cookies;
}

export async function signIn(page: Page, username: string): Promise<void> {
  await page.context().addCookies(await sessionCookies(username));
}

export const test = base.extend<{ authedPage: Page; adminPage: Page }>({
  authedPage: async ({ page }, use) => {
    await signIn(page, CANDIDATE);
    await use(page);
  },
  adminPage: async ({ page }, use) => {
    await signIn(page, ADMIN);
    await use(page);
  },
});

export { expect };
