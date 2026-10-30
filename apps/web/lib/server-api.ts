import { cookies } from "next/headers";
import { getLocale } from "next-intl/server";

const API = process.env.API_INTERNAL_URL || "http://localhost:8000";

export class ServerApiError extends Error {
  constructor(public status: number, public code: string) {
    super(code);
  }
}

interface Opts {
  /** Forward the viewer's cookies (personalised data, never cached). */
  auth?: boolean;
  /** ISR-style cache window for public data (seconds). */
  revalidate?: number;
  tags?: string[];
}

/** Server-side fetch to the API. Locale travels as a query param so cached entries are per-locale. */
export async function serverApi<T>(path: string, opts: Opts = {}): Promise<T> {
  const locale = await getLocale();
  const sep = path.includes("?") ? "&" : "?";
  const url = `${API}/api/v1${path}${sep}locale=${locale}`;
  const headers: Record<string, string> = { Accept: "application/json", "Accept-Language": locale };
  if (opts.auth) headers.cookie = (await cookies()).toString();
  const res = await fetch(url, {
    headers,
    ...(opts.auth ? { cache: "no-store" as const } : { next: { revalidate: opts.revalidate ?? 60, tags: opts.tags } }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ServerApiError(res.status, body?.error?.code || `http_${res.status}`);
  }
  return (await res.json()) as T;
}

export async function serverApiOrNull<T>(path: string, opts: Opts = {}): Promise<T | null> {
  try {
    return await serverApi<T>(path, opts);
  } catch (e) {
    if (e instanceof ServerApiError && (e.status === 404 || e.status === 410 || e.status === 401)) return null;
    throw e;
  }
}

export async function currentUser() {
  const jar = await cookies();
  if (!jar.get("karu_at") && !jar.get("karu_rt")) return null;
  return serverApiOrNull<import("./types").Me>("/me", { auth: true });
}
