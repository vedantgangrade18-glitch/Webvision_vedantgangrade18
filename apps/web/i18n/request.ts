import { cookies, headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { LOCALE_COOKIE, isLocale, negotiate, type Locale } from "./config";

type Messages = Record<string, unknown>;

function deepMerge(base: Messages, override: Messages): Messages {
  const out: Messages = { ...base };
  for (const [k, v] of Object.entries(override)) {
    const b = base[k];
    out[k] = v && typeof v === "object" && !Array.isArray(v) && b && typeof b === "object" ? deepMerge(b as Messages, v as Messages) : v;
  }
  return out;
}

export async function resolveLocale(): Promise<Locale> {
  // Locale comes from the cookie, then Accept-Language, then English (Part 2 §9.4). URLs stay locale-free
  // so QR codes and shared links never change.
  const cookie = (await cookies()).get(LOCALE_COOKIE)?.value;
  if (isLocale(cookie)) return cookie;
  return negotiate((await headers()).get("accept-language"));
}

export default getRequestConfig(async () => {
  const locale = await resolveLocale();
  const en = (await import("../messages/en.json")).default as Messages;
  // Locales other than en/hi are machine-assisted; English fills any gap so the UI never shows keys.
  const messages = locale === "en" ? en : deepMerge(en, (await import(`../messages/${locale}.json`)).default as Messages);
  return { locale, messages, timeZone: "Asia/Kolkata" };
});
