"use client";

import { useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, Minus, PartyPopper, Plus, Share2, Video } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRef, useState } from "react";
import { VerifiedBadge } from "@/components/karu/badges";
import { Banner, Button, Switch } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { mediaDuration, uploadMedia } from "@/lib/media";
import type { ArtisanListing } from "./review";

/** Making-video picker: native camera at 720p where possible; 20 s – 5 min; resumable upload. */
export function MakingVideoPicker({ listingId, onAttached, compact }: { listingId: string; onAttached: () => void; compact?: boolean }) {
  const t = useTranslations("sell.video");
  const input = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pick = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    const duration = await mediaDuration(file, "video");
    if (duration !== null && duration > 300) return setError(t("too_long"));
    if (duration !== null && duration < 18) return setError(t("too_short"));
    if (file.size > 300 * 1024 * 1024) return setError(t("too_big"));
    try {
      setProgress(0);
      const id = await uploadMedia(file, "video", { durationS: duration, onProgress: setProgress });
      await api(`/listings/${listingId}/making-video`, { method: "POST", body: { media_id: id } });
      onAttached();
    } catch (e) {
      setError(e instanceof ApiError ? t(`errors.${["video_too_short", "media_too_long", "unsupported_media_type"].includes(e.code) ? e.code : "generic"}`) : t("errors.upload"));
    } finally {
      setProgress(null);
    }
  };
  return (
    <div className="flex flex-col gap-3">
      {!compact && (
        <ul className="list-disc space-y-1 ps-5 text-body-s text-ink-600">
          <li>{t("guide_hands")}</li>
          <li>{t("guide_tools")}</li>
          <li>{t("guide_end")}</li>
          <li>{t("guide_children")}</li>
        </ul>
      )}
      {error && <Banner tone="danger">{error}</Banner>}
      {progress !== null ? (
        <div className="flex flex-col gap-2">
          <div className="h-3 overflow-hidden rounded-full bg-ink-100">
            <div className="h-full rounded-full bg-peacock-600 transition-all" style={{ width: `${Math.round(progress * 100)}%` }} />
          </div>
          <p className="text-sm text-ink-600">{t("uploading", { pct: Math.round(progress * 100) })}</p>
        </div>
      ) : (
        <Button variant="verified" size="L" icon={<Video className="size-5" />} onClick={() => input.current?.click()}>
          {t("add")}
        </Button>
      )}
      <input ref={input} type="file" accept="video/*" capture="environment" className="hidden" onChange={(e) => void pick(e.target.files?.[0])} />
    </div>
  );
}

/** A09: quantity stepper, returnable switch + nudge, optional making video, category confirm. */
export function FinalStep({ listing, onPublished }: { listing: ArtisanListing; onPublished: (r: { karu_ids: string[]; short_code: string; verification_status: string }) => void }) {
  const t = useTranslations("sell.final");
  const qc = useQueryClient();
  const [qty, setQty] = useState(1);
  const [returnable, setReturnable] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasVideo = !!listing.making_video;
  return (
    <section className="flex flex-col gap-5">
      <h1 className="font-display text-h2 leading-tight">{t("title")}</h1>
      {error && <Banner tone="danger">{error}</Banner>}
      <div className="flex items-center justify-between rounded-md bg-white p-4">
        <div>
          <p className="font-semibold">{t("quantity")}</p>
          <p className="text-sm text-ink-600">{t("quantity_hint")}</p>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-ink-300">
          <button className="tap flex items-center justify-center" onClick={() => setQty(Math.max(1, qty - 1))} aria-label={t("less")}><Minus className="size-5" /></button>
          <span className="w-10 text-center text-2xl font-semibold" aria-live="polite">{qty}</span>
          <button className="tap flex items-center justify-center" onClick={() => setQty(Math.min(500, qty + 1))} aria-label={t("more")}><Plus className="size-5" /></button>
        </div>
      </div>
      <div className="rounded-md bg-white p-4">
        <Switch checked={returnable} onChange={setReturnable} label={t("returnable")} description={t("returnable_nudge")} />
      </div>
      <div className="flex flex-col gap-3 rounded-md border-2 border-peacock-600/30 bg-peacock-50 p-4">
        <p className="flex items-center gap-2 font-semibold text-peacock-600"><BadgeCheck className="size-5" /> {t("get_verified")}</p>
        <p className="text-body-s text-ink-900">{t("get_verified_body")}</p>
        {hasVideo ? <Banner tone="success">{t("video_added")}</Banner> : <MakingVideoPicker listingId={listing.id} onAttached={() => qc.invalidateQueries({ queryKey: ["listing", listing.id] })} />}
        {!hasVideo && <p className="text-sm text-ink-600">{t("video_later")}</p>}
      </div>
      <Button
        size="L"
        loading={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            const r = await api<{ karu_ids: string[]; short_code: string; verification_status: string }>(`/listings/${listing.id}/publish`, {
              method: "POST",
              body: { quantity: qty, returnable },
            });
            await qc.invalidateQueries({ queryKey: ["my-listings"] });
            onPublished(r);
          } catch (e) {
            setError(e instanceof ApiError && e.code === "listing_incomplete" ? t("incomplete") : t("error"));
          } finally {
            setBusy(false);
          }
        }}
      >
        {t("publish")}
      </Button>
    </section>
  );
}

/** A10: warm, confetti-free success with Karu IDs created, verification status and share. */
export function Published({ listing, result }: { listing: ArtisanListing; result: { karu_ids: string[]; short_code: string; verification_status: string } }) {
  const t = useTranslations("sell.published");
  const title = listing.title[listing.source_lang] || listing.title.en || "";
  return (
    <section className="flex flex-col items-center gap-5 py-6 text-center">
      <span className="animate-settle flex size-20 items-center justify-center rounded-full bg-peacock-50 text-peacock-600">
        <PartyPopper className="size-10" />
      </span>
      <h1 className="font-display text-h2 leading-tight">{t("title", { title })}</h1>
      <p className="text-ink-600">{t("ids_created", { n: result.karu_ids.length })}</p>
      <ul className="flex flex-wrap justify-center gap-2">
        {result.karu_ids.map((k) => (
          <li key={k} className="rounded-full bg-white px-3 py-1 font-mono text-sm font-semibold text-brand">{k}</li>
        ))}
      </ul>
      <div className="flex flex-col items-center gap-2 rounded-md bg-white p-4">
        <VerifiedBadge status={listing.making_video ? "checking" : "not_verified"} size="lg" />
        <p className="text-sm text-ink-600">{listing.making_video ? t("checking") : t("add_video_hint")}</p>
      </div>
      <div className="flex w-full flex-col gap-2">
        <Link href={`/sell/products/${listing.id}?tab=share`} className="flex min-h-12 items-center justify-center gap-2 rounded-sm bg-brand font-semibold text-white">
          <Share2 className="size-5" /> {t("share")}
        </Link>
        {!listing.making_video && (
          <Link href={`/sell/products/${listing.id}?tab=verification`} className="flex min-h-12 items-center justify-center rounded-sm border-2 border-peacock-600 font-semibold text-peacock-600">
            {t("get_verified")}
          </Link>
        )}
        <Link href="/sell" className="min-h-12 font-semibold text-brand underline">{t("home")}</Link>
      </div>
    </section>
  );
}
