"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Download, Image as ImageIcon, MessageCircle, Pause, Play, Printer, QrCode, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, use, useState } from "react";
import { MakingVideoPicker } from "@/components/artisan/publish";
import { ReviewStep, useListing, type ArtisanListing } from "@/components/artisan/review";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { StockPill, VerifiedBadge } from "@/components/karu/badges";
import { PriceRangeBar } from "@/components/karu/price-range-bar";
import { useToast } from "@/components/toast";
import { Banner, Button, Card, Sheet, Skeleton, Stepper, Tabs } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { cx, date, inr, timeAgo } from "@/lib/format";
import { useJob, usePublicConfig } from "@/lib/hooks";
import type { PriceAdvice } from "@/lib/types";

type Tab = "overview" | "price" | "verification" | "edit" | "stock" | "share" | "more";

export default function ManageProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <Suspense>
      <AuthGate require="artisan">{() => <Manage id={id} />}</AuthGate>
    </Suspense>
  );
}

function Manage({ id }: { id: string }) {
  const t = useTranslations("sell.product");
  const params = useSearchParams();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>((params.get("tab") as Tab) || "overview");
  const { data: l, isLoading, refetch } = useListing(id);
  if (isLoading || !l) return <SellPage><Skeleton className="h-96" /></SellPage>;
  const title = l.title[l.source_lang] || l.title.en || "";
  return (
    <SellPage title={title} back="/sell/products">
      <div className="flex flex-wrap items-center gap-2">
        <VerifiedBadge status={l.verification_status as never} />
        <StockPill stock={{ state: l.quantity_available <= 0 ? "out" : l.quantity_available <= 3 ? "low" : "in", count: l.quantity_available }} />
        {l.status === "paused" && <span className="rounded-full bg-ink-100 px-2 py-0.5 text-xs font-semibold">{t("paused")}</span>}
      </div>
      <Tabs
        value={tab}
        onChange={(v) => {
          setTab(v);
          router.replace(`/sell/products/${id}?tab=${v}`, { scroll: false });
        }}
        tabs={(["overview", "price", "verification", "edit", "stock", "share", "more"] as Tab[]).map((v) => ({ value: v, label: t(`tab.${v}`) }))}
      />
      {tab === "overview" && <Overview l={l} />}
      {tab === "price" && <PriceTab l={l} />}
      {tab === "verification" && <VerificationTab l={l} onChange={() => refetch()} />}
      {tab === "edit" && <ReviewStep listing={l} onNext={() => { void refetch(); setTab("overview"); }} />}
      {tab === "stock" && <StockTab l={l} onChange={() => refetch()} />}
      {tab === "share" && <ShareTab l={l} />}
      {tab === "more" && <MoreTab l={l} onChange={() => refetch()} />}
    </SellPage>
  );
}

function Overview({ l }: { l: ArtisanListing }) {
  const t = useTranslations("sell.product");
  return (
    <div className="flex flex-col gap-4">
      <div className="no-scrollbar flex gap-2 overflow-x-auto">
        {l.gallery.map((g) => g.card && <img key={g.id} src={g.card} alt="" className="aspect-[4/5] w-36 shrink-0 rounded-sm object-cover" />)}
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label={t("price")} value={inr(l.price_inr)} />
        <Stat label={t("in_stock")} value={String(l.quantity_available)} />
        <Stat label={t("views")} value={String(l.views)} />
        <Stat label={t("sold")} value={String(l.sales.units)} />
      </div>
      <Card className="p-4">
        <p className="text-sm text-ink-600">{t("revenue")}</p>
        <p className="text-2xl font-semibold">{inr(l.sales.revenue_inr)}</p>
        <p className="text-sm text-ink-600">{t("zero_commission")}</p>
      </Card>
      <div className="inline-flex items-center gap-1 text-caption text-muted">
        <span>Product Code: <strong className="font-mono text-ink-900">{l.code}</strong></span>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-ink-100 bg-white p-3">
      <p className="text-xs text-ink-600">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  );
}

function PriceTab({ l }: { l: ArtisanListing }) {
  const t = useTranslations("sell.product");
  const tf = useTranslations();
  const qc = useQueryClient();
  const toast = useToast();
  const { data, isLoading } = useQuery({ queryKey: ["advice", l.id], queryFn: () => api<PriceAdvice>(`/listings/${l.id}/price-advice`) });
  if (isLoading) return <Skeleton className="h-40" />;
  if (!data || data.status === "none") return <p className="text-ink-600">{t("no_advice")}</p>;
  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-4 p-4">
        <PriceRangeBar advice={data} />
        {data.updated_at && <p className="text-xs text-ink-600">{t("updated", { ago: timeAgo(data.updated_at, (k, v) => tf(`common.${k}`, v)) })}</p>}
      </Card>
      {data.suggested_inr && data.suggested_inr !== data.price_inr && (
        <Button
          size="L"
          onClick={async () => {
            await api(`/listings/${l.id}/price-advice/accept`, { method: "POST", body: { price_inr: data.suggested_inr } });
            await qc.invalidateQueries({ queryKey: ["advice", l.id] });
            await qc.invalidateQueries({ queryKey: ["listing", l.id] });
            toast(t("price_updated"));
          }}
        >
          {t("use_price", { price: inr(data.suggested_inr) })}
        </Button>
      )}
      <p className="text-sm text-ink-600">{t("you_decide")}</p>
    </div>
  );
}

/** A12: three-layer stepper with status + tips (never numbers), video, result, try again. */
function VerificationTab({ l, onChange }: { l: ArtisanListing; onChange: () => void }) {
  const t = useTranslations("sell.verify");
  const locale = useLocale();
  const toast = useToast();
  const { data, refetch } = useQuery({
    queryKey: ["verification", l.id],
    queryFn: () =>
      api<{ status: string; has_video: boolean; run: { status: string; verdict: string | null; layers: Record<string, string>; hard_fail: boolean; tips: { key: string; text: string }[]; completed_at: string | null } | null }>(
        `/listings/${l.id}/verification`,
      ),
    refetchInterval: (q) => (q.state.data?.status === "checking" ? 5000 : false),
  });
  if (!data) return <Skeleton className="h-64" />;
  const layer = (k: "L1" | "L2" | "L3") => {
    const s = data.run?.layers?.[k];
    if (data.status === "checking") return "current" as const;
    if (s === "ok") return "done" as const;
    if (s === "needs_work" || s === "missing" || s === "under_review") return "warn" as const;
    return "todo" as const;
  };
  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col items-start gap-3 p-4">
        <VerifiedBadge status={data.status as never} size="lg" />
        {data.status === "checking" && <p className="text-body-s text-ink-600">{t("checking")}</p>}
        {data.status === "verified" && <p className="text-body-s text-peacock-600">{t("verified_body", { date: date(data.run?.completed_at, locale) })}</p>}
        {data.run?.hard_fail && <Banner tone="info">{t("under_review")}</Banner>}
      </Card>
      <Card className="p-4">
        <Stepper
          steps={[
            { label: t("l1"), state: layer("L1"), detail: t(`l1_${data.run?.layers?.L1 || "pending"}`) },
            { label: t("l2"), state: layer("L2"), detail: t(`l2_${data.run?.layers?.L2 || "pending"}`) },
            { label: t("l3"), state: data.has_video ? layer("L3") : "warn", detail: data.has_video ? t(`l3_${data.run?.layers?.L3 || "pending"}`) : t("l3_missing") },
          ]}
        />
      </Card>
      {data.status !== "verified" && data.status !== "checking" && data.run && data.run.tips.length > 0 && (
        <Card className="flex flex-col gap-2 p-4">
          <h3 className="font-semibold">{t("whats_missing")}</h3>
          <ul className="flex flex-col gap-2">
            {data.run.tips.map((tip) => (
              <li key={tip.key} className="flex gap-2 text-body-s">
                <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-gold-100 text-sm font-bold">!</span>
                <span>
                  {tip.text}
                  {tip.key === "tip.verify_aadhaar" && (
                    <Link href="/sell/passport" className="ms-2 font-semibold text-brand underline">{t("go")}</Link>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {data.status !== "checking" && (
        <Card className="flex flex-col gap-3 p-4">
          <h3 className="font-semibold">{data.has_video ? t("replace_video") : t("add_video")}</h3>
          <MakingVideoPicker
            listingId={l.id}
            onAttached={() => {
              toast(t("video_received"));
              void refetch();
              onChange();
            }}
          />
        </Card>
      )}
      {data.status === "not_verified" && data.has_video && (
        <Button
          size="L"
          variant="secondary"
          onClick={async () => {
            try {
              await api(`/listings/${l.id}/verify`, { method: "POST" });
              void refetch();
              onChange();
            } catch (e) {
              toast(e instanceof ApiError ? t(`errors.${e.code === "already_checking" ? e.code : "generic"}`) : t("errors.generic"), "error");
            }
          }}
        >
          {t("try_again")}
        </Button>
      )}
    </div>
  );
}

function StockTab({ l, onChange }: { l: ArtisanListing; onChange: () => void }) {
  const t = useTranslations("sell.product");
  const toast = useToast();
  const [add, setAdd] = useState(1);
  const { data, refetch } = useQuery({
    queryKey: ["karu-ids", l.id],
    queryFn: () => api<{ items: { code: string; status: string; verified: boolean; url: string; sold_at: string | null }[] }>(`/listings/${l.id}/karu-ids`),
  });
  return (
    <div className="flex flex-col gap-4">
      <Card className="flex items-center gap-3 p-4">
        <span className="flex-1 font-semibold">{t("add_stock")}</span>
        <input type="number" min={1} max={500} value={add} onChange={(e) => setAdd(Math.max(1, Number(e.target.value)))} className="min-h-12 w-20 rounded-xs border border-ink-300 px-3 text-center text-lg" aria-label={t("add_stock")} />
        <Button
          onClick={async () => {
            await api(`/listings/${l.id}/stock`, { method: "POST", body: { add } });
            toast(t("ids_created", { n: add }));
            void refetch();
            onChange();
          }}
        >
          {t("add")}
        </Button>
      </Card>
      <a href={`/api/v1/listings/${l.id}/tags.pdf`} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-sm border-2 border-brand font-semibold text-brand">
        <Printer className="size-5" /> {t("print_tags")}
      </a>
      <ul className="divide-y divide-ink-100 rounded-sm border border-ink-100 bg-white">
        {data?.items.map((k) => (
          <li key={k.code} className="flex items-center gap-3 px-4 py-3">
            <QrCode className="size-5 text-brand" />
            <span className="flex-1 font-mono font-semibold">{k.code}</span>
            <span className={cx("rounded-full px-2 py-0.5 text-xs font-semibold", k.status === "available" ? "bg-peacock-50 text-peacock-600" : k.status === "sold" ? "bg-brand-soft text-brand" : "bg-ink-100 text-ink-600")}>
              {t(`unit.${k.status}`)}
            </span>
            {k.status === "returned" && (
              <Button
                size="S"
                variant="tertiary"
                onClick={async () => {
                  await api(`/artisan/karu-ids/${k.code}/relist`, { method: "POST" });
                  void refetch();
                  onChange();
                }}
              >
                {t("relist")}
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** A19: format chooser (WhatsApp status 9:16, Instagram 4:5, link, clean image), preview, native share. */
function ShareTab({ l }: { l: ArtisanListing }) {
  const t = useTranslations("sell.share");
  const locale = useLocale();
  const toast = useToast();
  const [format, setFormat] = useState<"9x16" | "4x5" | "clean">("4x5");
  const [res, setRes] = useState<{ image_url: string; caption: string; url: string; whatsapp_url: string } | null>(null);
  const [busy, setBusy] = useState(false);
  if (l.status !== "published" && l.status !== "paused") return <p className="text-ink-600">{t("publish_first")}</p>;
  const make = async (f: typeof format) => {
    setFormat(f);
    setBusy(true);
    try {
      setRes(await api(`/listings/${l.id}/share-image`, { method: "POST", body: { format: f, locale } }));
    } finally {
      setBusy(false);
    }
  };
  const shareNative = async () => {
    if (!res) return;
    try {
      const blob = await (await fetch(res.image_url)).blob();
      const file = new File([blob], `karu-${l.code}.jpg`, { type: "image/jpeg" });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], text: res.caption });
        return;
      }
    } catch {
      /* fall through to WhatsApp link */
    }
    window.open(res.whatsapp_url, "_blank", "noopener");
  };
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-2">
        {(["9x16", "4x5", "clean"] as const).map((f) => (
          <button key={f} onClick={() => void make(f)} className={cx("flex min-h-20 flex-col items-center justify-center gap-1 rounded-sm border-2 bg-white p-2 text-sm font-semibold", format === f && res ? "border-brand" : "border-ink-100")}>
            {f === "clean" ? <ImageIcon className="size-6" /> : <span className={cx("rounded-sm border-2 border-current", f === "9x16" ? "h-7 w-4" : "h-6 w-5")} />}
            {t(`format.${f}`)}
          </button>
        ))}
      </div>
      {busy && <Skeleton className="aspect-[4/5]" />}
      {res && !busy && (
        <>
          <img src={res.image_url} alt={t("preview")} className="mx-auto max-h-[60vh] rounded-sm shadow" />
          {format === "clean" && <Banner tone="info">{t("clean_note")}</Banner>}
          <Button size="L" icon={<MessageCircle className="size-5" />} onClick={() => void shareNative()}>{t("share_whatsapp")}</Button>
          <a href={res.image_url} download className="inline-flex min-h-12 items-center justify-center gap-2 rounded-sm border-2 border-brand font-semibold text-brand">
            <Download className="size-5" /> {t("download")}
          </a>
          <p className="text-sm text-ink-600">{t("instagram_hint")}</p>
        </>
      )}
      <Card className="flex items-center gap-2 p-3">
        <span className="flex-1 truncate font-mono text-sm">{l.share_url}</span>
        <Button
          size="S"
          variant="secondary"
          icon={<Copy className="size-4" />}
          onClick={async () => {
            await navigator.clipboard.writeText(l.share_url);
            toast(t("copied"));
          }}
        >
          {t("copy")}
        </Button>
      </Card>
    </div>
  );
}

function MoreTab({ l, onChange }: { l: ArtisanListing; onChange: () => void }) {
  const t = useTranslations("sell.product");
  const router = useRouter();
  const { data: config } = usePublicConfig();
  const [confirm, setConfirm] = useState(false);
  const [syndication, setSyndication] = useState<{ id: string; job: string } | null>(null);
  return (
    <div className="flex flex-col gap-3">
      {l.status === "published" ? (
        <Button variant="secondary" size="L" icon={<Pause className="size-5" />} onClick={async () => { await api(`/listings/${l.id}/pause`, { method: "POST" }); onChange(); }}>
          {t("pause")}
        </Button>
      ) : l.status === "paused" ? (
        <Button variant="secondary" size="L" icon={<Play className="size-5" />} onClick={async () => { await api(`/listings/${l.id}/resume`, { method: "POST" }); onChange(); }}>
          {t("resume")}
        </Button>
      ) : null}
      <p className="text-sm text-ink-600">{t("pause_note")}</p>
      {config?.flags["syndication.demo"] && l.status === "published" && (
        <Card className="flex flex-col gap-3 p-4">
          <h3 className="font-semibold">{t("syndicate_title")}</h3>
          <p className="text-sm text-ink-600">{t("syndicate_body")}</p>
          <div className="flex flex-wrap gap-2">
            {(["ondc", "indiamart", "coop"] as const).map((p) => (
              <Button
                key={p}
                size="S"
                variant="secondary"
                onClick={async () => {
                  const r = await api<{ syndication_id: string; job_id: string }>(`/listings/${l.id}/syndicate`, { method: "POST", body: { portal: p } });
                  setSyndication({ id: r.syndication_id, job: r.job_id });
                }}
              >
                {t(`portal.${p}`)}
              </Button>
            ))}
          </div>
        </Card>
      )}
      <Button variant="danger" size="L" icon={<Trash2 className="size-5" />} onClick={() => setConfirm(true)}>{t("delete")}</Button>
      <Sheet open={confirm} onClose={() => setConfirm(false)} title={t("delete")}>
        <p className="mb-4">{t("delete_confirm")}</p>
        <Button variant="danger" block onClick={async () => { await api(`/listings/${l.id}`, { method: "DELETE" }); router.replace("/sell"); }}>
          {t("delete_yes")}
        </Button>
      </Sheet>
      {syndication && <SyndicationProgress syndicationId={syndication.id} jobId={syndication.job} onClose={() => setSyndication(null)} />}
    </div>
  );
}

/** A20 [DEMO]: live TinyFish agent progress. */
function SyndicationProgress({ syndicationId, jobId, onClose }: { syndicationId: string; jobId: string; onClose: () => void }) {
  const t = useTranslations("sell.product");
  const job = useJob(jobId);
  const { data } = useQuery({
    queryKey: ["syndication", syndicationId, job?.status, job?.progress],
    queryFn: () => api<{ status: string; steps: { step: string; kind: string }[]; result_url: string | null; streaming_url: string | null; portal_name: string }>(`/syndication/${syndicationId}`),
  });
  return (
    <Sheet open onClose={onClose} title={data?.portal_name || t("syndicate_title")}>
      <div className="flex flex-col gap-3">
        <div className="h-2 overflow-hidden rounded-full bg-ink-100"><div className="h-full bg-brand transition-all" style={{ width: `${job?.progress ?? 5}%` }} /></div>
        <ol className="flex flex-col gap-1.5">
          {(data?.steps || []).map((s, i) => (
            <li key={i} className={cx("text-body-s", s.kind === "error" ? "text-danger-600" : "text-ink-900")}>✓ {s.step}</li>
          ))}
        </ol>
        {data?.streaming_url && <a href={data.streaming_url} target="_blank" rel="noreferrer" className="font-semibold text-brand underline">{t("watch_live")}</a>}
        {data?.status === "completed" && data.result_url && (
          <Banner tone="success" action={<a href={data.result_url} target="_blank" rel="noreferrer" className="font-semibold underline">{t("open")}</a>}>{t("syndicated")}</Banner>
        )}
        {data?.status === "failed" && <Banner tone="danger">{t("syndication_failed")}</Banner>}
      </div>
    </Sheet>
  );
}
