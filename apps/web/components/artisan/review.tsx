"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Pencil, Plus, RefreshCw, Sparkles, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState, type ReactNode } from "react";
import { PriceRangeBar } from "@/components/karu/price-range-bar";
import { MicButton } from "@/components/karu/voice";
import { useToast } from "@/components/toast";
import { Banner, Button, Input, Select, Skeleton, Spinner, Textarea } from "@/components/ui";
import { languageNames, type Locale } from "@/i18n/config";
import { ApiError, api } from "@/lib/api";
import { cx, inr } from "@/lib/format";
import { useJob } from "@/lib/hooks";
import type { ImageSet, PriceAdvice } from "@/lib/types";

export interface ArtisanListing {
  id: string;
  code: string;
  status: string;
  source_lang: string;
  title: Record<string, string>;
  description: Record<string, string>;
  attributes: Record<string, unknown>;
  tags: string[];
  price_inr: number | null;
  category_slug: string | null;
  craft_slug: string | null;
  returnable: boolean;
  quantity_total: number;
  quantity_available: number;
  verification_status: string;
  price_position: string;
  field_confidence: Record<string, number>;
  missing_fields: string[];
  notes_for_artisan: string[];
  transcript: string | null;
  transcript_provider: string | null;
  extraction_status: string | null;
  processing: { job_id: string; status: string; progress: number; step: string | null } | null;
  shots_job_id?: string | null;
  gallery: (ImageSet & { is_primary: boolean; enhanced: boolean; original_id: string; ai?: boolean; role?: string })[];
  making_video: { id: string; duration_s: number | null; poster: string | null } | null;
  views: number;
  shares: number;
  sales: { units: number; revenue_inr: number };
  share_url: string;
  published_at: string | null;
  regenerate_left: number;
}

/** A field spec from Category.attribute_schema (the server owns which fields apply and what counts as missing). */
interface FieldSpec { key: string; type: "string" | "number" | "integer" | "array"; tier: "core" | "badge" | "optional" }
interface CategoryItem { slug: string; name: string; attribute_schema?: { fields?: FieldSpec[] } }

const getPath = (o: Record<string, unknown>, path: string): unknown =>
  path.split(".").reduce<unknown>((cur, k) => (cur && typeof cur === "object" ? (cur as Record<string, unknown>)[k] : undefined), o);
const setPath = (o: Record<string, unknown>, path: string, value: unknown): Record<string, unknown> => {
  const [head, ...rest] = path.split(".");
  const child = o[head] && typeof o[head] === "object" && !Array.isArray(o[head]) ? (o[head] as Record<string, unknown>) : {};
  return { ...o, [head]: rest.length ? setPath(child, rest.join("."), value) : value };
};
const filled = (v: unknown) => v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && v.length === 0);
// Typed text is kept as-is (lists as "red, blue"); the server splits, types and nests on save.
const fromInput = (type: FieldSpec["type"], text: string) => (type === "number" || type === "integer" ? text.replace(/[^\d.]/g, "") : type === "array" ? text.replace(/،/g, ",") : text);

export function useListing(id: string | null) {
  return useQuery({ queryKey: ["listing", id], queryFn: () => api<ArtisanListing>(`/listings/${id}`), enabled: !!id });
}

interface Preview { transcript?: string; category_slug?: string | null; price_inr?: number | null; material?: string | null; title?: string | null }

/** A07b: "Karu is listening…" with live job steps; partial results show up as each step lands. */
export function Processing({ jobId, onDone }: { jobId: string; onDone: () => void }) {
  const t = useTranslations("sell.new");
  const tr = useTranslations("sell.review");
  const job = useJob(jobId, (j) => j.status === "completed" || j.status === "failed" ? onDone() : undefined);
  const { data: cats } = useQuery({ queryKey: ["categories"], queryFn: () => api<{ items: { slug: string; name: string }[] }>("/catalog/categories") });
  const steps = ["listening", "understanding", "writing"];
  const current = job?.step ? steps.indexOf(job.step) : 0;
  const preview = (job?.result?.preview ?? {}) as Preview;
  const category = cats?.items.find((c) => c.slug === preview.category_slug)?.name;
  const chips = [category, preview.price_inr ? inr(preview.price_inr) : null, preview.material].filter(Boolean) as string[];
  return (
    <section className="flex flex-col items-center gap-6 py-10 text-center">
      <div className="relative flex size-32 items-center justify-center">
        <span className="animate-pulse-ring absolute inset-0 rounded-full bg-brand/10" />
        <span className="flex size-24 items-center justify-center rounded-full bg-brand text-white">
          <Sparkles className="size-10" />
        </span>
      </div>
      <h1 className="font-display text-h2">{t("listening")}</h1>
      <ol className="flex w-full max-w-xs flex-col gap-2 text-start">
        {steps.map((s, i) => (
          <li key={s} className={cx("flex items-center gap-3 text-body-s", i < current ? "text-peacock-600" : i === current ? "font-semibold text-ink-900" : "text-ink-300")}>
            <span className="flex size-6 items-center justify-center">{i < current ? "✓" : i === current ? <Spinner className="size-5" /> : "•"}</span>
            {t(`step.${s}`)}
          </li>
        ))}
      </ol>
      <div className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-ink-100">
        <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${job?.progress ?? 5}%` }} />
      </div>
      {(preview.transcript || chips.length > 0 || preview.title) && (
        <div className="flex w-full max-w-sm flex-col gap-3 rounded-md bg-white p-4 text-start shadow-soft" aria-live="polite">
          {preview.transcript && (
            <div className="animate-settle">
              <p className="text-xs font-semibold text-ink-600">{tr("what_you_said")}</p>
              <p className="line-clamp-3 text-body-s italic text-ink-900">“{preview.transcript}”</p>
            </div>
          )}
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {chips.map((c) => <span key={c} className="animate-settle rounded-full bg-brand-soft px-3 py-1 text-sm font-medium text-brand">{c}</span>)}
            </div>
          )}
          {preview.title && <p className="animate-settle font-display text-lg leading-snug">{preview.title}</p>}
        </div>
      )}
      <p className="text-sm text-ink-600">{t("usually_20s")}</p>
    </section>
  );
}

/** A08: one page of cards; each card has ✏️ edit, 🎤 speak, 🔄 regenerate. Low-confidence fields highlighted. */
export function ReviewStep({ listing, onNext }: { listing: ArtisanListing; onNext: () => void }) {
  const t = useTranslations("sell.review");
  const qc = useQueryClient();
  const toast = useToast();
  const src = listing.source_lang;
  const [title, setTitle] = useState(listing.title);
  const [desc, setDesc] = useState(listing.description);
  const [attrs, setAttrs] = useState<Record<string, unknown>>(listing.attributes);
  const [price, setPrice] = useState<string>(listing.price_inr ? String(listing.price_inr) : "");
  const [category, setCategory] = useState(listing.category_slug || "");
  const [craft, setCraft] = useState(listing.craft_slug || "");
  const [regenJob, setRegenJob] = useState<{ id: string; field: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showMore, setShowMore] = useState(false);
  const { data: cats } = useQuery({ queryKey: ["categories"], queryFn: () => api<{ items: CategoryItem[] }>("/catalog/categories") });
  const { data: crafts } = useQuery({ queryKey: ["crafts"], queryFn: () => api<{ items: { slug: string; name: string; gi_tag: boolean }[] }>("/catalog/crafts") });
  const tn = useTranslations("sell.new");
  // Market prices are fetched in the background after the draft is ready; poll for ~2 min until they land.
  const advice = useQuery({
    queryKey: ["advice", listing.id],
    queryFn: () => api<PriceAdvice>(`/listings/${listing.id}/price-advice`),
    refetchInterval: (q) => (q.state.data?.status === "none" && q.state.dataUpdateCount < 40 ? 3000 : false),
  });
  // Reading dataUpdatedAt subscribes this component to every poll, so the count below stays current.
  const pricePolls = advice.dataUpdatedAt && (qc.getQueryState(["advice", listing.id])?.dataUpdateCount ?? 0);
  const checkingPrices = advice.data?.status === "none" && pricePolls < 40;

  useJob(regenJob?.id, async () => {
    const fresh = await qc.fetchQuery({ queryKey: ["listing", listing.id], queryFn: () => api<ArtisanListing>(`/listings/${listing.id}`) });
    if (regenJob?.field === "title" || regenJob?.field === "all") setTitle(fresh.title);
    if (regenJob?.field === "description" || regenJob?.field === "all") setDesc(fresh.description);
    if (regenJob?.field === "attributes") setAttrs(fresh.attributes);
    setRegenJob(null);
  });

  const shotsJob = useJob(
    listing.shots_job_id,
    async () => {
      await qc.invalidateQueries({ queryKey: ["listing", listing.id] });
    },
    async () => {
      await qc.invalidateQueries({ queryKey: ["listing", listing.id] });
    }
  );

  const aiShots = listing.gallery.filter((g) => g.ai);
  const realPhotos = listing.gallery.filter((g) => !g.ai);

  const isGeneratingShots =
    shotsJob?.status === "queued" ||
    shotsJob?.status === "running" ||
    (Boolean(listing.shots_job_id) && !shotsJob && aiShots.length < 5);

  const [triggeringShots, setTriggeringShots] = useState(false);
  const triggerShots = async () => {
    setTriggeringShots(true);
    try {
      await api(`/listings/${listing.id}/generate-shots`, { method: "POST" });
      await qc.invalidateQueries({ queryKey: ["listing", listing.id] });
    } catch {
      toast(t("error"), "error");
    } finally {
      setTriggeringShots(false);
    }
  };

  const deleteShot = async (mediaId: string) => {
    try {
      await api(`/listings/${listing.id}/shots/${mediaId}`, { method: "DELETE" });
      await qc.invalidateQueries({ queryKey: ["listing", listing.id] });
    } catch {
      toast(t("error"), "error");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync local edit state when the listing is refetched
    setTitle(listing.title);
    setDesc(listing.description);
    setAttrs(listing.attributes);
    setPrice(listing.price_inr ? String(listing.price_inr) : "");
    setCategory(listing.category_slug || "");
    setCraft(listing.craft_slug || "");
  }, [listing.title, listing.description, listing.attributes, listing.price_inr, listing.category_slug, listing.craft_slug]);

  const regenerate = async (field: string) => {
    try {
      const r = await api<{ job_id: string }>(`/listings/${listing.id}/regenerate`, { method: "POST", body: { field } });
      setRegenJob({ id: r.job_id, field });
    } catch (e) {
      toast(e instanceof ApiError && e.code === "regenerate_limit_reached" ? t("regen_limit") : t("error"), "error");
    }
  };
  const low = (k: string) => (listing.field_confidence?.[k] ?? 1) < 0.7 || listing.missing_fields.includes(k);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await api(`/listings/${listing.id}`, {
        method: "PATCH",
        body: {
          title,
          description: desc,
          attributes: attrs,
          price_inr: price ? Number(price) : undefined,
          category_slug: category || undefined,
          craft_slug: craft,
        },
      });
      await qc.invalidateQueries({ queryKey: ["listing", listing.id] });
      onNext();
    } catch {
      setError(t("error"));
    } finally {
      setSaving(false);
    }
  };

  // Fields follow the selected category; anything already filled stays visible (no silent data loss after a
  // wrong category guess). Visibility uses the saved values so a field doesn't vanish while it's being cleared.
  const allFields = new Map<string, FieldSpec>();
  cats?.items.forEach((c) => c.attribute_schema?.fields?.forEach((f) => { if (!allFields.has(f.key)) allFields.set(f.key, f); }));
  const schema = cats?.items.find((c) => c.slug === category)?.attribute_schema?.fields ?? [];
  const inSchema = new Set(schema.map((f) => f.key));
  const saved = (f: FieldSpec) => filled(getPath(listing.attributes, f.key));
  const extras = [...allFields.values()].filter((f) => !inSchema.has(f.key) && saved(f));
  const hiddenOptional = schema.filter((f) => f.tier === "optional" && !saved(f));
  const fields = [...schema.filter((f) => showMore || f.tier !== "optional" || saved(f)), ...extras];
  const fieldLow = (f: FieldSpec) => {
    const has = filled(getPath(attrs, f.key));
    return (f.tier === "core" && !has) || (has && (listing.field_confidence?.[f.key.split(".")[0]] ?? 1) < 0.7);
  };
  const giCraft = crafts?.items.find((c) => c.slug === craft && c.gi_tag);
  const badgeNudge = giCraft && inSchema.has("technique") && !filled(getPath(attrs, "technique"));
  const langs = Array.from(new Set([src, "en", "hi"]));
  return (
    <section className="flex flex-col gap-4">
      <h1 className="font-display text-h2 leading-tight">{t("title")}</h1>
      {listing.extraction_status === "fallback" || listing.notes_for_artisan.includes("manual_form") ? <Banner tone="warn">{t("manual_fallback")}</Banner> : null}
      {listing.notes_for_artisan.filter((n) => n !== "manual_form").map((n) => (
        <Banner key={n} tone="warn" icon={<AlertTriangle className="size-5" />}>{t.has(`note.${n}`) ? t(`note.${n}`) : t("note.generic", { field: n })}</Banner>
      ))}
      {error && <Banner tone="danger">{error}</Banner>}

      <ReviewCard
        title={t("catalogue_images")}
        busy={isGeneratingShots || triggeringShots}
        onRegenerate={triggerShots}
      >
        {isGeneratingShots && (
          <div className="flex items-center gap-2 rounded-sm bg-brand-soft p-3 text-sm font-medium text-brand">
            <Spinner className="size-4 shrink-0" />
            <div className="flex flex-1 items-center justify-between">
              <span>{t("creating_catalogue_images")}</span>
              <span className="text-xs text-brand">{aiShots.length}/5 ready</span>
            </div>
          </div>
        )}

        {(aiShots.length > 0 || isGeneratingShots) && (
          <div className="no-scrollbar flex gap-2 overflow-x-auto pb-1">
            {aiShots.map((g) => (
              <div key={g.id} className="relative w-28 shrink-0">
                {g.card && (
                  <img
                    src={g.card}
                    alt=""
                    className="aspect-[4/5] w-full rounded-sm object-cover shadow-sm"
                  />
                )}
                {g.is_primary && (
                  <span className="absolute start-1 top-1 rounded-full bg-brand px-2 text-caption font-semibold text-white">
                    Hero
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => deleteShot(g.id)}
                  className="tap absolute end-1 top-1 flex size-6 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80"
                  aria-label={t("remove_image")}
                  title={t("remove_image")}
                >
                  <X className="size-3.5" />
                </button>
              </div>
            ))}
            {isGeneratingShots &&
              Array.from({ length: Math.max(0, 5 - aiShots.length) }).map((_, idx) => (
                <div
                  key={`skeleton-${idx}`}
                  className="relative flex aspect-[4/5] w-28 shrink-0 flex-col items-center justify-center gap-2 rounded-sm border-2 border-dashed border-sand-200 bg-gradient-to-b from-brand-soft/70 to-ink-50 p-2 text-center text-ink-400 animate-pulse"
                >
                  <div className="flex size-8 items-center justify-center rounded-full bg-brand-soft text-brand-hover">
                    <Sparkles className="size-4 animate-spin" />
                  </div>
                  <span className="text-caption font-medium text-ink-500">
                    {idx === 0 ? "Creating..." : `Shot ${aiShots.length + idx + 1}`}
                  </span>
                </div>
              ))}
          </div>
        )}

        {!isGeneratingShots && aiShots.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-3 rounded-sm border-2 border-dashed border-ink-200 p-6 text-center">
            <Sparkles className="size-8 text-brand" />
            <p className="text-sm text-ink-600">{t("no_catalogue_images")}</p>
            <Button variant="secondary" size="S" onClick={triggerShots} loading={triggeringShots}>
              {t("generate_now")}
            </Button>
          </div>
        )}

        <p className="mt-2 text-sm text-ink-600">{t("catalogue_note")}</p>
      </ReviewCard>

      <ReviewCard title={t("photos")}>
        <div className="no-scrollbar flex gap-2 overflow-x-auto">
          {realPhotos.map((g) => (
              <div key={g.id} className="relative w-28 shrink-0">
                {g.card && <img src={g.card} alt="" className="aspect-[4/5] w-full rounded-sm object-cover" />}
                {g.enhanced && <span className="absolute start-1 top-1 rounded-full bg-white/95 px-2 text-caption font-semibold text-brand">{t("cleaned_up")}</span>}
              </div>
            ))}
        </div>
        <p className="mt-2 text-sm text-ink-600">{t("photos_note")}</p>
      </ReviewCard>

      <ReviewCard
        title={t("name")}
        low={low("title")}
        busy={regenJob?.field === "title"}
        onRegenerate={() => regenerate("title")}
        onSpeak={(text) => setTitle({ ...title, [src]: text })}
        regenLeft={listing.regenerate_left}
      >
        {langs.map((l) => (
          <label key={l} className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-ink-600">{languageNames[l as Locale]?.native || l}</span>
            <Input value={title[l] || ""} onChange={(e) => setTitle({ ...title, [l]: e.target.value })} lang={l} dir={l === "ur" ? "rtl" : undefined} />
          </label>
        ))}
      </ReviewCard>

      <ReviewCard
        title={t("description")}
        low={low("description")}
        busy={regenJob?.field === "description"}
        onRegenerate={() => regenerate("description")}
        onSpeak={(text) => setDesc({ ...desc, [src]: `${desc[src] ? `${desc[src]} ` : ""}${text}` })}
        regenLeft={listing.regenerate_left}
      >
        {langs.map((l) => (
          <label key={l} className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-ink-600">{languageNames[l as Locale]?.native || l}</span>
            <Textarea value={desc[l] || ""} onChange={(e) => setDesc({ ...desc, [l]: e.target.value })} lang={l} dir={l === "ur" ? "rtl" : undefined} className="min-h-32" />
          </label>
        ))}
      </ReviewCard>

      <ReviewCard title={t("details")} busy={regenJob?.field === "attributes"} onRegenerate={() => regenerate("attributes")} regenLeft={listing.regenerate_left}>
        {badgeNudge && (
          <Banner tone="info" icon={<Sparkles className="size-5 shrink-0" />} action={<MicButton size={44} onText={(text) => setAttrs((a) => setPath(a, "technique", text))} />}>
            {t("badge_nudge", { craft: giCraft.name })}
          </Banner>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          {fields.map((f) => {
            const value = getPath(attrs, f.key);
            const lowConf = fieldLow(f);
            return (
              <label key={f.key} className="flex flex-col gap-1">
                <span className={cx("text-sm font-semibold", lowConf ? "text-terracotta-600" : "text-ink-900")}>
                  {t(`attr.${f.key.split(".").pop()}`)} {lowConf && <span className="text-xs font-normal">· {t("please_check")}</span>}
                </span>
                <div className="flex gap-2">
                  <Input
                    inputMode={f.type === "number" || f.type === "integer" ? "decimal" : undefined}
                    value={Array.isArray(value) ? value.join(", ") : value === undefined || value === null ? "" : String(value)}
                    onChange={(e) => setAttrs((a) => setPath(a, f.key, fromInput(f.type, e.target.value)))}
                    className={lowConf ? "border-gold-500 ring-2 ring-gold-500/30" : ""}
                  />
                  <MicButton size={44} onText={(text) => setAttrs((a) => setPath(a, f.key, fromInput(f.type, text)))} />
                </div>
              </label>
            );
          })}
        </div>
        {!showMore && hiddenOptional.length > 0 && (
          <Button variant="secondary" size="S" icon={<Plus className="size-4" />} onClick={() => setShowMore(true)}>
            {t("more_details")}
          </Button>
        )}
      </ReviewCard>

      <ReviewCard title={t("category")} low={low("category_slug")}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Select value={category} onChange={(e) => setCategory(e.target.value)} aria-label={t("category")}>
            <option value="">{t("choose")}</option>
            {cats?.items.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
          </Select>
          <Select value={craft} onChange={(e) => setCraft(e.target.value)} aria-label={t("craft")}>
            <option value="">{t("no_craft")}</option>
            {crafts?.items.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
          </Select>
        </div>
      </ReviewCard>

      <ReviewCard title={t("price")} low={low("price_inr")}>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-semibold">₹</span>
          <Input inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value.replace(/\D/g, ""))} className="text-2xl font-semibold" aria-label={t("price")} />
          <MicButton onText={(text) => setPrice(text.replace(/\D/g, ""))} />
        </div>
        {!price && <p className="text-sm text-terracotta-600">{t("price_missing")}</p>}
        {advice.isLoading || checkingPrices ? (
          <div className="mt-2 flex flex-col gap-2">
            <p className="flex items-center gap-2 text-sm text-ink-600"><Spinner className="size-4" /> {tn("step.checking_prices")}</p>
            <Skeleton className="h-20" />
          </div>
        ) : advice.data && advice.data.status !== "none" ? (
          <div className="mt-2 flex flex-col gap-3">
            <PriceRangeBar advice={advice.data} price={price ? Number(price) : null} />
            {advice.data.suggested_inr && Number(price) !== advice.data.suggested_inr && (
              <Button variant="secondary" onClick={() => setPrice(String(advice.data!.suggested_inr))}>{t("use_price", { price: inr(advice.data.suggested_inr) })}</Button>
            )}
            <p className="text-xs text-ink-600">{t("never_changes")}</p>
          </div>
        ) : null}
      </ReviewCard>

      {listing.transcript && (
        <details className="rounded-sm bg-white p-4">
          <summary className="cursor-pointer font-semibold">{t("what_you_said")}</summary>
          <p className="mt-2 text-body-s" lang={src}>{listing.transcript}</p>
          {listing.transcript_provider === "browser" && <p className="mt-1 text-xs text-ink-600">{t("browser_transcript")}</p>}
        </details>
      )}

      <div className="flex gap-2">
        <Button variant="secondary" size="L" icon={<RefreshCw className="size-5" />} onClick={() => regenerate("all")} loading={regenJob?.field === "all"} disabled={listing.regenerate_left <= 0}>
          {t("regenerate_all")}
        </Button>
        <Button size="L" block loading={saving} disabled={!price || !category || !(title[src] || title.en)} onClick={save}>
          {t("looks_good")}
        </Button>
      </div>
    </section>
  );
}

function ReviewCard({ title, children, low, busy, onRegenerate, onSpeak, regenLeft }: { title: string; children: ReactNode; low?: boolean; busy?: boolean; onRegenerate?: () => void; onSpeak?: (text: string) => void; regenLeft?: number }) {
  const t = useTranslations("sell.review");
  return (
    <div className={cx("flex flex-col gap-3 rounded-md border-2 bg-white p-4", low ? "border-gold-500" : "border-ink-100")}>
      <div className="flex items-center gap-2">
        <h2 className="flex flex-1 items-center gap-2 font-semibold">
          <Pencil className="size-4 text-ink-600" /> {title}
        </h2>
        {onSpeak && <MicButton size={44} onText={onSpeak} />}
        {onRegenerate && (
          <button
            type="button"
            onClick={onRegenerate}
            disabled={busy || (regenLeft ?? 1) <= 0}
            className="tap inline-flex items-center justify-center rounded-full text-brand hover:bg-brand-soft disabled:text-ink-300"
            aria-label={t("regenerate")}
            title={t("regen_left", { n: regenLeft ?? 0 })}
          >
            <RefreshCw className={cx("size-5", busy && "animate-spin")} />
          </button>
        )}
      </div>
      {children}
    </div>
  );
}
