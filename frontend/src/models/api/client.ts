import type { ApiErrorBody } from "./types";

const LEGACY_TOKEN_KEY = "hejobs.token";
const CSRF_COOKIE = "csrftoken";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly body: ApiErrorBody | null;

  constructor(status: number, body: ApiErrorBody | null) {
    super(body?.detail ?? `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.code ?? "error";
    this.body = body;
  }

  get extra(): Record<string, unknown> {
    return this.body?.extra ?? {};
  }

  get fieldErrors(): Record<string, string[]> {
    return this.body?.errors ?? {};
  }

  get readableMessage(): string {
    const fields = Object.entries(this.fieldErrors);
    if (fields.length === 0) return this.message;

    return fields
      .map(([field, messages]) => {
        const text = messages.join(" ");
        return field === "non_field_errors" || field === "detail" ? text : `${label(field)}: ${text}`;
      })
      .join(" ");
  }
}

function label(field: string): string {
  const words = field.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function forgetLegacyToken(): void {
  try {
    globalThis.localStorage?.removeItem(LEGACY_TOKEN_KEY);
  } catch {
    // Storage is blocked, so there is nothing to remove.
  }
}

export function csrfToken(): string | null {
  const match = globalThis.document?.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE}=([^;]+)`));
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

export function apiHeaders(method: string): Record<string, string> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const csrf = csrfToken();
  if (!SAFE_METHODS.has(method.toUpperCase()) && csrf) headers["X-CSRFToken"] = csrf;
  return headers;
}

export const API_BASE = "/api";

export function urlOf(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers = apiHeaders(method);
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "same-origin",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  const payload: unknown = text ? safeParse(text) : null;

  if (!response.ok) {
    throw new ApiError(response.status, payload as ApiErrorBody | null);
  }
  return payload as T;
}

function stringifyParam(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function safeParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export function toQueryString(params: Record<string, unknown>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null && item !== "") {
          search.append(key, stringifyParam(item));
        }
      }
    } else {
      search.set(key, stringifyParam(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { credentials: "same-origin" });
  if (!response.ok) throw new ApiError(response.status, null);

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
