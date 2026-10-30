import { revalidatePath } from "next/cache";
import { NextResponse, type NextRequest } from "next/server";

/** On-demand revalidation called by the API when a unit, listing or verification changes (Part 2 §9.4). */
export async function POST(req: NextRequest) {
  const secret = process.env.WEB_REVALIDATE_SECRET;
  if (!secret || req.headers.get("x-revalidate-secret") !== secret) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }
  const body = (await req.json().catch(() => ({}))) as { paths?: string[] };
  const paths = (body.paths || []).filter((p) => typeof p === "string" && /^\/(p|k|m)\/[A-Za-z0-9-]+$/.test(p)).slice(0, 200);
  for (const p of paths) revalidatePath(p);
  revalidatePath("/");
  return NextResponse.json({ ok: true, revalidated: paths.length });
}
