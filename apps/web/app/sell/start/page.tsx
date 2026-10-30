"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LocateFixed, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { LanguageTiles } from "@/components/karu/language";
import { SpeakerButton, VoiceField } from "@/components/karu/voice";
import { OtpLogin } from "@/components/otp-login";
import { Banner, Button, Field, Input, Select, Spinner } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { cx } from "@/lib/format";
import { useMe } from "@/lib/hooks";

type Step = "language" | "phone" | "name" | "dob" | "craft" | "location" | "consent";
const DETAIL_STEPS: Step[] = ["name", "dob", "craft", "location", "consent"];
// Latest date of birth allowed (18+), computed once per page load.
const ADULT_MAX = new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().slice(0, 10);

const STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
  "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
];

/** F1 artisan onboarding — target under 3 minutes. */
export default function StartPage() {
  const t = useTranslations("sell.start");
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me, isLoading } = useMe();
  const [step, setStep] = useState<Step>("language");
  const [form, setForm] = useState({ public_name: "", dob: "", crafts: [] as string[], other_craft: "", village_town: "", district: "", state: "", pin_code: "", lat: null as number | null, lng: null as number | null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (me?.has_artisan_profile) router.replace("/sell");
  }, [me, router]);

  const { data: crafts } = useQuery({ queryKey: ["crafts"], queryFn: () => api<{ items: { slug: string; name: string; regions: string[] }[] }>("/catalog/crafts") });

  if (isLoading) return <div className="flex min-h-[50vh] items-center justify-center"><Spinner /></div>;

  const next = (s: Step) => {
    setError(null);
    setStep(s);
    window.scrollTo({ top: 0 });
  };
  const detailIndex = DETAIL_STEPS.indexOf(step);

  const finish = async () => {
    setBusy(true);
    setError(null);
    try {
      const crafts = [...form.crafts, ...(form.other_craft.trim() ? [form.other_craft.trim()] : [])];
      await api("/artisan/enable", {
        method: "POST",
        body: {
          public_name: form.public_name.trim(),
          legal_name: form.public_name.trim(),
          dob: form.dob || null,
          crafts,
          village_town: form.village_town || null,
          district: form.district || null,
          state: form.state || null,
          pin_code: /^\d{6}$/.test(form.pin_code) ? form.pin_code : null,
          lat: form.lat,
          lng: form.lng,
          consents: ["terms", "privacy", "public_voice", "public_video"],
        },
      });
      await qc.invalidateQueries({ queryKey: ["me"] });
      router.replace("/sell?welcome=1");
    } catch (e) {
      setError(e instanceof ApiError ? t(`errors.${["must_be_adult", "invalid_state", "already_artisan"].includes(e.code) ? e.code : "generic"}`) : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-lg flex-col gap-6 px-4 pb-16 pt-6">
      {detailIndex >= 0 && (
        <div className="flex justify-center gap-2" aria-label={t("progress", { n: detailIndex + 1, total: DETAIL_STEPS.length })}>
          {DETAIL_STEPS.map((s, i) => (
            <span key={s} className={cx("h-2 rounded-full transition-all", i <= detailIndex ? "w-8 bg-brand" : "w-2 bg-ink-300")} />
          ))}
        </div>
      )}
      {error && <Banner tone="danger">{error}</Banner>}

      {step === "language" && (
        <section className="flex flex-col gap-5">
          <Header title={t("language_title")} body={t("language_body")} />
          <LanguageTiles signedIn={!!me} onPick={() => setTimeout(() => { router.refresh(); next(me ? "name" : "phone"); }, 600)} />
        </section>
      )}

      {step === "phone" && (
        <section className="flex flex-col gap-5">
          <Header title={t("phone_title")} body={t("phone_body")} />
          <OtpLogin big onDone={(r) => (r.user.has_artisan_profile ? router.replace("/sell") : next("name"))} />
        </section>
      )}

      {step === "name" && (
        <Question title={t("name_q")} onNext={() => next("dob")} canNext={form.public_name.trim().length > 0}>
          <VoiceField
            value={form.public_name}
            onChange={(e) => setForm({ ...form, public_name: e.target.value })}
            onVoice={(text) => setForm({ ...form, public_name: text.replace(/[.।]$/, "") })}
            aria-label={t("name_q")}
            autoComplete="name"
            className="text-xl"
          />
          <p className="text-sm text-ink-600">{t("name_hint")}</p>
        </Question>
      )}

      {step === "dob" && (
        <Question title={t("dob_q")} onNext={() => next("craft")} onSkip={() => next("craft")} canNext={!!form.dob}>
          <Input type="date" value={form.dob} max={ADULT_MAX} onChange={(e) => setForm({ ...form, dob: e.target.value })} className="text-xl" aria-label={t("dob_q")} />
          <p className="text-sm text-ink-600">{t("dob_hint")}</p>
        </Question>
      )}

      {step === "craft" && (
        <Question title={t("craft_q")} onNext={() => next("location")} onSkip={() => next("location")} canNext={form.crafts.length > 0 || !!form.other_craft.trim()}>
          <div className="grid grid-cols-2 gap-3">
            {crafts?.items.map((c) => {
              const on = form.crafts.includes(c.slug);
              return (
                <button
                  key={c.slug}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setForm({ ...form, crafts: on ? form.crafts.filter((x) => x !== c.slug) : [...form.crafts, c.slug] })}
                  className={cx("flex min-h-20 flex-col items-start justify-center rounded-md border-2 bg-white p-3 text-start", on ? "border-brand bg-brand-soft" : "border-ink-100")}
                >
                  <span className="font-semibold">{c.name}</span>
                  <span className="text-xs text-ink-600">{c.regions[0]}</span>
                </button>
              );
            })}
          </div>
          <Field label={t("craft_other")}>
            <VoiceField value={form.other_craft} onChange={(e) => setForm({ ...form, other_craft: e.target.value })} onVoice={(text) => setForm({ ...form, other_craft: text })} aria-label={t("craft_other")} />
          </Field>
        </Question>
      )}

      {step === "location" && (
        <Question title={t("location_q")} onNext={() => next("consent")} onSkip={() => next("consent")} canNext={!!(form.district || form.village_town || form.pin_code)}>
          <Button
            variant="secondary"
            size="L"
            icon={<LocateFixed className="size-5" />}
            onClick={() =>
              navigator.geolocation?.getCurrentPosition(
                (pos) => setForm({ ...form, lat: Math.round(pos.coords.latitude * 100) / 100, lng: Math.round(pos.coords.longitude * 100) / 100 }),
                () => setError(t("errors.location_denied")),
                { enableHighAccuracy: false, timeout: 10000 },
              )
            }
          >
            {form.lat ? t("location_saved") : t("use_location")}
          </Button>
          <p className="text-xs text-ink-600">{t("location_privacy")}</p>
          <Field label={t("pin")} htmlFor="pin">
            <Input
              id="pin"
              inputMode="numeric"
              maxLength={6}
              value={form.pin_code}
              onChange={async (e) => {
                const pin = e.target.value.replace(/\D/g, "").slice(0, 6);
                setForm((f) => ({ ...f, pin_code: pin }));
                if (pin.length === 6) {
                  const r = await api<{ found: boolean; district?: string; state?: string; places?: string[] }>(`/geo/pincode/${pin}`).catch(() => null);
                  if (r?.found) setForm((f) => ({ ...f, district: r.district || f.district, state: STATES.find((s) => s.toLowerCase() === (r.state || "").toLowerCase()) || f.state }));
                }
              }}
              className="text-xl tracking-widest"
            />
          </Field>
          <Field label={t("village")}>
            <VoiceField value={form.village_town} onChange={(e) => setForm({ ...form, village_town: e.target.value })} onVoice={(text) => setForm({ ...form, village_town: text })} aria-label={t("village")} />
          </Field>
          <Field label={t("district")}>
            <VoiceField value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} onVoice={(text) => setForm({ ...form, district: text })} aria-label={t("district")} />
          </Field>
          <Field label={t("state")} htmlFor="state">
            <Select id="state" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })}>
              <option value="">—</option>
              {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
          </Field>
        </Question>
      )}

      {step === "consent" && (
        <section className="flex flex-col gap-5">
          <div className="flex items-start gap-2">
            <ShieldCheck className="mt-1 size-8 shrink-0 text-peacock-600" />
            <h1 className="font-display flex-1 text-h2 leading-tight">{t("consent_title")}</h1>
            <SpeakerButton text={`${t("consent_title")}. ${t("consent_1")} ${t("consent_2")} ${t("consent_3")} ${t("consent_4")}`} auto />
          </div>
          <ul className="flex flex-col gap-3 rounded-md bg-white p-5 text-body">
            {[1, 2, 3, 4].map((n) => (
              <li key={n} className="flex gap-3">
                <span className="mt-1 flex size-6 shrink-0 items-center justify-center rounded-full bg-peacock-50 text-sm font-bold text-peacock-600">✓</span>
                {t(`consent_${n}`)}
              </li>
            ))}
          </ul>
          <p className="text-sm text-ink-600">
            {t("consent_full")} <span className="font-semibold text-brand">{t("terms")}</span> · <span className="font-semibold text-brand">{t("privacy")}</span>
          </p>
          <Button size="L" variant="verified" loading={busy} onClick={finish}>{t("agree")}</Button>
        </section>
      )}
    </div>
  );
}

function Header({ title, body }: { title: string; body?: string }) {
  return (
    <div className="flex items-start gap-2">
      <div className="flex-1">
        <h1 className="font-display text-h2 leading-tight">{title}</h1>
        {body && <p className="mt-1 text-ink-600">{body}</p>}
      </div>
      <SpeakerButton text={`${title}. ${body || ""}`} auto />
    </div>
  );
}

function Question({ title, children, onNext, onSkip, canNext }: { title: string; children: React.ReactNode; onNext: () => void; onSkip?: () => void; canNext: boolean }) {
  const t = useTranslations("sell.start");
  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        if (canNext) onNext();
      }}
    >
      <Header title={title} />
      {children}
      <Button type="submit" size="L" disabled={!canNext}>{t("next")}</Button>
      {onSkip && (
        <button type="button" onClick={onSkip} className="min-h-12 font-semibold text-brand underline">
          {t("skip")}
        </button>
      )}
    </form>
  );
}
