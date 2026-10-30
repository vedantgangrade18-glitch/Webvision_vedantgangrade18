"use client";

import { ChevronLeft, ChevronRight, Heart, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { ProductTag, VerifiedBadge } from "./badges";
import { api } from "@/lib/api";
import { cx, inr } from "@/lib/format";
import { useMe } from "@/lib/hooks";
import type { Card } from "@/lib/types";

export interface ProductCardProps {
  card: Card;
  variant?: "grid" | "rail" | "editorial" | "row" | "mini";
  priority?: boolean;
  className?: string;
}

/** ProductCard: Editorial craft card respecting Mrittika & Terra & Soul design guidelines. */
export function ProductCard({
  card,
  variant = "grid",
  priority = false,
  className,
}: ProductCardProps) {
  const t = useTranslations("card");
  const router = useRouter();
  const { data: me } = useMe();
  const [wished, setWished] = useState(card.wishlisted);

  const toggleWishlist = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!me) {
      router.push(`/login?next=${encodeURIComponent(window.location.pathname)}`);
      return;
    }
    const next = !wished;
    setWished(next);
    try {
      await api(`/wishlist/${card.id}`, { method: next ? "POST" : "DELETE" });
    } catch {
      setWished(!next);
    }
  };

  const handleQuickAdd = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!me) {
      router.push(`/login?next=${encodeURIComponent(`/p/${card.code}`)}`);
      return;
    }
    try {
      await api("/cart/items", { method: "POST", body: { listing_id: card.id, qty: 1 } });
      router.push("/cart");
    } catch {
      router.push(`/p/${card.code}`);
    }
  };

  // Mini variant for search hits / recently viewed
  if (variant === "mini") {
    return (
      <Link
        href={`/p/${card.code}`}
        className={cx("group flex items-center gap-3 rounded-xs p-2 transition-colors hover:bg-surface-alt", className)}
      >
        <div className="relative aspect-[4/5] size-16 shrink-0 overflow-hidden rounded-xs bg-sand-100">
          {card.image?.thumb && (
            <img src={card.image.thumb} alt={card.title} className="size-full object-cover" loading="lazy" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-caption text-muted truncate">{card.maker.name}</p>
          <h4 className="font-serif text-body-s font-medium text-text truncate group-hover:text-brand">{card.title}</h4>
          <p className="text-body-s font-semibold tabular-nums text-text">{inr(card.price_inr)}</p>
        </div>
      </Link>
    );
  }

  // Row variant for Cart / Wishlist / Orders
  if (variant === "row") {
    return (
      <div className={cx("flex items-center gap-4 py-4 border-b border-line last:border-b-0", className)}>
        <Link href={`/p/${card.code}`} className="relative aspect-[4/5] w-20 sm:w-24 shrink-0 overflow-hidden rounded-sm bg-sand-100">
          {card.image?.card && (
            <img src={card.image.card} alt={card.title} className="size-full object-cover" loading="lazy" />
          )}
        </Link>
        <div className="min-w-0 flex-1 flex flex-col gap-1">
          <p className="text-caption text-muted uppercase tracking-wider">{card.maker.name} · {card.maker.place}</p>
          <Link href={`/p/${card.code}`} className="font-serif text-body font-medium text-text hover:text-brand truncate">
            {card.title}
          </Link>
          <div className="flex items-center gap-2 mt-0.5">
            <VerifiedBadge status={card.verification === "verified" ? "verified" : "not_verified"} size="sm" />
            {card.stock.state === "low" && <ProductTag kind="low_stock" />}
          </div>
          <p className="font-semibold tabular-nums text-body text-text mt-1">{inr(card.price_inr)}</p>
        </div>
      </div>
    );
  }

  // Editorial large variant
  if (variant === "editorial") {
    return (
      <Link
        href={`/p/${card.code}`}
        className={cx("group relative block aspect-[3/4] overflow-hidden rounded-sm bg-sand-100", className)}
      >
        {card.image?.large && (
          <img
            src={card.image.large}
            alt={card.title}
            className="size-full object-cover transition-transform duration-700 ease-out group-hover:scale-104"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
        <div className="absolute inset-x-5 bottom-5 flex flex-col gap-1 text-white">
          <p className="text-caption uppercase tracking-wider text-sand-200">{card.maker.name} · {card.maker.place}</p>
          <h3 className="font-serif text-xl sm:text-2xl font-medium leading-snug">{card.title}</h3>
          <p className="text-body font-semibold tabular-nums">{inr(card.price_inr)}</p>
        </div>
      </Link>
    );
  }

  // Standard Grid and Rail variants (Mrittika style with bordered panel on desktop)
  return (
    <Link
      href={`/p/${card.code}`}
      className={cx(
        "group flex flex-col overflow-hidden rounded-sm transition-all focus-visible:outline-none",
        variant === "grid" ? "border border-line/60 bg-surface hover:border-line-strong hover:shadow-2xs" : "",
        className
      )}
    >
      {/* 4:5 Aspect Ratio Photo Frame */}
      <div className="relative aspect-[4/5] w-full overflow-hidden bg-sand-100">
        {card.image?.card ? (
          <img
            src={card.image.card}
            alt={card.title}
            loading={priority ? "eager" : "lazy"}
            className="size-full object-cover transition-transform duration-500 ease-out group-hover:scale-103"
          />
        ) : (
          <div className="flex size-full items-center justify-center font-serif text-caption text-muted italic">
            Handcrafted Piece
          </div>
        )}

        {/* Top-Start: Product Tag if Low Stock / New / Sold Out */}
        <div className="absolute start-2.5 top-2.5 z-10 flex flex-col gap-1">
          {card.stock.state === "out" ? (
            <ProductTag kind="out" />
          ) : card.stock.state === "low" ? (
            <ProductTag kind="low_stock" />
          ) : null}
        </div>

        {/* Top-End: Wishlist Button */}
        <button
          type="button"
          onClick={toggleWishlist}
          aria-label={wished ? t("unwish") : t("wish")}
          className="absolute end-2.5 top-2.5 z-10 flex size-9 items-center justify-center rounded-full bg-surface/90 text-text shadow-2xs backdrop-blur-md transition-all hover:bg-surface hover:scale-105 active:scale-95"
        >
          <Heart
            className={cx(
              "size-4 transition-colors",
              wished ? "fill-brand text-brand" : "text-muted hover:text-text"
            )}
          />
        </button>

        {/* Bottom-Start: Verified Badge Overlay */}
        <div className="absolute bottom-2.5 start-2.5 z-10">
          <VerifiedBadge
            status={card.verification === "verified" ? "verified" : "not_verified"}
            overlay
          />
        </div>
      </div>

      {/* Info Panel: Maker eyebrow -> Title -> Price + Quick Action (+) */}
      <div className={cx("flex flex-col gap-1 p-3.5", variant === "rail" && "px-1 pt-2")}>
        <p className="text-caption font-medium uppercase tracking-wider text-muted truncate">
          {card.maker.name}
          {card.maker.place ? ` · ${card.maker.place}` : ""}
        </p>

        <h3
          className="font-serif text-body-s sm:text-body font-medium leading-snug text-text line-clamp-2 min-h-[2.6em] group-hover:text-brand transition-colors"
        >
          {card.title}
        </h3>

        <div className="mt-1 flex items-center justify-between pt-1 border-t border-line/60">
          <p className="text-body font-semibold tabular-nums text-text">
            {inr(card.price_inr)}
          </p>

          {/* Quick Add Button (+) */}
          <button
            type="button"
            onClick={handleQuickAdd}
            aria-label={`Add ${card.title} to bag`}
            className="flex size-7.5 items-center justify-center rounded-full border border-line bg-surface-alt text-text transition-colors group-hover:bg-brand group-hover:text-white group-hover:border-brand cursor-pointer"
          >
            <Plus className="size-3.5" />
          </button>
        </div>
      </div>
    </Link>
  );
}

/** ProductGrid: Responsive 2-col mobile up to 5-col desktop grid with density support. */
export function ProductGrid({
  cards,
  columns = 4,
  className,
}: {
  cards: Card[];
  columns?: 2 | 3 | 4 | 5;
  className?: string;
}) {
  const colClass =
    columns === 3
      ? "grid-cols-2 sm:grid-cols-3 lg:grid-cols-3"
      : columns === 5
      ? "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5"
      : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4";

  return (
    <div className={cx("grid gap-4 sm:gap-6", colClass, className)}>
      {cards.map((card, i) => (
        <ProductCard key={card.id} card={card} priority={i < 4} />
      ))}
    </div>
  );
}

/** ProductRail: Snap carousel with visible desktop prev/next controls. */
export function ProductRail({ cards }: { cards: Card[] }) {
  const railRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: "left" | "right") => {
    if (!railRef.current) return;
    const offset = direction === "left" ? -320 : 320;
    railRef.current.scrollBy({ left: offset, behavior: "smooth" });
  };

  return (
    <div className="relative group/rail">
      {/* Desktop Prev Button */}
      <button
        type="button"
        onClick={() => scroll("left")}
        aria-label="Scroll left"
        className="hidden lg:flex absolute start-0 top-1/2 -translate-y-1/2 -translate-x-4 z-20 size-10 items-center justify-center rounded-full border border-line bg-surface text-text shadow-sm transition-opacity opacity-0 group-hover/rail:opacity-100 hover:bg-surface-alt cursor-pointer"
      >
        <ChevronLeft className="size-5 flip-rtl" />
      </button>

      {/* Rail Container */}
      <div
        ref={railRef}
        tabIndex={0}
        aria-roledescription="carousel"
        className="no-scrollbar -mx-4 flex snap-x gap-4 overflow-x-auto px-4 py-2 pb-6 sm:-mx-6 sm:px-6 md:mx-0 md:px-0 focus-visible:outline-none"
      >
        {cards.map((c) => (
          <div key={c.id} className="w-44 shrink-0 snap-start sm:w-56 md:w-60">
            <ProductCard card={c} variant="rail" />
          </div>
        ))}
      </div>

      {/* Desktop Next Button */}
      <button
        type="button"
        onClick={() => scroll("right")}
        aria-label="Scroll right"
        className="hidden lg:flex absolute end-0 top-1/2 -translate-y-1/2 translate-x-4 z-20 size-10 items-center justify-center rounded-full border border-line bg-surface text-text shadow-sm transition-opacity opacity-0 group-hover/rail:opacity-100 hover:bg-surface-alt cursor-pointer"
      >
        <ChevronRight className="size-5 flip-rtl" />
      </button>
    </div>
  );
}
