import { ExternalLink } from "lucide-react";
import { useTranslations } from "next-intl";
import { cx, inr } from "@/lib/format";
import type { PriceAdvice } from "@/lib/types";

/** PriceRangeBar: replica range (grey), handmade range (indigo gradient), the artisan's price marker
 *  (haldi), labels, and the example sources behind a tap (Part 1 §9.6). */
export function PriceRangeBar({ advice, price, compact }: { advice: PriceAdvice; price?: number | null; compact?: boolean }) {
  const t = useTranslations("price");
  const hand = advice.handmade;
  const rep = advice.replica;
  const p = price ?? advice.price_inr;
  if (!hand && !rep) {
    return <p className="rounded-sm bg-khadi-50 p-3 text-sm text-ink-600">{advice.message}</p>;
  }
  const values = [hand?.p25, hand?.p75, rep?.p25, rep?.p75, p].filter((v): v is number => typeof v === "number");
  const min = Math.min(...values) * 0.85;
  const max = Math.max(...values) * 1.1;
  const pos = (v: number) => `${Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100))}%`;
  const width = (a: number, b: number) => `${Math.max(2, ((b - a) / (max - min)) * 100)}%`;
  return (
    <div className="flex flex-col gap-3">
      <div className="relative h-14" role="img" aria-label={advice.message}>
        <div className="absolute inset-x-0 top-6 h-3 rounded-full bg-ink-100" />
        {rep && <div className="absolute top-6 h-3 rounded-full bg-unverified/50" style={{ insetInlineStart: pos(rep.p25), width: width(rep.p25, rep.p75) }} />}
        {hand && (
          <div
            className="absolute top-6 h-3 rounded-full bg-gradient-to-r from-brand to-brand-hover"
            style={{ insetInlineStart: pos(hand.p25), width: width(hand.p25, hand.p75) }}
          />
        )}
        {typeof p === "number" && (
          <div className="absolute top-0 flex -translate-x-1/2 flex-col items-center rtl:translate-x-1/2" style={{ insetInlineStart: pos(p) }}>
            <span className="rounded-md bg-gold-500 px-1.5 text-xs font-bold text-ink-900">{inr(p)}</span>
            <span className="h-8 w-1 rounded-full bg-gold-500" />
          </div>
        )}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-600">
        {hand && (
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-4 rounded-full bg-brand" /> {t("handmade_range", { low: inr(hand.p25), high: inr(hand.p75) })}
          </span>
        )}
        {rep && (
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-4 rounded-full bg-unverified/50" /> {t("replica_range", { low: inr(rep.p25), high: inr(rep.p75) })}
          </span>
        )}
      </div>
      {!compact && (
        <>
          <p className={cx("text-body-s", advice.position === "below" ? "text-ink-900" : "text-ink-600")}>{advice.message}</p>
          {advice.compare_message && <p className="rounded-sm bg-peacock-50 p-3 text-sm text-peacock-600">{advice.compare_message}</p>}
          {advice.sources.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer font-semibold text-brand">{t("sources", { n: advice.sources.length })}</summary>
              <ul className="mt-2 divide-y divide-ink-100 rounded-sm border border-ink-100 bg-white">
                {advice.sources.map((s, idx) => {
                  const fullUrl = s.url || s.site;
                  const href = fullUrl.startsWith("http://") || fullUrl.startsWith("https://") ? fullUrl : `https://${fullUrl}`;
                  return (
                    <li key={s.url || idx} className="flex items-center justify-between gap-3 px-3 py-2">
                      <div className="min-w-0 flex-1">
                        <a
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group inline-flex max-w-full items-center gap-1.5 font-medium text-brand hover:underline"
                          title={fullUrl}
                        >
                          <span className="truncate">{fullUrl}</span>
                          <ExternalLink className="size-3.5 shrink-0 text-brand group-hover:text-brand" />
                        </a>
                        {s.title && <span className="block truncate text-xs text-ink-600">{s.title}</span>}
                      </div>
                      <span className="shrink-0 font-semibold">{inr(s.price_inr)}</span>
                    </li>
                  );
                })}
              </ul>
              {advice.provider === "fake" && <p className="mt-2 text-xs text-ink-600">{t("demo_sources")}</p>}
            </details>
          )}
        </>
      )}
    </div>
  );
}
