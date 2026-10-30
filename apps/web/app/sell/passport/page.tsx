"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, Camera, CircleDashed, IdCard, Mic, Settings, Wallet, HelpCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Suspense, useState } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { PassportCard } from "@/components/karu/passport-card";
import { VoiceField } from "@/components/karu/voice";
import { useToast } from "@/components/toast";
import { Banner, Button, Card, Field, Input, Skeleton, Switch } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { cx } from "@/lib/format";
import { uploadMedia, uploadPhoto } from "@/lib/media";
import { VoiceRecorder } from "@/lib/speech";
import { speechTags, type Locale } from "@/i18n/config";
import type { Maker } from "@/lib/types";

interface PassportView {
  passport: { code: string; state: string; verified_at: string | null; member_since: string };
  checklist: { aadhaar: boolean; one_of: { pehchan: boolean; verified_product: boolean; reviews: boolean }; reviews_count: number; min_reviews: number; min_avg_rating: number };
  public: Maker;
}

interface Profile {
  public_name: string;
  crafts: string[];
  years_of_practice: number | null;
  story_text: Record<string, string>;
  story_voice: { id: string; url: string | null } | null;
  show_voice_publicly: boolean;
  photo_url: string | null;
  linked_social_urls: string[];
  aadhaar_status: string;
  aadhaar_last4: string | null;
  pehchan_status: string;
  profile_completion: number;
  profile_missing: string[];
  handle: string;
  handle_editable: boolean;
}

/** A15: passport card, how to reach "Verified" as a checklist, public profile editor. */
export default function PassportPage() {
  return (
    <Suspense>
      <AuthGate require="artisan">{() => <PassportView />}</AuthGate>
    </Suspense>
  );
}

function PassportView() {
  const t = useTranslations("sell.passport");
  const locale = useLocale() as Locale;
  const params = useSearchParams();
  const toast = useToast();
  const qc = useQueryClient();
  const pass = useQuery({ queryKey: ["passport"], queryFn: () => api<PassportView>("/artisan/passport") });
  const prof = useQuery({ queryKey: ["artisan-profile"], queryFn: () => api<Profile>("/artisan/profile") });
  const [card, setCard] = useState("");
  const kyc = params.get("kyc");
  if (!pass.data || !prof.data) return <SellPage><Skeleton className="h-96" /></SellPage>;
  const c = pass.data.checklist;
  const p = prof.data;
  const refresh = () => Promise.all([pass.refetch(), prof.refetch(), qc.invalidateQueries({ queryKey: ["sell-dashboard"] })]);

  return (
    <SellPage title={t("title")}>
      {kyc === "verified" && <Banner tone="success">{t("kyc_done")}</Banner>}
      {kyc === "failed" && <Banner tone="warn">{t("kyc_failed")}</Banner>}
      {pass.data.passport.state === "suspended" && <Banner tone="danger">{t("suspended")}</Banner>}
      <PassportCard maker={pass.data.public} locale={locale} exportable />

      <Card className="flex flex-col gap-3 p-4">
        <h2 className="font-semibold">{pass.data.passport.state === "verified" ? t("you_are_verified") : t("how_to_verify")}</h2>
        <Check done={c.aadhaar} label={t("check_aadhaar")} />
        <p className="text-sm text-ink-600">{t("and_one_of")}</p>
        <Check done={c.one_of.pehchan} label={t("check_pehchan")} />
        <Check done={c.one_of.verified_product} label={t("check_product")} />
        <Check done={c.one_of.reviews} label={t("check_reviews", { n: c.min_reviews, avg: c.min_avg_rating, have: c.reviews_count })} />
      </Card>

      <Card className="flex flex-col gap-3 p-4">
        <h2 className="flex items-center gap-2 font-semibold"><IdCard className="size-5" /> {t("aadhaar")}</h2>
        {p.aadhaar_status === "verified" ? (
          <p className="text-peacock-600">✓ {t("aadhaar_verified", { last4: p.aadhaar_last4 || "" })}</p>
        ) : (
          <>
            <p className="text-body-s text-ink-600">{t("aadhaar_body")}</p>
            <Button
              variant="verified"
              size="L"
              onClick={async () => {
                const r = await api<{ redirect_url: string }>("/artisan/kyc/aadhaar/start", { method: "POST" });
                window.location.href = r.redirect_url;
              }}
            >
              {t("aadhaar_start")}
            </Button>
          </>
        )}
        <p className="text-xs text-ink-600">{t("aadhaar_privacy")}</p>
      </Card>

      <Card className="flex flex-col gap-3 p-4">
        <h2 className="font-semibold">{t("pehchan")}</h2>
        {p.pehchan_status === "verified" ? (
          <p className="text-peacock-600">✓ {t("pehchan_verified")}</p>
        ) : p.pehchan_status === "pending" ? (
          <p className="text-ink-600">{t("pehchan_pending")}</p>
        ) : (
          <form
            className="flex gap-2"
            onSubmit={async (e) => {
              e.preventDefault();
              await api("/artisan/pehchan", { method: "POST", body: { card_no: card } });
              toast(t("pehchan_sent"));
              void refresh();
            }}
          >
            <Input value={card} onChange={(e) => setCard(e.target.value)} placeholder={t("pehchan_ph")} aria-label={t("pehchan")} />
            <Button type="submit" disabled={card.length < 4}>{t("check")}</Button>
          </form>
        )}
        {p.pehchan_status === "failed" && <Banner tone="warn">{t("pehchan_failed")}</Banner>}
      </Card>

      <ProfileEditor profile={p} locale={locale} onSaved={refresh} />

      <nav className="grid grid-cols-3 gap-2">
        <QuickLink href="/sell/payouts" icon={<Wallet className="size-6" />} label={t("payouts")} />
        <QuickLink href="/sell/settings" icon={<Settings className="size-6" />} label={t("settings")} />
        <QuickLink href="/sell/help" icon={<HelpCircle className="size-6" />} label={t("help")} />
      </nav>
    </SellPage>
  );
}

function Check({ done, label }: { done: boolean; label: string }) {
  return (
    <p className={cx("flex items-start gap-2 text-body-s", done ? "text-peacock-600" : "text-ink-900")}>
      {done ? <BadgeCheck className="size-5 shrink-0" /> : <CircleDashed className="size-5 shrink-0 text-ink-300" />} {label}
    </p>
  );
}

function QuickLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link href={href} className="flex min-h-20 flex-col items-center justify-center gap-1 rounded-md border border-ink-100 bg-white text-sm font-semibold text-brand">
      {icon}
      {label}
    </Link>
  );
}

function ProfileEditor({ profile, locale, onSaved }: { profile: Profile; locale: Locale; onSaved: () => void }) {
  const t = useTranslations("sell.passport");
  const toast = useToast();
  const [story, setStory] = useState(profile.story_text[locale] || Object.values(profile.story_text)[0] || "");
  const [years, setYears] = useState(profile.years_of_practice ? String(profile.years_of_practice) : "");
  const [links, setLinks] = useState(profile.linked_social_urls.join("\n"));
  const [showVoice, setShowVoice] = useState(profile.show_voice_publicly);
  const [handle, setHandle] = useState(profile.handle);
  const [busy, setBusy] = useState<string | null>(null);
  const [rec, setRec] = useState<VoiceRecorder | null>(null);

  const patch = async (body: Record<string, unknown>, key: string) => {
    setBusy(key);
    try {
      await api("/artisan/profile", { method: "PATCH", body });
      toast(t("saved"));
      onSaved();
    } catch (e) {
      toast(e instanceof ApiError && (e.code === "handle_taken" || e.code === "handle_already_edited") ? t(e.code) : t("error"), "error");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="flex flex-col gap-4 p-4">
      <h2 className="font-semibold">{t("public_profile")}</h2>
      <label className="flex items-center gap-3">
        <span className="flex size-16 items-center justify-center overflow-hidden rounded-full bg-brand-soft">
          {profile.photo_url ? <img src={profile.photo_url} alt="" className="size-full object-cover" /> : <Camera className="size-6 text-brand" />}
        </span>
        <span className="font-semibold text-brand underline">{busy === "photo" ? t("uploading") : t("change_photo")}</span>
        <input
          type="file"
          accept="image/*"
          className="hidden"
          onChange={async (e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            setBusy("photo");
            const id = await uploadPhoto(f);
            await patch({ profile_photo_media_id: id }, "photo");
          }}
        />
      </label>
      <Field label={t("story")} hint={t("story_hint")}>
        <VoiceField multiline textareaValue={story} onTextarea={setStory} onVoice={(x) => setStory((s) => (s ? `${s} ${x}` : x))} aria-label={t("story")} />
      </Field>
      <div className="flex flex-col gap-2">
        <span className="text-sm font-semibold">{t("voice_clip")}</span>
        {profile.story_voice?.url && <audio src={profile.story_voice.url} controls className="w-full" />}
        <Button
          variant="secondary"
          icon={<Mic className="size-5" />}
          onClick={async () => {
            if (rec) {
              const out = await rec.stop();
              setRec(null);
              setBusy("voice");
              const id = await uploadMedia(out.blob, "voice", { durationS: out.durationS });
              await patch({ story_voice_media_id: id, show_voice_publicly: showVoice }, "voice");
            } else {
              const r = new VoiceRecorder(speechTags[locale]);
              await r.start();
              setRec(r);
            }
          }}
          loading={busy === "voice"}
        >
          {rec ? t("stop_recording") : profile.story_voice ? t("rerecord_voice") : t("record_voice")}
        </Button>
        <Switch checked={showVoice} onChange={(v) => { setShowVoice(v); void patch({ show_voice_publicly: v }, "voice-toggle"); }} label={t("show_voice")} description={t("show_voice_hint")} />
      </div>
      <Field label={t("years")}>
        <Input inputMode="numeric" value={years} onChange={(e) => setYears(e.target.value.replace(/\D/g, "").slice(0, 2))} />
      </Field>
      <Field label={t("links")} hint={t("links_hint")}>
        <textarea value={links} onChange={(e) => setLinks(e.target.value)} className="min-h-20 rounded-xs border border-ink-300 p-3" />
      </Field>
      <Field label={t("handle")} hint={profile.handle_editable ? t("handle_hint") : t("handle_locked")}>
        <Input value={handle} onChange={(e) => setHandle(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} disabled={!profile.handle_editable} dir="ltr" />
      </Field>
      <Button
        size="L"
        loading={busy === "profile"}
        onClick={() =>
          patch(
            {
              story_text: { ...profile.story_text, [locale]: story },
              years_of_practice: years ? Number(years) : null,
              linked_social_urls: links.split(/\s+/).filter(Boolean),
              ...(profile.handle_editable && handle !== profile.handle ? { handle } : {}),
            },
            "profile",
          )
        }
      >
        {t("save")}
      </Button>
    </Card>
  );
}
