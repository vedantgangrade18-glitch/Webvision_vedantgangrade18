"use client";

/** Browser API client: same-origin `/api/v1` (rewritten to the API), cookie auth, CSRF echo,
 *  one transparent refresh on `token_expired`, typed errors. */

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public details: Record<string, unknown> = {},
  ) {
    super(code);
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/[.$?*|{}()[\]\\/+^]/g, "\\$&") + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

let refreshing: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch("/api/v1/auth/refresh", { method: "POST", credentials: "same-origin" })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => setTimeout(() => (refreshing = null), 0));
  }
  return refreshing;
}

export interface ApiOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  form?: FormData;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export async function api<T = unknown>(path: string, opts: ApiOptions = {}, retried = false): Promise<T> {
  const method = opts.method || (opts.body || opts.form ? "POST" : "GET");
  const headers: Record<string, string> = { Accept: "application/json", ...(opts.headers || {}) };
  if (method !== "GET") {
    const csrf = readCookie("karu_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(`/api/v1${path}`, { method, headers, body, credentials: "same-origin", signal: opts.signal });
  if (res.status === 401 && !retried) {
    const err = await res.clone().json().catch(() => null);
    if (err?.error?.code === "token_expired" || err?.error?.code === "unauthorized") {
      if (await refresh()) return api<T>(path, opts, true);
    }
  }
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new ApiError(res.status, err?.error?.code || `http_${res.status}`, err?.error?.details || {});
  }
  const type = res.headers.get("content-type") || "";
  if (type.includes("application/json")) return (await res.json()) as T;
  return (await res.blob()) as unknown as T;
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, body?: unknown, headers?: Record<string, string>) =>
  api<T>(path, { method: "POST", body: body ?? {}, headers });
export const patch = <T,>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body });
export const put = <T,>(path: string, body: unknown) => api<T>(path, { method: "PUT", body });
export const del = <T,>(path: string) => api<T>(path, { method: "DELETE" });

export function errorKey(e: unknown): string {
  if (e instanceof ApiError) return e.code;
  if (typeof navigator !== "undefined" && !navigator.onLine) return "offline";
  return "unknown";
}
