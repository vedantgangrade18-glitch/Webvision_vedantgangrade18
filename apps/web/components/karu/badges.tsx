"use client";

import { BadgeCheck, CircleDashed, Clock3, QrCode, ShieldOff, Sparkles } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Emblem } from "./ornaments";
import { cx } from "@/lib/format";
import type { ProofCheck, Stock, VerificationStatus } from "@/lib/types";

/** Wordmark: Centred or inline brand logo with Karu sun emblem and editorial typography. */
export function Wordmark({
  layout = "inline",
  tone = "dark",
  showTagline = true,
  className,
  light,
  href = "/sell",
}: {
  layout?: "centered" | "inline";
  tone?: "dark" | "light";
  showTagline?: boolean;
  className?: string;
  light?: boolean;
  href?: string | false;
}) {
  const isLight = light || tone === "light";
  const isCentered = layout === "centered";

  const content = (
    <>
      <Emblem
        size={isCentered ? 30 : 26}
        tone={isLight ? "gold" : "brand"}
        className="transition-transform duration-300 group-hover:scale-105"
      />
      <div className={cx("flex flex-col", isCentered ? "items-center" : "items-start")}>
        <span
          className={cx(
            "font-sans font-extrabold tracking-tight leading-none lowercase text-2xl",
            isLight ? "text-white" : "text-[#801452]"
          )}
        >
          meesho
        </span>
        {showTagline && (
          <span
            className={cx(
              "text-[10.5px] font-bold tracking-wider uppercase leading-tight mt-0.5",
              isLight ? "text-[#F43397]" : "text-[#801452]"
            )}
          >
            Supplier Hub
          </span>
        )}
      </div>
    </>
  );

  const classes = cx(
    "group inline-flex items-center select-none transition-opacity hover:opacity-90",
    isCentered ? "flex-col items-center text-center gap-1.5" : "flex-row items-center gap-3",
    className
  );

  if (href) {
    return (
      <Link href={href} className={classes}>
        {content}
      </Link>
    );
  }

  return <div className={classes}>{content}</div>;
}

/** VerifiedBadge: Pill (rounded-full). sm 24px (cards), lg 32px (PDP, /k). */
export function VerifiedBadge({
  status,
  size = "sm",
  overlay = false,
  className,
}: {
  status: VerificationStatus;
  size?: "sm" | "lg";
  overlay?: boolean;
  className?: string;
}) {
  const t = useTranslations("badge");
  const isLg = size === "lg";

  const sizeClasses = isLg
    ? "min-h-8 px-3.5 text-body-s gap-2"
    : "min-h-6 px-2.5 text-caption gap-1.5";

  if (status === "verified") {
    return (
      <span
        className={cx(
          "inline-flex items-center rounded-full font-semibold whitespace-nowrap shadow-xs transition-all",
          sizeClasses,
          overlay
            ? "bg-white/95 text-peacock-700 border border-peacock-600/30 backdrop-blur-md"
            : "bg-peacock-700 text-white border border-peacock-600/40",
          className
        )}
      >
        <BadgeCheck className={cx(isLg ? "size-4.5" : "size-3.5", "text-gold-500 shrink-0")} aria-hidden />
        <span>{t("verified")}</span>
      </span>
    );
  }

  if (status === "checking") {
    return (
      <span
        className={cx(
          "inline-flex items-center rounded-full font-medium whitespace-nowrap border border-line bg-surface-alt text-ink-800",
          sizeClasses,
          className
        )}
      >
        <Clock3 className={cx(isLg ? "size-4" : "size-3.5", "shrink-0")} aria-hidden />
        <span>{t("checking")}</span>
        <span className="inline-flex gap-0.5 ms-1" aria-hidden>
          <span className="size-1 animate-bounce rounded-full bg-current [animation-delay:-0.2s]" />
          <span className="size-1 animate-bounce rounded-full bg-current [animation-delay:-0.1s]" />
          <span className="size-1 animate-bounce rounded-full bg-current" />
        </span>
      </span>
    );
  }

  if (status === "revoked") {
    return (
      <span
        className={cx(
          "inline-flex items-center rounded-full font-medium whitespace-nowrap border border-ink-200 bg-ink-100 text-ink-900",
          sizeClasses,
          className
        )}
      >
        <ShieldOff className={cx(isLg ? "size-4" : "size-3.5", "text-danger-600 shrink-0")} aria-hidden />
        <span>{t("revoked")}</span>
      </span>
    );
  }

  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full font-medium whitespace-nowrap border border-line-strong bg-ink-100 text-ink-600",
        sizeClasses,
        className
      )}
    >
      <CircleDashed className={cx(isLg ? "size-4" : "size-3.5", "shrink-0")} aria-hidden />
      <span>{t("not_verified")}</span>
    </span>
  );
}

/** GiTag: Small zari-outlined tag for GI crafts. */
export function GiTag({ craft, className }: { craft: string; className?: string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-xs border border-gold-300 bg-gold-50 px-2 py-0.5 text-caption font-semibold text-gold-900 uppercase tracking-wider",
        className
      )}
    >
      <Sparkles className="size-3 text-gold-600 shrink-0" aria-hidden />
      <span>GI · {craft}</span>
    </span>
  );
}

/** ProductTag: Square tags on card corners (Mrittika 'New', 'Best Seller'). */
export function ProductTag({
  kind,
  label,
  className,
}: {
  kind: "new" | "low_stock" | "out" | "made_to_order";
  label?: string;
  className?: string;
}) {
  const kindConfig = {
    new: { text: label || "New Drop", classes: "bg-surface/95 text-text border-line" },
    low_stock: { text: label || "Low Stock", classes: "bg-terracotta-50 text-brand border-terracotta-200" },
    out: { text: label || "Sold Out", classes: "bg-surface text-muted border-line" },
    made_to_order: { text: label || "Made to Order", classes: "bg-gold-50 text-gold-900 border-gold-200" },
  }[kind];

  return (
    <span
      className={cx(
        "inline-flex items-center rounded-xs border px-2 py-0.5 text-caption font-semibold tracking-wider uppercase shadow-2xs backdrop-blur-xs",
        kindConfig.classes,
        className
      )}
    >
      {kindConfig.text}
    </span>
  );
}

/** StockPill: Text + dot on PDP ('● In stock · ships in 3 days'). */
export function StockPill({ stock, className }: { stock: Stock; className?: string }) {
  const t = useTranslations("stock");

  if (stock.state === "out") {
    return (
      <span className={cx("inline-flex items-center gap-1.5 text-body-s font-medium text-muted", className)}>
        <span className="size-2 rounded-full bg-ink-400 shrink-0" />
        <span>{t("out")}</span>
      </span>
    );
  }

  if (stock.state === "low") {
    return (
      <span className={cx("inline-flex items-center gap-1.5 text-body-s font-semibold text-brand", className)}>
        <span className="size-2 rounded-full bg-brand shrink-0" />
        <span>{t("low", { n: stock.count })}</span>
      </span>
    );
  }

  return (
    <span className={cx("inline-flex items-center gap-1.5 text-body-s font-medium text-peacock-700", className)}>
      <span className="size-2 rounded-full bg-peacock-600 shrink-0" />
      <span>{t("in")} · Ships directly from artisan cluster</span>
    </span>
  );
}

/** KaruIdChip: KRU-XXXX in hairline box with copy / link. */
export function KaruIdChip({ code, className }: { code: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  const copyCode = (e: React.MouseEvent) => {
    e.preventDefault();
    if (navigator.clipboard) {
      void navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Link
      href={`/k/${code}`}
      onClick={copyCode}
      title="Click to copy Karu ID, or open certificate"
      className={cx(
        "group inline-flex items-center gap-1.5 rounded-xs border border-line-strong bg-surface px-2.5 py-1 font-mono text-caption text-text transition-colors hover:border-brand hover:text-brand",
        className
      )}
    >
      <QrCode className="size-3.5 text-muted group-hover:text-brand shrink-0" />
      <span>{copied ? "COPIED ✓" : code}</span>
    </Link>
  );
}

/** ProofChecks: Verified checklist with human-readable check marks. */
export function ProofChecks({
  checks,
  photosOriginal,
  registry,
}: {
  checks: ProofCheck[];
  photosOriginal?: boolean | null;
  registry?: { kind: string; date: string }[];
}) {
  const t = useTranslations("proof");

  const icon = (state: ProofCheck["state"]) =>
    state === "passed" ? (
      <span className="flex size-5.5 items-center justify-center rounded-full bg-peacock-700 text-xs font-bold text-white shadow-2xs shrink-0">
        ✓
      </span>
    ) : state === "new_maker" ? (
      <span className="flex size-5.5 items-center justify-center rounded-full bg-gold-100 text-xs font-bold text-gold-700 shrink-0">
        ★
      </span>
    ) : (
      <span className="flex size-5.5 items-center justify-center rounded-full bg-sand-200 text-xs font-bold text-ink-600 shrink-0">
        –
      </span>
    );

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-3">
        {checks.map((c) => (
          <li key={c.key} className="flex items-start gap-3">
            {icon(c.state)}
            <span className="text-body-s font-medium text-text leading-tight pt-0.5">
              {t(`check.${c.key}.${c.state}`)}
            </span>
          </li>
        ))}
        {photosOriginal && (
          <li className="flex items-start gap-3">
            {icon("passed")}
            <span className="text-body-s font-medium text-text leading-tight pt-0.5">
              {t("photos_original")}
            </span>
          </li>
        )}
        {(registry || []).map((r) => (
          <li key={r.kind} className="flex items-start gap-3">
            {icon("passed")}
            <span className="text-body-s font-medium text-text leading-tight pt-0.5">
              {t(`registry.${r.kind}`, { date: r.date })}
            </span>
          </li>
        ))}
      </ul>
      <details className="group rounded-xs border border-line bg-surface-alt px-3.5 py-2.5 text-caption text-muted">
        <summary className="cursor-pointer font-semibold text-brand hover:text-brand-hover">
          {t("how_we_checked")}
        </summary>
        <ul className="mt-2 list-disc space-y-1.5 ps-5 text-muted">
          <li>{t("how.l1")}</li>
          <li>{t("how.l2")}</li>
          <li>{t("how.l3")}</li>
          <li>{t("how.no_scores")}</li>
        </ul>
      </details>
    </div>
  );
}

export { Woven } from "./ornaments";
