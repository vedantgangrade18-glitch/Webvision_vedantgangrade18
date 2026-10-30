"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { SellPage } from "@/components/artisan/shell";
import { AuthGate } from "@/components/auth-gate";
import { LanguageSwitcher } from "@/components/karu/language";
import { Button, Card, Sheet, Switch } from "@/components/ui";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

/** A17: language, voice prompts, notifications, hide voice clip, logout, delete account. */
export default function ArtisanSettingsPage() {
  return <AuthGate require="artisan">{(me) => <Settings me={me} />}</AuthGate>;
}

function Settings({ me }: { me: Me }) {
  const t = useTranslations("sell.settings");
  const qc = useQueryClient();
  const router = useRouter();
  const [prefs, setPrefs] = useState(me.notification_prefs);
  const [voice, setVoice] = useState(me.voice_prompts);
  const [confirm, setConfirm] = useState(false);
  const profile = useQuery({ queryKey: ["artisan-profile"], queryFn: () => api<{ show_voice_publicly: boolean }>("/artisan/profile") });
  const patchMe = async (body: Record<string, unknown>) => qc.setQueryData(["me"], await api<Me>("/me", { method: "PATCH", body }));
  return (
    <SellPage title={t("title")} back="/sell/passport">
      <Card className="flex items-center justify-between p-4">
        <span className="font-semibold">{t("language")}</span>
        <LanguageSwitcher signedIn />
      </Card>
      <Card className="flex flex-col gap-5 p-4">
        <Switch checked={voice} onChange={(v) => { setVoice(v); void patchMe({ voice_prompts: v }); }} label={t("voice_prompts")} description={t("voice_prompts_hint")} />
        {profile.data && (
          <Switch
            checked={profile.data.show_voice_publicly}
            onChange={async (v) => { await api("/artisan/profile", { method: "PATCH", body: { show_voice_publicly: v } }); void profile.refetch(); }}
            label={t("show_voice")}
            description={t("show_voice_hint")}
          />
        )}
      </Card>
      <Card className="flex flex-col gap-5 p-4">
        <h2 className="font-semibold">{t("notifications")}</h2>
        {(["whatsapp", "sms", "in_app"] as const).map((k) => (
          <Switch key={k} checked={!!prefs[k]} onChange={(v) => { const next = { ...prefs, [k]: v }; setPrefs(next); void patchMe({ notification_prefs: next }); }} label={t(`channel.${k}`)} />
        ))}
      </Card>
      {/* API download (JSON attachment), not a page — a plain link is intended. */}
      {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
      <a href="/api/v1/me/export" className="font-semibold text-brand underline">{t("export")}</a>
      <Button variant="secondary" size="L" icon={<LogOut className="size-5" />} onClick={async () => { await api("/auth/logout", { method: "POST" }); qc.clear(); router.replace("/"); }}>
        {t("logout")}
      </Button>
      <Button variant="danger" size="L" onClick={() => setConfirm(true)}>{t("delete")}</Button>
      <Sheet open={confirm} onClose={() => setConfirm(false)} title={t("delete")}>
        <p className="mb-4">{t("delete_confirm")}</p>
        <Button variant="danger" block onClick={async () => { await api("/me", { method: "DELETE" }); qc.clear(); router.replace("/"); }}>{t("delete_yes")}</Button>
      </Sheet>
    </SellPage>
  );
}
