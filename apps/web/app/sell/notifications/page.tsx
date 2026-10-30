"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { EmptyState, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { cx, timeAgo } from "@/lib/format";

export default function NotificationsPage() {
  return <AuthGate>{() => <Notes />}</AuthGate>;
}

function Notes() {
  const t = useTranslations("sell.notifications");
  const tc = useTranslations("common");
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: () => api<{ unread: number; items: { id: string; body: string; link: string | null; created_at: string; read: boolean }[] }>("/me/notifications?limit=50"),
  });
  useEffect(() => {
    if (data?.unread) void api("/me/notifications/read", { method: "POST", body: {} }).then(() => qc.invalidateQueries({ queryKey: ["notifications"], exact: true }));
  }, [data?.unread, qc]);
  return (
    <SellPage title={t("title")}>
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : !data?.items.length ? (
        <EmptyState title={t("none")} />
      ) : (
        <ul className="flex flex-col gap-2">
          {data.items.map((n) => {
            const body = (
              <div className={cx("rounded-md border bg-white p-4", n.read ? "border-ink-100" : "border-brand/40")}>
                <p className="text-body-s">{n.body}</p>
                <p className="mt-1 text-xs text-ink-600">{timeAgo(n.created_at, (k, v) => tc(k, v))}</p>
              </div>
            );
            return <li key={n.id}>{n.link ? <Link href={n.link}>{body}</Link> : body}</li>;
          })}
        </ul>
      )}
    </SellPage>
  );
}
