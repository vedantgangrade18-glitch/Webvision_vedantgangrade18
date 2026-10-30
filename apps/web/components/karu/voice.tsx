"use client";

import { Loader2, Mic, MicOff, Square, Volume2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { forwardRef, useEffect, useRef, useState, type InputHTMLAttributes } from "react";
import { speechTags, type Locale } from "@/i18n/config";
import { api } from "@/lib/api";
import { cx } from "@/lib/format";
import { useMe, usePublicConfig } from "@/lib/hooks";
import { speak, speechRecognitionSupported, VoiceRecorder } from "@/lib/speech";

type MicState = "idle" | "listening" | "processing" | "error";

/** MicButton: round, indigo; idle / listening (pulsing ring) / processing / error (Part 1 §9.6).
 *  Server STT (POST /stt, ≤ 15 s) when an STT provider is configured, the browser's own speech
 *  recognition otherwise. */
export function MicButton({ onText, size = 48, maxSeconds = 15, label }: { onText: (text: string) => void; size?: number; maxSeconds?: number; label?: string }) {
  const t = useTranslations("voice");
  const locale = useLocale() as Locale;
  const { data: config } = usePublicConfig();
  const [state, setState] = useState<MicState>("idle");
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<VoiceRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stop = async () => {
    if (timer.current) clearTimeout(timer.current);
    const r = rec.current;
    rec.current = null;
    if (!r) return;
    setState("processing");
    try {
      const { blob, transcript } = await r.stop();
      let text = transcript;
      if (config && config.providers.stt !== "fake" && blob.size > 0) {
        const form = new FormData();
        form.append("file", blob, "voice.webm");
        form.append("locale", locale);
        if (transcript) form.append("client_transcript", transcript);
        const res = await api<{ text: string }>("/stt", { method: "POST", form });
        text = res.text || transcript;
      }
      if (!text) {
        setError(t("not_caught"));
        setState("error");
        return;
      }
      onText(text);
      setState("idle");
    } catch {
      setError(t("not_caught"));
      setState("error");
    }
  };

  const start = async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(t("unsupported"));
      setState("error");
      return;
    }
    try {
      const r = new VoiceRecorder(speechTags[locale] || "hi-IN");
      await r.start();
      rec.current = r;
      setState("listening");
      timer.current = setTimeout(() => void stop(), maxSeconds * 1000);
    } catch {
      setError(t("permission_denied"));
      setState("error");
    }
  };

  useEffect(() => () => rec.current?.cancel(), []);

  const unsupported = typeof window !== "undefined" && config?.providers.stt === "fake" && !speechRecognitionSupported();

  return (
    <span className="inline-flex flex-col items-center">
      <button
        type="button"
        onClick={() => (state === "listening" ? void stop() : void start())}
        disabled={state === "processing" || unsupported}
        aria-label={state === "listening" ? t("stop") : label || t("speak")}
        title={unsupported ? t("unsupported") : undefined}
        className={cx(
          "inline-flex shrink-0 items-center justify-center rounded-full text-white transition-colors",
          state === "listening" ? "animate-pulse-ring bg-terracotta-600" : state === "error" ? "bg-danger-600" : "bg-brand hover:bg-brand",
          unsupported && "opacity-40",
        )}
        style={{ width: size, height: size }}
      >
        {state === "processing" ? (
          <Loader2 className="size-5 animate-spin" />
        ) : state === "listening" ? (
          <Square className="size-4 fill-current" />
        ) : state === "error" ? (
          <MicOff className="size-5" />
        ) : (
          <Mic className="size-5" />
        )}
      </button>
      {error && (
        <span role="alert" className="mt-1 max-w-40 text-center text-xs text-danger-600">
          {error}
        </span>
      )}
    </span>
  );
}

/** VoiceField: text input + MicButton + optional speaker (read aloud). */
export const VoiceField = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { onVoice: (text: string) => void; speakText?: string; multiline?: boolean; textareaValue?: string; onTextarea?: (v: string) => void }
>(function VoiceField({ onVoice, speakText, className, multiline, textareaValue, onTextarea, ...rest }, ref) {
  const locale = useLocale() as Locale;
  return (
    <div className="flex items-start gap-2">
      {multiline ? (
        <textarea
          className={cx(
            "min-h-28 w-full rounded-xs border border-ink-300 bg-white px-3 py-2.5 text-base focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20",
            className,
          )}
          value={textareaValue}
          onChange={(e) => onTextarea?.(e.target.value)}
          placeholder={rest.placeholder}
          aria-label={rest["aria-label"]}
          id={rest.id}
        />
      ) : (
        <input
          ref={ref}
          className={cx(
            "min-h-12 w-full rounded-xs border border-ink-300 bg-white px-3 py-2.5 text-base focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20",
            className,
          )}
          {...rest}
        />
      )}
      <MicButton onText={onVoice} />
      {speakText && <SpeakerButton text={speakText} lang={speechTags[locale]} />}
    </div>
  );
});

export function SpeakerButton({ text, lang, auto }: { text: string; lang?: string; auto?: boolean }) {
  const t = useTranslations("voice");
  const locale = useLocale() as Locale;
  const { data: me } = useMe();
  const tag = lang || speechTags[locale];
  useEffect(() => {
    if (auto && me?.voice_prompts) speak(text, tag);
  }, [auto, me?.voice_prompts, text, tag]);
  return (
    <button
      type="button"
      onClick={() => speak(text, tag)}
      className="tap inline-flex items-center justify-center rounded-full text-brand hover:bg-brand-soft"
      aria-label={t("read_aloud")}
    >
      <Volume2 className="size-5" />
    </button>
  );
}
