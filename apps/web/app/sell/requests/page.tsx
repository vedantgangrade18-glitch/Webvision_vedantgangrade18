"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useState } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { MicButton } from "@/components/karu/voice";
import { useToast } from "@/components/toast";
import { Banner, Button, Card, EmptyState, Field, Input, Sheet, Skeleton, Tabs } from "@/components/ui";
import { api } from "@/lib/api";
import type { ImageSet } from "@/lib/types";

interface MakeAgain {
  id: string;
  listing_id: string;
  title: string;
  image: ImageSet | null;
  quantity: number;
  needed_by: string | null;
  note: string | null;
  buyer_first_name: string | null;
  status: string;
  reply: Record<string, unknown> | null;
}
interface Opportunity {
  id: string;
  product_type: string;
  category: string | null;
  quantity: number;
  target_price: string | null;
  deadline: string | null;
  description: string | null;
  my_response: { quantity_offered: number; status: string } | null;
}

/** A16: make-again requests from buyers + bulk opportunities from Karu. */
export default function RequestsPage() {
  return (
    <Suspense>
      <AuthGate require="artisan">{() => <Requests />}</AuthGate>
    </Suspense>
  );
}

function Requests() {
  const t = useTranslations("sell.requests");
  const params = useSearchParams();
  const [tab, setTab] = useState<"make_again" | "bulk">(params.get("tab") === "bulk" ? "bulk" : "make_again");
  const [replying, setReplying] = useState<MakeAgain | null>(null);
  const [joining, setJoining] = useState<Opportunity | null>(null);
  const reqs = useQuery({ queryKey: ["artisan-requests"], queryFn: () => api<{ items: MakeAgain[] }>("/artisan/requests") });
  const bulk = useQuery({ queryKey: ["bulk-opps"], queryFn: () => api<{ eligible: boolean; items: Opportunity[] }>("/artisan/bulk-opportunities") });
  return (
    <SellPage title={t("title")}>
      <Tabs value={tab} onChange={setTab} tabs={[{ value: "make_again", label: t("make_again"), count: reqs.data?.items.filter((r) => r.status === "open").length }, { value: "bulk", label: t("bulk") }]} />
      {tab === "make_again" &&
        (reqs.isLoading ? (
          <Skeleton className="h-40" />
        ) : !reqs.data?.items.length ? (
          <EmptyState art="thread" title={t("none")} body={t("none_body")} />
        ) : (
          <ul className="flex flex-col gap-3">
            {reqs.data.items.map((r) => (
              <li key={r.id} className="flex flex-col gap-3 rounded-md border border-ink-100 bg-white p-4">
                <div className="flex gap-3">
                  {r.image?.thumb && <img src={r.image.thumb} alt="" className="aspect-[4/5] w-16 rounded-xs object-cover" />}
                  <div className="flex-1">
                    <p className="font-semibold">{r.title}</p>
                    <p className="text-body-s">{t("wants", { name: r.buyer_first_name || t("a_buyer"), n: r.quantity })}</p>
                    {r.needed_by && <p className="text-sm text-ink-600">{t("by_date", { date: r.needed_by })}</p>}
                  </div>
                </div>
                {r.note && <p className="rounded-sm bg-khadi-50 p-3 text-body-s">“{r.note}”</p>}
                {r.status === "open" ? (
                  <div className="flex gap-2">
                    <Button block onClick={() => setReplying(r)}>{t("reply")}</Button>
                    <Button
                      variant="tertiary"
                      onClick={async () => {
                        await api(`/artisan/requests/${r.id}/reply`, { method: "POST", body: { action: "decline" } });
                        void reqs.refetch();
                      }}
                    >
                      {t("decline")}
                    </Button>
                  </div>
                ) : (
                  <p className="text-sm font-semibold text-ink-600">{t(`status.${r.status}`)}</p>
                )}
              </li>
            ))}
          </ul>
        ))}
      {tab === "bulk" &&
        (bulk.isLoading ? (
          <Skeleton className="h-40" />
        ) : (
          <div className="flex flex-col gap-3">
            {!bulk.data?.eligible && <Banner tone="info">{t("bulk_verified_only")}</Banner>}
            {!bulk.data?.items.length ? (
              <EmptyState title={t("no_bulk")} />
            ) : (
              bulk.data.items.map((o) => (
                <Card key={o.id} className="flex flex-col gap-2 p-4">
                  <p className="font-semibold">{o.product_type}</p>
                  <p className="text-body-s">{t("bulk_line", { n: o.quantity, deadline: o.deadline || "—" })}</p>
                  {o.target_price && <p className="text-sm text-ink-600">{t("target", { price: o.target_price })}</p>}
                  {o.description && <p className="text-sm">{o.description}</p>}
                  {o.my_response ? (
                    <p className="text-sm font-semibold text-peacock-600">{t("joined", { n: o.my_response.quantity_offered })}</p>
                  ) : (
                    <Button disabled={!bulk.data?.eligible} onClick={() => setJoining(o)}>{t("i_can_make")}</Button>
                  )}
                </Card>
              ))
            )}
          </div>
        ))}
      <ReplySheet req={replying} onClose={() => setReplying(null)} onDone={() => { setReplying(null); void reqs.refetch(); }} />
      <JoinSheet opp={joining} onClose={() => setJoining(null)} onDone={() => { setJoining(null); void bulk.refetch(); }} />
    </SellPage>
  );
}

function ReplySheet({ req, onClose, onDone }: { req: MakeAgain | null; onClose: () => void; onDone: () => void }) {
  const t = useTranslations("sell.requests");
  const toast = useToast();
  const [price, setPrice] = useState("");
  const [days, setDays] = useState("");
  const [msg, setMsg] = useState("");
  return (
    <Sheet open={!!req} onClose={onClose} title={t("reply")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!req) return;
          await api(`/artisan/requests/${req.id}/reply`, { method: "POST", body: { action: "reply", price_inr: price ? Number(price) : null, ready_in_days: days ? Number(days) : null, message: msg || null } });
          toast(t("sent"));
          onDone();
        }}
      >
        <Field label={t("price_each")}><div className="flex gap-2"><Input inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value.replace(/\D/g, ""))} /><MicButton onText={(x) => setPrice(x.replace(/\D/g, ""))} /></div></Field>
        <Field label={t("ready_in")}><div className="flex gap-2"><Input inputMode="numeric" value={days} onChange={(e) => setDays(e.target.value.replace(/\D/g, ""))} /><MicButton onText={(x) => setDays(x.replace(/\D/g, ""))} /></div></Field>
        <Field label={t("message")}><div className="flex gap-2"><Input value={msg} onChange={(e) => setMsg(e.target.value)} /><MicButton onText={setMsg} /></div></Field>
        <Button type="submit" size="L">{t("send")}</Button>
      </form>
    </Sheet>
  );
}

function JoinSheet({ opp, onClose, onDone }: { opp: Opportunity | null; onClose: () => void; onDone: () => void }) {
  const t = useTranslations("sell.requests");
  const [qty, setQty] = useState("");
  const [canMeet, setCanMeet] = useState(true);
  return (
    <Sheet open={!!opp} onClose={onClose} title={t("i_can_make")}>
      <form
        className="flex flex-col gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!opp) return;
          await api(`/artisan/bulk-opportunities/${opp.id}/respond`, { method: "POST", body: { quantity_offered: Number(qty), can_meet_deadline: canMeet } });
          onDone();
        }}
      >
        <Field label={t("how_many")}><Input inputMode="numeric" required value={qty} onChange={(e) => setQty(e.target.value.replace(/\D/g, ""))} /></Field>
        <label className="flex items-center gap-2"><input type="checkbox" className="size-5 accent-brand" checked={canMeet} onChange={(e) => setCanMeet(e.target.checked)} />{t("can_meet")}</label>
        <Button type="submit" size="L" disabled={!qty}>{t("join")}</Button>
      </form>
    </Sheet>
  );
}
