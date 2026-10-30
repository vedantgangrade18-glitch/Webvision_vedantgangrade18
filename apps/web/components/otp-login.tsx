"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { cx } from "@/lib/format";
import type { Me } from "@/lib/types";

interface SendResult {
  sent: boolean;
  channel: "sms" | "email";
  resend_after_s: number;
  dev_code?: string;
}

/** A02/A03 and B13: 6 separate 52px boxes with auto-advance and paste (spec §6.3 / B13). */
export function OtpLogin({
  mode = "phone",
  big,
  onDone,
}: {
  mode?: "phone" | "email";
  big?: boolean;
  onDone: (r: { user: Me; is_new: boolean }) => void;
}) {
  const t = useTranslations("auth");
  const locale = useLocale();
  const qc = useQueryClient();
  const [step, setStep] = useState<"dest" | "code">("dest");
  const [dest, setDest] = useState("");
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devCode, setDevCode] = useState<string | null>(null);
  const [wait, setWait] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (wait <= 0) return;
    const id = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(id);
  }, [wait]);

  const body = () =>
    mode === "phone"
      ? { phone: dest.startsWith("+") ? dest : `+91${dest.replace(/\D/g, "")}` }
      : { email: dest.trim() };

  const send = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api<SendResult>("/auth/otp/send", { method: "POST", body: { ...body(), locale } });
      setStep("code");
      setWait(r.resend_after_s);
      setDevCode(r.dev_code || null);
      setDigits(["", "", "", "", "", ""]);
      setTimeout(() => inputRefs.current[0]?.focus(), 100);

      if (mode === "phone" && "OTPCredential" in window) {
        const ac = new AbortController();
        setTimeout(() => ac.abort(), 120_000);
        navigator.credentials
          .get({ otp: { transport: ["sms"] }, signal: ac.signal } as CredentialRequestOptions)
          .then((cred) => {
            const c = (cred as unknown as { code?: string })?.code;
            if (c && c.length === 6) {
              const arr = c.split("");
              setDigits(arr);
              void verify(c);
            }
          })
          .catch(() => undefined);
      }
    } catch (e) {
      setError(t(`errors.${e instanceof ApiError ? mapError(e.code) : "generic"}`));
    } finally {
      setBusy(false);
    }
  };

  const verify = async (codeStr?: string) => {
    const value = codeStr || digits.join("");
    if (value.length !== 6) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ user: Me; is_new: boolean }>("/auth/otp/verify", {
        method: "POST",
        body: { ...body(), code: value, locale },
      });
      qc.setQueryData(["me"], r.user);
      onDone(r);
    } catch (e) {
      const errCode = e instanceof ApiError ? e.code : "generic";
      const left = e instanceof ApiError ? (e.details.attempts_left as number | undefined) : undefined;
      setError(
        errCode === "otp_wrong_code" && left !== undefined
          ? t("errors.wrong_code_left", { n: left })
          : t(`errors.${mapError(errCode)}`)
      );
      setDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setBusy(false);
    }
  };

  const handleDigitChange = (index: number, val: string) => {
    const char = val.replace(/\D/g, "").slice(-1);
    const newDigits = [...digits];
    newDigits[index] = char;
    setDigits(newDigits);

    if (char && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    if (newDigits.every((d) => d !== "")) {
      void verify(newDigits.join(""));
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted) {
      const arr = pasted.split("");
      while (arr.length < 6) arr.push("");
      setDigits(arr);
      if (pasted.length === 6) {
        void verify(pasted);
      } else {
        inputRefs.current[pasted.length]?.focus();
      }
    }
  };

  const size = big ? "L" : "M";

  return (
    <div className="flex flex-col gap-4">
      {error && <Banner tone="danger">{error}</Banner>}

      {step === "dest" ? (
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          {mode === "phone" ? (
            <Field label={t("phone_label") || "Mobile Phone Number"} htmlFor="otp-phone" hint={t("phone_hint") || "We will send a 6-digit verification code"}>
              <div className="flex gap-2" dir="ltr">
                <span className={cx("flex items-center rounded-xs border border-line bg-surface-alt px-3 font-semibold text-ink-900", big ? "text-xl" : "text-body")}>
                  +91
                </span>
                <Input
                  id="otp-phone"
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel-national"
                  maxLength={10}
                  required
                  value={dest}
                  onChange={(e) => setDest(e.target.value.replace(/\D/g, ""))}
                  className={big ? "text-xl tracking-widest" : "text-body tracking-wider"}
                  placeholder="98765 43210"
                />
              </div>
            </Field>
          ) : (
            <Field label={t("email_label") || "Email Address"} htmlFor="otp-email">
              <Input
                id="otp-email"
                type="email"
                autoComplete="email"
                required
                value={dest}
                onChange={(e) => setDest(e.target.value)}
                placeholder="name@example.com"
              />
            </Field>
          )}

          <Button
            type="submit"
            variant="primary"
            size={size}
            block
            loading={busy}
            disabled={mode === "phone" ? dest.length !== 10 : !dest.includes("@")}
          >
            {t("send_code") || "Send code"}
          </Button>
        </form>
      ) : (
        <form
          className="flex flex-col gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            void verify();
          }}
        >
          <div className="text-center">
            <p className="text-body-s text-muted">
              {t("code_sent_to", { dest: mode === "phone" ? `+91 ${dest}` : dest })}
            </p>
          </div>

          {devCode && (
            <Banner
              tone="warn"
              action={
                <Button
                  size="S"
                  variant="secondary"
                  onClick={() => {
                    const arr = devCode.split("");
                    setDigits(arr);
                    void verify(devCode);
                  }}
                >
                  {t("use_code") || "Use code"}
                </Button>
              }
            >
              {t("dev_code", { code: devCode })}
            </Banner>
          )}

          {/* 6 Separate 52px Boxes */}
          <div className="flex justify-center gap-2 sm:gap-3" dir="ltr">
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => {
                  inputRefs.current[i] = el;
                }}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleDigitChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                onPaste={handlePaste}
                className="size-13 rounded-xs border border-line bg-surface text-center font-mono text-2xl font-semibold text-ink-900 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 transition-all"
                aria-label={`Digit ${i + 1}`}
              />
            ))}
          </div>

          <Button
            type="submit"
            variant="primary"
            size={size}
            block
            loading={busy}
            disabled={digits.some((d) => d === "")}
          >
            {t("verify") || "Verify code"}
          </Button>

          <div className="flex items-center justify-between text-caption pt-1">
            <button
              type="button"
              className="text-brand underline underline-offset-4 hover:text-brand-hover cursor-pointer"
              onClick={() => setStep("dest")}
            >
              {t("change") || "Change number"}
            </button>
            <button
              type="button"
              className="text-brand underline underline-offset-4 hover:text-brand-hover disabled:text-muted disabled:no-underline cursor-pointer"
              disabled={wait > 0 || busy}
              onClick={() => void send()}
            >
              {wait > 0 ? t("resend_in", { s: wait }) : t("resend") || "Resend code"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function mapError(code: string): string {
  const known = [
    "invalid_phone",
    "invalid_email",
    "otp_rate_limited",
    "resend_too_soon",
    "otp_expired",
    "otp_too_many_attempts",
    "otp_not_found",
    "account_suspended",
    "account_deleted",
    "otp_wrong_code",
  ];
  return known.includes(code) ? code : "generic";
}
