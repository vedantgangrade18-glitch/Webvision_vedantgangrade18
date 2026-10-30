"use client";

import { useQuery } from "@tanstack/react-query";
import { Landmark, Smartphone } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { MicButton } from "@/components/karu/voice";
import { useToast } from "@/components/toast";
import { Banner, Button, Card, Field, Input, Skeleton, Tabs } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { cx, date } from "@/lib/format";

interface Payouts {
  setup: { status: string; method: string | null; masked: string | null; reason: string | null };
  totals: { on_the_way: string; paid: string };
  items: { id: string; amount: string; status: string; hold_until: string | null; order_number: string; title: string; created_at: string; failure_reason: string | null }[];
}

/** A14 / F10: UPI or bank, KYC through the payment provider, clear status, payout list. */
export default function PayoutsPage() {
  return <AuthGate require="artisan">{() => <PayoutsView />}</AuthGate>;
}

function PayoutsView() {
  const t = useTranslations("sell.payouts");
  const locale = useLocale();
  const { data, isLoading, refetch } = useQuery({ queryKey: ["payouts"], queryFn: () => api<Payouts>("/artisan/payouts") });
  const [editing, setEditing] = useState(false);
  if (isLoading || !data) return <SellPage title={t("title")}><Skeleton className="h-64" /></SellPage>;
  const active = data.setup.status === "active";
  return (
    <SellPage title={t("title")}>
      <div className="grid grid-cols-2 gap-2">
        <Card className="p-4"><p className="text-sm text-ink-600">{t("on_the_way")}</p><p className="text-2xl font-semibold">{data.totals.on_the_way}</p></Card>
        <Card className="p-4"><p className="text-sm text-ink-600">{t("paid")}</p><p className="text-2xl font-semibold">{data.totals.paid}</p></Card>
      </div>
      <Card className="flex flex-col gap-3 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">{t("account")}</h2>
          <span className={cx("rounded-full px-2.5 py-0.5 text-sm font-semibold", active ? "bg-peacock-50 text-peacock-600" : data.setup.status === "failed" ? "bg-danger-50 text-danger-600" : "bg-gold-100")}>
            {t(`status.${data.setup.status}`)}
          </span>
        </div>
        {data.setup.masked && <p className="font-mono">{data.setup.masked}</p>}
        {data.setup.reason && <Banner tone="warn">{t(`reason.${data.setup.reason === "upi_settlement_not_enabled" ? data.setup.reason : "other"}`)}</Banner>}
        {!active || editing ? <PayoutForm onDone={() => { setEditing(false); void refetch(); }} /> : <Button variant="tertiary" onClick={() => setEditing(true)}>{t("change")}</Button>}
        <p className="text-xs text-ink-600">{t("hold_note")}</p>
      </Card>
      <section className="flex flex-col gap-2">
        <h2 className="font-display text-xl">{t("history")}</h2>
        {!data.items.length ? (
          <p className="text-ink-600">{t("none")}</p>
        ) : (
          <ul className="divide-y divide-ink-100 rounded-sm border border-ink-100 bg-white">
            {data.items.map((p) => (
              <li key={p.id} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{p.title}</p>
                  <p className="text-xs text-ink-600">{p.order_number} · {date(p.created_at, locale)}</p>
                  {p.status === "on_hold" && p.hold_until && <p className="text-xs text-ink-600">{t("release_on", { date: date(p.hold_until, locale) })}</p>}
                </div>
                <div className="text-end">
                  <p className="font-semibold">{p.amount}</p>
                  <p className={cx("text-xs font-semibold", p.status === "failed" ? "text-danger-600" : p.status === "released" || p.status === "settled" ? "text-peacock-600" : "text-ink-600")}>{t(`p_status.${p.status}`)}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </SellPage>
  );
}

function PayoutForm({ onDone }: { onDone: () => void }) {
  const t = useTranslations("sell.payouts");
  const toast = useToast();
  const [method, setMethod] = useState<"upi" | "bank">("bank");
  const [vpa, setVpa] = useState("");
  const [acc, setAcc] = useState("");
  const [ifsc, setIfsc] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await api("/artisan/payouts/setup", {
            method: "POST",
            body: method === "upi" ? { method, vpa } : { method, account_number: acc, ifsc: ifsc.toUpperCase(), beneficiary_name: name || null },
          });
          toast(t("saved"));
          onDone();
        } catch (err) {
          setError(err instanceof ApiError && err.code === "validation_error" ? t("check_details") : t("error"));
        } finally {
          setBusy(false);
        }
      }}
    >
      <Tabs value={method} onChange={setMethod} tabs={[{ value: "bank", label: <span className="inline-flex items-center gap-1"><Landmark className="size-4" /> {t("bank")}</span> }, { value: "upi", label: <span className="inline-flex items-center gap-1"><Smartphone className="size-4" /> UPI</span> }]} />
      {error && <Banner tone="danger">{error}</Banner>}
      {method === "upi" ? (
        <Field label={t("vpa")} hint={t("vpa_hint")}><Input value={vpa} onChange={(e) => setVpa(e.target.value.trim())} placeholder="name@bank" required /></Field>
      ) : (
        <>
          <Field label={t("acc")}>
            <div className="flex gap-2"><Input inputMode="numeric" value={acc} onChange={(e) => setAcc(e.target.value.replace(/\D/g, ""))} required /><MicButton onText={(x) => setAcc(x.replace(/\D/g, ""))} /></div>
          </Field>
          <Field label={t("ifsc")} hint={t("ifsc_hint")}><Input value={ifsc} onChange={(e) => setIfsc(e.target.value.toUpperCase())} maxLength={11} required /></Field>
          <Field label={t("holder")}><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
        </>
      )}
      <Button type="submit" size="L" loading={busy}>{t("save")}</Button>
      <p className="text-xs text-ink-600">{t("kyc_note")}</p>
    </form>
  );
}
