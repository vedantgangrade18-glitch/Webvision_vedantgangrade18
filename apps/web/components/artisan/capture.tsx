"use client";

import { Camera, ImagePlus, Mic, Play, RotateCcw, Square, Sun, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { SpeakerButton } from "@/components/karu/voice";
import { Banner, Button } from "@/components/ui";
import { speechTags, type Locale } from "@/i18n/config";
import { cx } from "@/lib/format";
import { brightness } from "@/lib/media";
import { VoiceRecorder, type Recording } from "@/lib/speech";

export interface PhotoItem {
  file: Blob;
  url: string;
  dark: boolean;
}

/** A06: camera with on-screen tips, up to 6 photos, retake/remove, "photo too dark" warning. */
export function PhotoStep({ photos, setPhotos, max = 6, onNext }: { photos: PhotoItem[]; setPhotos: (p: PhotoItem[]) => void; max?: number; onNext: () => void }) {
  const t = useTranslations("sell.new");
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const add = async (files: FileList | null) => {
    if (!files) return;
    const next = [...photos];
    for (const f of Array.from(files)) {
      if (next.length >= max) break;
      if (!f.type.startsWith("image/")) continue;
      next.push({ file: f, url: URL.createObjectURL(f), dark: (await brightness(f)) < 60 });
    }
    setPhotos(next);
  };
  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-start gap-2">
        <h1 className="font-display flex-1 text-h2 leading-tight">{t("photos_title")}</h1>
        <SpeakerButton text={`${t("photos_title")}. ${t("tip_daylight")}. ${t("tip_plain")}. ${t("tip_whole")}.`} auto />
      </div>
      <ul className="grid grid-cols-3 gap-2 rounded-md bg-brand-soft p-3 text-sm font-medium text-brand">
        <li className="flex flex-col items-center gap-1 text-center"><Sun className="size-6" />{t("tip_daylight")}</li>
        <li className="flex flex-col items-center gap-1 text-center"><span className="size-6 rounded border-2 border-current" />{t("tip_plain")}</li>
        <li className="flex flex-col items-center gap-1 text-center"><Camera className="size-6" />{t("tip_whole")}</li>
      </ul>
      {photos.some((p) => p.dark) && <Banner tone="warn">{t("too_dark")}</Banner>}
      <div className="grid grid-cols-3 gap-2">
        {photos.map((p, i) => (
          <div key={p.url} className={cx("relative aspect-[4/5] overflow-hidden rounded-sm border-2", p.dark ? "border-gold-500" : "border-transparent")}>
            <img src={p.url} alt={t("photo_n", { n: i + 1 })} className="size-full object-cover" />
            {i === 0 && <span className="absolute start-1 top-1 rounded-full bg-brand px-2 text-xs font-semibold text-white">{t("main_photo")}</span>}
            <button
              type="button"
              onClick={() => setPhotos(photos.filter((_, j) => j !== i))}
              className="absolute end-1 bottom-1 flex size-10 items-center justify-center rounded-full bg-white/95 text-danger-600"
              aria-label={t("remove_photo")}
            >
              <Trash2 className="size-5" />
            </button>
          </div>
        ))}
        {photos.length < max && (
          <button
            type="button"
            onClick={() => camera.current?.click()}
            className="flex aspect-[4/5] flex-col items-center justify-center gap-2 rounded-sm border-2 border-dashed border-brand bg-white text-brand"
          >
            <Camera className="size-8" />
            <span className="text-sm font-semibold">{photos.length ? t("add_photo") : t("take_photo")}</span>
          </button>
        )}
      </div>
      <input ref={camera} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => void add(e.target.files).then(() => (e.target.value = ""))} />
      <input ref={gallery} type="file" accept="image/*" multiple className="hidden" onChange={(e) => void add(e.target.files).then(() => (e.target.value = ""))} />
      <Button variant="secondary" size="L" icon={<ImagePlus className="size-5" />} onClick={() => gallery.current?.click()} disabled={photos.length >= max}>
        {t("from_gallery")}
      </Button>
      <p className="text-center text-sm text-ink-600">{t("photo_count", { n: photos.length, max })}</p>
      <Button size="L" disabled={!photos.length} onClick={onNext}>{t("next")}</Button>
    </section>
  );
}

/** A07: big mic, live waveform, timer, example prompt (shown and spoken), playback, re-record. */
export function VoiceStep({ maxSeconds, onDone, onSkip }: { maxSeconds: number; onDone: (r: Recording) => void; onSkip: () => void }) {
  const t = useTranslations("sell.new");
  const locale = useLocale() as Locale;
  const [state, setState] = useState<"idle" | "recording" | "done">("idle");
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>(Array(32).fill(0.05));
  const [live, setLive] = useState("");
  const [result, setResult] = useState<(Recording & { url: string }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<VoiceRecorder | null>(null);
  const raf = useRef<number | null>(null);

  const stop = async () => {
    const r = rec.current;
    if (!r) return;
    rec.current = null;
    if (raf.current) cancelAnimationFrame(raf.current);
    const out = await r.stop();
    if (out.durationS < 3) {
      setError(t("too_short"));
      setState("idle");
      return;
    }
    setResult({ ...out, url: URL.createObjectURL(out.blob) });
    setState("done");
  };

  const start = async () => {
    setError(null);
    setResult(null);
    setLive("");
    try {
      const r = new VoiceRecorder(speechTags[locale], setLive);
      await r.start();
      rec.current = r;
      setState("recording");
      const tick = () => {
        if (!rec.current) return;
        const e = rec.current.elapsed();
        setElapsed(e);
        setLevels((l) => [...l.slice(1), Math.max(0.05, rec.current?.level() || 0)]);
        if (e >= maxSeconds) {
          void stop();
          return;
        }
        raf.current = requestAnimationFrame(tick);
      };
      raf.current = requestAnimationFrame(tick);
    } catch {
      setError(t("mic_denied"));
    }
  };

  useEffect(() => () => {
    rec.current?.cancel();
    if (raf.current) cancelAnimationFrame(raf.current);
  }, []);

  const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  return (
    <section className="flex flex-col items-center gap-5 text-center">
      <div className="flex w-full items-start gap-2 text-start">
        <h1 className="font-display flex-1 text-h2 leading-tight">{t("voice_title")}</h1>
        <SpeakerButton text={`${t("voice_title")}. ${t("voice_prompt")}`} auto />
      </div>
      <p className="rounded-md bg-white p-4 text-body text-ink-900">“{t("voice_prompt")}”</p>
      {error && <Banner tone="danger">{error}</Banner>}
      <div className="flex h-16 w-full items-center justify-center gap-1" aria-hidden>
        {levels.map((l, i) => (
          <span key={i} className={cx("w-1.5 rounded-full transition-[height]", state === "recording" ? "bg-terracotta-600" : "bg-ink-300")} style={{ height: `${Math.max(6, l * 64)}px` }} />
        ))}
      </div>
      <p className="font-mono text-2xl" aria-live="polite">
        {mmss(state === "done" && result ? result.durationS : elapsed)} / {mmss(maxSeconds)}
      </p>
      <button
        type="button"
        onClick={() => (state === "recording" ? void stop() : void start())}
        className={cx("flex size-28 items-center justify-center rounded-full text-white shadow-lg", state === "recording" ? "animate-pulse-ring bg-terracotta-600" : "bg-brand")}
        aria-label={state === "recording" ? t("stop") : t("record")}
      >
        {state === "recording" ? <Square className="size-10 fill-current" /> : <Mic className="size-12" />}
      </button>
      <p className="text-ink-600">{state === "recording" ? t("tap_to_stop") : state === "done" ? t("recorded") : t("tap_to_speak")}</p>
      {live && state === "recording" && <p className="text-sm text-ink-600" lang={locale}>{live}</p>}
      {result && (
        <div className="flex w-full flex-col gap-3">
          <audio src={result.url} controls className="w-full" />
          {result.transcript && (
            <p className="rounded-sm bg-white p-3 text-start text-body-s" lang={locale}>
              <span className="block text-xs font-semibold uppercase tracking-wider text-ink-600">{t("we_heard")}</span>
              {result.transcript}
            </p>
          )}
          <div className="flex gap-2">
            <Button variant="secondary" size="L" block icon={<RotateCcw className="size-5" />} onClick={() => void start()}>{t("rerecord")}</Button>
            <Button size="L" block icon={<Play className="flip-rtl size-5" />} onClick={() => onDone(result)}>{t("continue")}</Button>
          </div>
        </div>
      )}
      <button type="button" onClick={onSkip} className="min-h-12 font-semibold text-brand underline">{t("skip_voice")}</button>
    </section>
  );
}
