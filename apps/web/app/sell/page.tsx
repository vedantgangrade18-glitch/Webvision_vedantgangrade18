"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { StockPill, VerifiedBadge } from "@/components/karu/badges";
import { SpeakerButton } from "@/components/karu/voice";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { FilterChip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/empty-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { StatTile } from "@/components/ui/stat-tile";
import { speechTags, type Locale } from "@/i18n/config";
import { api } from "@/lib/api";
import { cx, inr } from "@/lib/format";
import { db, onOutboxChange, retryItem, type OutboxItem } from "@/lib/offline";
import { speak } from "@/lib/speech";
import type { ImageSet, Stock, VerificationStatus } from "@/lib/types";

interface Dashboard {
  greeting_name: string;
  summary: { views_today: number; orders_to_ship: number; money_on_the_way: string };
  banners: { key: string; count?: number; amount?: string; link: string }[];
  open_requests: number;
  profile_completion: number;
  profile_missing: string[];
  passport: { code: string; state: string };
  impact: { earned: string; pieces_sold: number; buyer_cities: number };
}

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

export default function SellHome() {
  return (
    <Suspense>
      <AuthGate require="artisan">{() => <Home />}</AuthGate>
    </Suspense>
  );
}

function Home() {
  const t = useTranslations("sell.home");
  const locale = useLocale() as Locale;
  const params = useSearchParams();
  const router = useRouter();
  const [filter, setFilter] = useState<string>(params.get("filter") || "all");
  const dash = useQuery({ queryKey: ["sell-dashboard"], queryFn: () => api<Dashboard>("/artisan/dashboard") });
  const listings = useQuery({ queryKey: ["my-listings"], queryFn: () => api<{ items: MyListing[] }>("/listings/mine") });
  const [drafts, setDrafts] = useState<OutboxItem[]>([]);
  const [hideCompletion, setHideCompletion] = useState(true);

  useEffect(() => {
    const load = () => void db().outbox.where("status").anyOf("pending", "uploading", "failed").toArray().then(setDrafts);
    load();
    return onOutboxChange(load);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reading session dismissal on mount
    setHideCompletion(sessionStorage.getItem("karu:completion-dismissed") === "1");
  }, []);

  useEffect(() => {
    if (params.get("welcome") === "1") {
      speak([t("tour_1"), t("tour_2"), t("tour_3")].join(" "), speechTags[locale]);
      router.replace("/sell");
    }
  }, [params, router, t, locale]);

  const d = dash.data;
  const items = (listings.data?.items || []).filter((l) =>
    filter === "all"
      ? true
      : filter === "not_verified"
      ? l.verification !== "verified" && l.status === "published"
      : filter === "drafts"
      ? l.status === "draft" || l.status === "processing"
      : l.status === filter
  );

  return (
    <SellPage>
      {/* Top Header: Greeting, Date, and Speaker */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-4 mb-6">
        <div>
          <span className="text-eyebrow text-brand">{locale === "hi" ? "मास्टर कारीगर स्टूडियो" : "Master Artisan Studio"}</span>
          <h1 className="font-serif text-h1 text-ink-900 mt-1">
            {t("greeting")} {d?.greeting_name || (locale === "hi" ? "कारीगर" : "Artisan")}
          </h1>
          <p className="text-caption text-muted mt-0.5">
            {new Date().toLocaleDateString(locale, { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
        <SpeakerButton
          text={t("speak_summary", {
            orders: d?.summary.orders_to_ship ?? 0,
            money: d?.summary.money_on_the_way ?? "",
          })}
        />
      </div>

      {/* 3 Main StatTiles */}
      {dash.isLoading ? (
        <CardSkeleton />
      ) : d ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-6">
          <StatTile
            label={t("views_today") || "Views Today"}
            value={d.summary.views_today}
            delta={locale === "hi" ? "+12% कल से" : "+12% from yesterday"}
          />
          <StatTile
            label={t("to_ship") || "Orders To Ship"}
            value={d.summary.orders_to_ship}
            delta={d.summary.orders_to_ship > 0 ? (locale === "hi" ? "जल्द डिस्पैच करें" : "Express dispatch needed") : (locale === "hi" ? "सभी पैक हैं" : "All packed")}
          />
          <StatTile
            label={t("on_the_way") || "Money on the Way"}
            value={d.summary.money_on_the_way}
            delta={locale === "hi" ? "सीधे बैंक खाते में" : "Direct transfer to bank"}
          />
        </div>
      ) : null}

      {/* Action Banners */}
      {d?.banners.map((b) => (
        <div key={b.key} className="mb-4">
          <Link href={b.link}>
            <Banner
              tone={b.key === "orders_to_ship" ? "warn" : "info"}
              action={<span className="flip-rtl text-body font-semibold">View →</span>}
            >
              {t(`banner.${b.key}`, { n: b.count ?? 0, amount: b.amount ?? "" }) || "Action required"}
            </Banner>
          </Link>
        </div>
      ))}

      {/* 8/4 Desktop Layout */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-start mt-6">
        {/* Start Column: 8 cols Products Management */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {/* Drafts Waiting on Phone */}
          {drafts.length > 0 && (
            <section className="rounded-sm border border-line bg-surface p-4 shadow-xs flex flex-col gap-3">
              <h3 className="font-medium text-body-s text-ink-900">{t("saved_on_phone") || "Drafts saved on phone"}</h3>
              {drafts.map((dr) => (
                <div
                  key={dr.id}
                  className="flex items-center justify-between gap-3 rounded-xs border border-dashed border-line bg-surface-alt p-3 text-body-s"
                >
                  <span className="text-muted">
                    {t(dr.status === "failed" ? "draft_failed" : "draft_waiting", { n: dr.photos.length })}
                  </span>
                  {dr.status === "failed" && (
                    <Button size="S" variant="secondary" onClick={() => void retryItem(dr.id!)}>
                      {t("retry") || "Retry upload"}
                    </Button>
                  )}
                </div>
              ))}
            </section>
          )}

          {/* Products List & Status Filter Pills */}
          <section className="rounded-sm border border-line bg-surface p-6 shadow-xs flex flex-col gap-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
              <h2 className="font-serif text-h3 text-ink-900">
                {t("products") || "Workshop Products"}
              </h2>
              <Link href="/sell/new">
                <Button variant="primary" size="M" icon={<Plus className="size-4" />}>
                  {t("new") || "New Product"}
                </Button>
              </Link>
            </div>

            {/* Filter Pills */}
            <div className="flex flex-wrap gap-2">
              {["all", "published", "not_verified", "drafts", "paused"].map((f) => (
                <FilterChip key={f} selected={filter === f} onClick={() => setFilter(f)}>
                  {t(`filter.${f}`) || f.replace("_", " ")}
                </FilterChip>
              ))}
            </div>

            {/* Product Items */}
            {listings.isLoading ? (
              <div className="flex flex-col gap-3">
                <CardSkeleton />
                <CardSkeleton />
              </div>
            ) : !items.length ? (
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
                {items.map((l) => (
                  <article key={l.id} className="py-4 flex gap-4 items-center">
                    <Link
                      href={
                        l.status === "draft" || l.status === "processing"
                          ? `/sell/new?listing=${l.id}`
                          : `/sell/products/${l.id}`
                      }
                      className="size-20 shrink-0 overflow-hidden rounded-xs border border-line bg-sand-100"
                    >
                      {l.image?.thumb && (
                        <img src={l.image.thumb} alt="" className="size-full object-cover" />
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
                        {l.title || t("untitled") || "Untitled handcraft piece"}
                      </Link>

                      <div className="flex items-center gap-3 text-body-s">
                        <span className="font-semibold text-ink-900">{inr(l.price_inr)}</span>
                        <PriceDot position={l.price_position} />
                      </div>

                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        {l.status === "published" || l.status === "paused" ? (
                          <VerifiedBadge status={l.verification} />
                        ) : (
                          <span className="rounded-full bg-surface-alt px-2 py-0.5 text-caption font-medium text-muted capitalize">
                            {t(`status.${l.status}`) || l.status}
                          </span>
                        )}
                        {l.status === "published" && <StockPill stock={l.stock} />}
                      </div>
                    </div>

                    <Link
                      href={
                        l.status === "draft" || l.status === "processing"
                          ? `/sell/new?listing=${l.id}`
                          : `/sell/products/${l.id}`
                      }
                    >
                      <Button variant="secondary" size="S">
                        {locale === "hi" ? "प्रबंधन" : "Manage"}
                      </Button>
                    </Link>
                  </article>
                ))}
              </div>
            )}
            {items.length > 0 && (
              <div className="pt-3 border-t border-line flex justify-end">
                <Link
                  href="/sell/products"
                  className="inline-flex items-center gap-1 text-caption font-semibold text-brand hover:underline"
                >
                  <span>{locale === "hi" ? "सभी कार्यशाला उत्पाद देखें →" : "View All Workshop Products →"}</span>
                </Link>
              </div>
            )}
          </section>
        </div>

        {/* End Column: 4 cols Sidebar (Passport, Completion, Impact) */}
        <aside className="lg:col-span-4 flex flex-col gap-5 lg:sticky lg:top-24">
          {/* Profile Completion Card */}
          {d && d.profile_completion < 100 && !hideCompletion && (
            <div className="rounded-sm border border-line bg-surface p-5 shadow-xs flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <ShieldCheck className="size-4 text-brand" />
                  <span className="text-body-s font-semibold text-ink-900">
                    {t("completion", { pct: d.profile_completion }) || `Profile ${d.profile_completion}% Complete`}
                  </span>
                </div>
                {d.profile_missing[0] && (
                  <Link href="/sell/passport" className="text-caption font-medium text-brand underline underline-offset-4">
                    {t(`missing.${d.profile_missing[0]}`) || "Add Aadhaar / Artisan Pehchan card to unlock verified stamp"}
                  </Link>
                )}
              </div>
              <button
                type="button"
                className="text-muted hover:text-ink-900 p-1"
                aria-label={t("dismiss") || "Dismiss"}
                onClick={() => {
                  sessionStorage.setItem("karu:completion-dismissed", "1");
                  setHideCompletion(true);
                }}
              >
                <X className="size-4" />
              </button>
            </div>
          )}

          {/* Mini Impact Card */}
          {d && (
            <div className="rounded-sm border border-line bg-surface-deep p-6 text-khadi-100 shadow-xs flex flex-col gap-3">
              <span className="text-eyebrow text-gold-300">Lifetime Earnings</span>
              <p className="font-serif text-3xl font-medium text-white">{d.impact.earned}</p>
              <p className="text-caption text-sand-200">
                {t("impact_line", { pieces: d.impact.pieces_sold, cities: d.impact.buyer_cities }) ||
                  `${d.impact.pieces_sold} pieces delivered to patrons across ${d.impact.buyer_cities} cities`}
              </p>
              <div className="pt-2 border-t border-white/10 flex justify-between items-center text-caption text-gold-300">
                <span>Direct Maker Payouts</span>
                <Link href="/sell/payouts" className="underline hover:text-white">
                  Payout History →
                </Link>
              </div>
            </div>
          )}
        </aside>
      </div>
    </SellPage>
  );
}

function PriceDot({ position }: { position: MyListing["price_position"] }) {
  const t = useTranslations("sell.home");
  const color =
    position === "in_range"
      ? "bg-verified"
      : position === "below"
      ? "bg-gold-500"
      : position === "above"
      ? "bg-brand"
      : "bg-sand-300";

  return (
    <span className="inline-flex items-center gap-1.5 text-caption text-muted">
      <span className={cx("size-2 rounded-full", color)} aria-hidden />
      <span>{t(`price.${position}`) || position.replace("_", " ")}</span>
    </span>
  );
}
