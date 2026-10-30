"use client";

import { useQuery } from "@tanstack/react-query";
import { MapPin, Phone, QrCode, Truck } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { useToast } from "@/components/toast";
import { Banner, Button, EmptyState, Field, Input, Sheet, Skeleton, Tabs } from "@/components/ui";
import { api } from "@/lib/api";
import { date, inr } from "@/lib/format";
import type { ImageSet } from "@/lib/types";

interface ArtisanOrder {
  id: string;
  order_number: string;
  status: string;
  title: string;
  image: ImageSet | null;
  price_inr: number;
  karu_id: string | null;
  paid_at: string | null;
  buyer: { first_name: string; city: string | null };
  ship_to: Record<string, string | null>;
  courier: string | null;
  tracking_no: string | null;
  shipped_at: string | null;
  return: { id: string; status: string; reason: string; details: string | null } | null;
}

type G = "to_pack" | "shipped" | "delivered" | "returns";

/** A13: tabs to pack / shipped / delivered / returns; mark shipped with optional courier + tracking. */
export default function ArtisanOrdersPage() {
  return <AuthGate require="artisan">{() => <Orders />}</AuthGate>;
}

function Orders() {
  const t = useTranslations("sell.orders");
  const locale = useLocale();
  const toast = useToast();
  const [tab, setTab] = useState<G>("to_pack");
  const [shipping, setShipping] = useState<ArtisanOrder | null>(null);
  const { data, isLoading, refetch } = useQuery({ queryKey: ["artisan-orders", tab], queryFn: () => api<{ items: ArtisanOrder[]; counts: Record<G, number> }>(`/artisan/orders?status=${tab}`) });
  return (
    <SellPage title={t("title")}>
      <Tabs value={tab} onChange={setTab} tabs={(["to_pack", "shipped", "delivered", "returns"] as G[]).map((g) => ({ value: g, label: t(`tab.${g}`), count: g === "to_pack" || g === "returns" ? data?.counts[g] : undefined }))} />
      {isLoading ? (
        <Skeleton className="h-48" />
      ) : !data?.items.length ? (
        <EmptyState art="basket" title={t(`empty.${tab}`)} />
      ) : (
        <ul className="flex flex-col gap-3">
          {data.items.map((o) => (
            <li key={o.id} className="flex flex-col gap-3 rounded-md border border-ink-100 bg-white p-4">
              <div className="flex gap-3">
                {o.image?.thumb && <img src={o.image.thumb} alt="" className="aspect-[4/5] w-20 rounded-sm object-cover" />}
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <p className="font-semibold leading-snug">{o.title}</p>
                  <p className="text-body-s">{inr(o.price_inr)} · {o.order_number}</p>
                  <p className="text-sm text-ink-600">{t("buyer", { name: o.buyer.first_name, city: o.buyer.city || "" })} · {date(o.paid_at, locale)}</p>
                </div>
              </div>
              {o.karu_id && (
                <p className="flex items-center gap-2 rounded-sm bg-brand-soft p-3 text-body-s font-semibold text-brand">
                  <QrCode className="size-5" /> {t("attach_tag", { id: o.karu_id })}
                </p>
              )}
              {tab === "to_pack" && (
                <details className="rounded-sm bg-khadi-50 p-3 text-body-s">
                  <summary className="cursor-pointer font-semibold">{t("address")}</summary>
                  <p className="mt-2 flex gap-2"><MapPin className="size-4 shrink-0" />{[o.ship_to.name, o.ship_to.line1, o.ship_to.line2, o.ship_to.city, o.ship_to.state, o.ship_to.pin].filter(Boolean).join(", ")}</p>
                  <p className="flex gap-2"><Phone className="size-4" />{o.ship_to.phone}</p>
                </details>
              )}
              {o.shipped_at && <p className="text-sm text-ink-600">{t("shipped_on", { date: date(o.shipped_at, locale) })} {o.courier ? `· ${o.courier}` : ""} {o.tracking_no ? `· ${o.tracking_no}` : ""}</p>}
              {o.return && (
                <Banner tone="warn" action={o.return.status === "requested" ? (
                  <Button size="S" onClick={async () => { await api(`/artisan/returns/${o.return!.id}/receive`, { method: "POST" }); toast(t("return_received")); void refetch(); }}>{t("got_it_back")}</Button>
                ) : undefined}>
                  {t(`return.${o.return.status}`)} · {t(`reason.${o.return.reason}`)}
                </Banner>
              )}
              {tab === "to_pack" && <Button size="L" icon={<Truck className="size-5" />} onClick={() => setShipping(o)}>{t("mark_shipped")}</Button>}
            </li>
          ))}
        </ul>
      )}
      <ShipSheet order={shipping} onClose={() => setShipping(null)} onDone={() => { setShipping(null); void refetch(); toast(t("shipped_toast")); }} />
    </SellPage>
  );
}

function ShipSheet({ order, onClose, onDone }: { order: ArtisanOrder | null; onClose: () => void; onDone: () => void }) {
  const t = useTranslations("sell.orders");
  const [courier, setCourier] = useState("");
  const [tracking, setTracking] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Sheet open={!!order} onClose={onClose} title={t("mark_shipped")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!order) return;
          setBusy(true);
          try {
            await api(`/artisan/orders/items/${order.id}/ship`, { method: "POST", body: { courier: courier || null, tracking_no: tracking || null } });
            onDone();
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label={t("courier")} hint={t("optional")}><Input value={courier} onChange={(e) => setCourier(e.target.value)} placeholder="India Post" /></Field>
        <Field label={t("tracking")} hint={t("optional")}><Input value={tracking} onChange={(e) => setTracking(e.target.value)} /></Field>
        <Button type="submit" size="L" loading={busy}>{t("confirm_shipped")}</Button>
      </form>
    </Sheet>
  );
}
