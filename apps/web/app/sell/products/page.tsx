"use client";

import { useQuery } from "@tanstack/react-query";
import { Package, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useState } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { StockPill, VerifiedBadge } from "@/components/karu/badges";
import { Button } from "@/components/ui/button";
import { FilterChip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/empty-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { inr } from "@/lib/format";
import type { ImageSet, Stock, VerificationStatus } from "@/lib/types";

interface MyListing {
  id: string;
  code: string;
  status: string;
  title: string;
  price_inr: number | null;
  image: ImageSet | null;
  stock: Stock;
  quantity_total: number;
  verification: VerificationStatus;
  price_position: "below" | "in_range" | "above" | "unknown";
}

export default function SellProductsPage() {
  return (
    <Suspense>
      <AuthGate require="artisan">{() => <ProductsView />}</AuthGate>
    </Suspense>
  );
}

function ProductsView() {
  const t = useTranslations("sell.products");
  const tNav = useTranslations("sell.nav");
  const params = useSearchParams();
  const [filter, setFilter] = useState<string>(params.get("filter") || "all");
  const [search, setSearch] = useState<string>("");

  const listings = useQuery({
    queryKey: ["my-listings"],
    queryFn: () => api<{ items: MyListing[] }>("/listings/mine"),
  });

  const allItems = listings.data?.items || [];

  const filteredItems = allItems.filter((l) => {
    // Search match
    if (search.trim()) {
      const q = search.toLowerCase();
      const match =
        (l.title && l.title.toLowerCase().includes(q)) ||
        (l.code && l.code.toLowerCase().includes(q));
      if (!match) return false;
    }

    // Filter status match
    if (filter === "all") return true;
    if (filter === "not_verified") return l.verification !== "verified" && l.status === "published";
    if (filter === "drafts") return l.status === "draft" || l.status === "processing";
    return l.status === filter;
  });

  const countByFilter = {
    all: allItems.length,
    published: allItems.filter((l) => l.status === "published").length,
    not_verified: allItems.filter((l) => l.verification !== "verified" && l.status === "published").length,
    drafts: allItems.filter((l) => l.status === "draft" || l.status === "processing").length,
    paused: allItems.filter((l) => l.status === "paused").length,
  };

  return (
    <SellPage
      title={
        <div className="flex flex-col gap-1">
          <span className="text-eyebrow text-brand">Artisan Catalogue</span>
          <h1 className="font-serif text-h1 text-ink-900">{t("title") || "Workshop Products"}</h1>
        </div>
      }
      back="/sell"
    >
      <div className="flex flex-col gap-6">
        {/* Top Control Bar: Search + New Product Button */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 size-4 text-muted" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by piece title or code…"
              className="w-full rounded-xs border border-line bg-surface ps-9 pe-4 py-2.5 text-body-s text-ink-900 placeholder:text-muted focus:border-brand focus:outline-none"
            />
          </div>

          <Link href="/sell/new" className="shrink-0">
            <Button variant="primary" size="M" icon={<Plus className="size-4" />}>
              {tNav("new_product") || "New Product"}
            </Button>
          </Link>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-2">
          {[
            { id: "all", label: `${t("filter_all") || "All Pieces"} (${countByFilter.all})` },
            { id: "published", label: `${t("filter_published") || "Live & Listed"} (${countByFilter.published})` },
            { id: "not_verified", label: `${t("filter_not_verified") || "Verification Pending"} (${countByFilter.not_verified})` },
            { id: "drafts", label: `${t("filter_drafts") || "Drafts"} (${countByFilter.drafts})` },
            { id: "paused", label: `${t("filter_paused") || "Paused"} (${countByFilter.paused})` },
          ].map((f) => (
            <FilterChip key={f.id} selected={filter === f.id} onClick={() => setFilter(f.id)}>
              {f.label}
            </FilterChip>
          ))}
        </div>

        {/* Products List */}
        <div className="rounded-sm border border-line bg-surface p-4 sm:p-6 shadow-xs">
          {listings.isLoading ? (
            <div className="flex flex-col gap-3">
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : !filteredItems.length ? (
            <EmptyState
              art="loom"
              title={t("empty_title") || "No pieces in this view"}
              description={t("empty_body") || "Photograph a finished piece on your workbench to list it across India."}
              action={
                <Link href="/sell/new">
                  <Button variant="primary" size="M" icon={<Plus className="size-4" />}>
                    {t("add_first") || "List your first piece"}
                  </Button>
                </Link>
              }
            />
          ) : (
            <div className="flex flex-col divide-y divide-line">
              {filteredItems.map((l) => (
                <article key={l.id} className="py-4 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                  <div className="flex items-center gap-4 min-w-0 flex-1">
                    <Link
                      href={
                        l.status === "draft" || l.status === "processing"
                          ? `/sell/new?listing=${l.id}`
                          : `/sell/products/${l.id}`
                      }
                      className="size-20 shrink-0 overflow-hidden rounded-xs border border-line bg-sand-100"
                    >
                      {l.image?.thumb ? (
                        <img src={l.image.thumb} alt="" className="size-full object-cover" />
                      ) : (
                        <div className="flex size-full items-center justify-center text-caption text-muted italic">
                          <Package className="size-6 text-muted" />
                        </div>
                      )}
                    </Link>

                    <div className="min-w-0 flex-1 flex flex-col gap-1">
                      <Link
                        href={
                          l.status === "draft" || l.status === "processing"
                            ? `/sell/new?listing=${l.id}`
                            : `/sell/products/${l.id}`
                        }
                        className="font-serif text-body font-medium text-ink-900 truncate hover:text-brand"
                      >
                        {l.title || "Untitled handcrafted piece"}
                      </Link>

                      <div className="flex items-center gap-3 text-body-s">
                        <span className="font-semibold text-ink-900">{inr(l.price_inr)}</span>
                        <span className="font-mono text-caption text-muted">ID: {l.code}</span>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        {l.status === "published" || l.status === "paused" ? (
                          <VerifiedBadge status={l.verification} />
                        ) : (
                          <span className="rounded-full bg-surface-alt px-2.5 py-0.5 text-caption font-medium text-muted capitalize">
                            {l.status}
                          </span>
                        )}
                        {l.status === "published" && <StockPill stock={l.stock} />}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    <Link
                      href={
                        l.status === "draft" || l.status === "processing"
                          ? `/sell/new?listing=${l.id}`
                          : `/sell/products/${l.id}`
                      }
                    >
                      <Button variant="secondary" size="S">
                        {t("manage") || "Manage Piece"}
                      </Button>
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </SellPage>
  );
}
