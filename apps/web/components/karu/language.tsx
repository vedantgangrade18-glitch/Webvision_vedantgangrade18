"use client";

import { Check, ChevronDown, Globe, Volume2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { LOCALE_COOKIE, languageNames, locales, speechTags, type Locale } from "@/i18n/config";
import { api } from "@/lib/api";
import { cx } from "@/lib/format";
import { speak } from "@/lib/speech";

export async function setLocale(locale: Locale, signedIn: boolean) {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=${365 * 86400}; samesite=lax`;
  if (signedIn) {
    try {
      await api("/me", { method: "PATCH", body: { locale } });
    } catch {
      /* cookie alone is enough for the UI */
    }
  }
}

export interface LanguageSwitcherProps {
  signedIn?: boolean;
  variant?: "default" | "dark" | "compact";
  className?: string;
}

/** Header language switcher (artisan header / buyer header + footer). */
export function LanguageSwitcher({
  signedIn = false,
  variant = "default",
  className,
}: LanguageSwitcherProps) {
  const locale = useLocale() as Locale;
  const t = useTranslations("common");

  const variantStyles = {
    dark: "border border-white/20 bg-white/10 text-white hover:bg-white/15",
    compact: "border border-line bg-surface text-ink-900 text-caption py-0.5 px-2",
    default: "border border-line/80 bg-surface text-text hover:border-brand shadow-2xs py-1 px-2.5 text-caption",
  }[variant];

  return (
    <label
      className={cx(
        "relative inline-flex items-center gap-1.5 rounded-xs transition-colors cursor-pointer select-none",
        variantStyles,
        className
      )}
    >
      <Globe className={cx("size-3.5 shrink-0", variant === "dark" ? "text-gold-300" : "text-muted")} aria-hidden />
      <span className="sr-only">{t("language")}</span>
      <select
        value={locale}
        onChange={async (e) => {
          const next = e.target.value as Locale;
          await setLocale(next, signedIn);
          window.location.reload();
        }}
        className="appearance-none bg-transparent font-medium cursor-pointer focus:outline-none pe-4 text-inherit"
      >
        {locales.map((l) => (
          <option key={l} value={l} className="bg-white text-ink-900">
            {languageNames[l].native} ({languageNames[l].english})
          </option>
        ))}
      </select>
      <ChevronDown
        className={cx("pointer-events-none absolute end-1.5 top-1/2 -translate-y-1/2 size-3", variant === "dark" ? "text-white/60" : "text-muted")}
        aria-hidden
      />
    </label>
  );
}

/** A01: big tiles, name in its own script + English; tapping plays a greeting in that language. */
export function LanguageTiles({ onPick, signedIn }: { onPick: (l: Locale) => void; signedIn: boolean }) {
  const current = useLocale() as Locale;
  const [chosen, setChosen] = useState<Locale | null>(null);
  return (
    <div className="grid grid-cols-2 gap-3">
      {locales.map((l) => (
        <button
          key={l}
          type="button"
          lang={l}
          dir={l === "ur" ? "rtl" : "ltr"}
          onClick={async () => {
            setChosen(l);
            speak(languageNames[l].greeting, speechTags[l]);
            await setLocale(l, signedIn);
            onPick(l);
          }}
          className={cx(
            "flex min-h-24 flex-col items-start justify-between rounded-md border-2 bg-white p-4 text-start transition-colors",
            (chosen || current) === l ? "border-brand bg-brand-soft" : "border-ink-100 hover:border-brand/40",
          )}
        >
          <span className="flex w-full items-center justify-between">
            <span className="text-2xl font-semibold text-ink-900">{languageNames[l].native}</span>
            {(chosen || current) === l ? <Check className="size-5 text-brand" /> : <Volume2 className="size-5 text-ink-300" />}
          </span>
          <span className="text-sm text-ink-600" lang="en" dir="ltr">
            {languageNames[l].english}
          </span>
        </button>
      ))}
    </div>
  );
}
