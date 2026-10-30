"use client";

import { BadgeCheck, Download, ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { date } from "@/lib/format";
import type { Maker } from "@/lib/types";

/** PassportCard: luxury-label style, zari woven border, arch frame, canvas export (Part 1 §9.6 / B07). */
export function PassportCard({
  maker,
  locale,
  exportable,
  compact = false,
  tone = "olive",
}: {
  maker: Maker;
  locale: string;
  exportable?: boolean;
  compact?: boolean;
  tone?: "olive" | "terracotta";
}) {
  const t = useTranslations("passport");
  const verified = maker.passport.state === "verified";
  const bgClass = tone === "olive" ? "bg-surface-deep text-khadi-100" : "bg-terracotta-900 text-khadi-100";

  const download = async () => {
    const W = 1080;
    const H = 640;
    const c = document.createElement("canvas");
    c.width = W;
    c.height = H;
    const ctx = c.getContext("2d")!;
    ctx.fillStyle = tone === "olive" ? "#1E251E" : "#5A2210";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "#FAF7F2";
    ctx.fillRect(24, 24, W - 48, H - 48);
    for (let x = 24; x < W - 24; x += 14) {
      ctx.fillStyle = (x / 14) % 2 ? "#D4A338" : "#8C3B1E";
      ctx.fillRect(x, 24, 8, 6);
      ctx.fillRect(x, H - 30, 8, 6);
    }
    ctx.fillStyle = "#8C3B1E";
    ctx.font = "600 44px Georgia, serif";
    ctx.fillText("karu", 64, 100);
    ctx.font = "600 22px sans-serif";
    ctx.fillStyle = "#7A736B";
    ctx.fillText(t("title").toUpperCase(), 64, 140);
    if (maker.photo_url) {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.src = maker.photo_url;
      await new Promise((r) => {
        img.onload = r;
        img.onerror = r;
      });
      if (img.complete && img.naturalWidth) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(170, 330, 110, 0, Math.PI * 2);
        ctx.clip();
        ctx.drawImage(img, 60, 220, 220, 220);
        ctx.restore();
      }
    }
    ctx.fillStyle = "#1E1A16";
    ctx.font = "600 52px Georgia, serif";
    ctx.fillText(maker.name, 330, 290);
    ctx.font = "26px sans-serif";
    ctx.fillStyle = "#7A736B";
    ctx.fillText(maker.place, 330, 336);
    ctx.fillText(t("member_since", { date: date(maker.passport.member_since, locale) }), 330, 380);
    ctx.font = "600 30px monospace";
    ctx.fillStyle = "#8C3B1E";
    ctx.fillText(maker.passport.code || "", 330, 440);
    ctx.fillStyle = verified ? "#0E6E60" : "#7A736B";
    ctx.beginPath();
    ctx.roundRect(330, 480, verified ? 330 : 360, 56, 28);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.font = "600 26px sans-serif";
    ctx.fillText(verified ? t("state.verified") : t("state.unverified"), 356, 517);
    const a = document.createElement("a");
    a.href = c.toDataURL("image/png");
    a.download = `karu-passport-${maker.passport.code}.png`;
    a.click();
  };

  return (
    <div className={`relative overflow-hidden rounded-sm p-1 shadow-lift ${bgClass}`}>
      <div className="rounded-xs border border-gold-500/40 bg-surface p-5 text-ink-900">
        <div className="flex items-start justify-between gap-3 border-b border-line pb-3">
          <div>
            <span className="font-serif text-xl font-medium tracking-wide text-brand">karu</span>
            <p className="text-caption font-semibold uppercase tracking-[0.2em] text-muted">{t("title")}</p>
          </div>
          {verified ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-verified-soft px-2.5 py-1 text-xs font-semibold text-verified">
              <BadgeCheck className="size-3.5 text-gold-600" /> {t("state.verified")}
            </span>
          ) : maker.passport.state === "suspended" ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-danger-100 px-2.5 py-1 text-xs font-semibold text-danger">
              <ShieldAlert className="size-3.5" /> {t("state.suspended")}
            </span>
          ) : (
            <span className="rounded-full bg-sand-200 px-2.5 py-1 text-xs font-medium text-subtle">
              {t("state.unverified")}
            </span>
          )}
        </div>

        <div className="mt-4 flex items-center gap-4">
          <div className="relative shrink-0">
            {maker.photo_url ? (
              <div className="h-20 w-16 overflow-hidden rounded-t-full border border-gold-500/50 bg-sand-200 shadow-xs">
                <img src={maker.photo_url} alt={maker.name} className="h-full w-full object-cover" />
              </div>
            ) : (
              <div className="flex h-20 w-16 items-center justify-center rounded-t-full border border-gold-500/50 bg-sand-200 text-lg font-serif font-medium text-brand">
                {maker.name.slice(0, 2).toUpperCase()}
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="font-serif text-lg font-medium tracking-tight text-ink-900 truncate">{maker.name}</h4>
            <p className="text-xs text-muted truncate">{maker.place}</p>
            {maker.crafts.length > 0 && <p className="text-xs text-brand truncate mt-0.5">{maker.crafts.join(" · ")}</p>}
          </div>
        </div>

        <div className={`mt-4 grid grid-cols-2 gap-3 border-t border-dashed border-line pt-3 ${compact ? "text-xs" : "text-sm"}`}>
          <div>
            <p className="text-caption uppercase tracking-wider text-muted">{t("id")}</p>
            <p className="font-mono font-semibold text-brand text-xs mt-0.5">{maker.passport.code || "—"}</p>
          </div>
          <div>
            <p className="text-caption uppercase tracking-wider text-muted">{t("since")}</p>
            <p className="font-medium text-ink-900 text-xs mt-0.5">{date(maker.passport.member_since, locale)}</p>
          </div>
          {maker.stats && (
            <>
              <div>
                <p className="text-caption uppercase tracking-wider text-muted">{t("verified_pieces")}</p>
                <p className="font-semibold text-ink-900 text-xs mt-0.5">{maker.stats.verified_products}</p>
              </div>
              <div>
                <p className="text-caption uppercase tracking-wider text-muted">{t("rating")}</p>
                <p className="font-semibold text-ink-900 text-xs mt-0.5">
                  {maker.stats.rating ? `${maker.stats.rating} ★ (${maker.stats.reviews})` : "—"}
                </p>
              </div>
            </>
          )}
        </div>

        {exportable && (
          <div className="mt-4 pt-2 border-t border-line">
            <Button variant="secondary" size="S" block onClick={download} icon={<Download className="size-3.5" />}>
              {t("save_image")}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
