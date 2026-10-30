"use client";

import { MessageCircle, Phone } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { SellPage } from "@/components/artisan/shell";
import { SpeakerButton } from "@/components/karu/voice";
import { speechTags, type Locale } from "@/i18n/config";

const HELP_PHONE = process.env.NEXT_PUBLIC_HELP_PHONE || "";

/** A18: short voice-narrated how-tos per main task + call/WhatsApp Karu help. */
export default function HelpPage() {
  const t = useTranslations("sell.help");
  const locale = useLocale() as Locale;
  const topics = ["list", "verify", "price", "ship", "payout", "share"] as const;
  return (
    <SellPage title={t("title")} back="/sell/passport">
      <ul className="flex flex-col gap-3">
        {topics.map((k) => (
          <li key={k} className="flex items-start gap-3 rounded-md border border-ink-100 bg-white p-4">
            <div className="flex-1">
              <h2 className="font-semibold">{t(`${k}.title`)}</h2>
              <p className="text-body-s text-ink-600">{t(`${k}.body`)}</p>
            </div>
            <SpeakerButton text={`${t(`${k}.title`)}. ${t(`${k}.body`)}`} lang={speechTags[locale]} />
          </li>
        ))}
      </ul>
      {HELP_PHONE ? (
        <div className="grid grid-cols-2 gap-2">
          <a href={`tel:${HELP_PHONE}`} className="flex min-h-14 items-center justify-center gap-2 rounded-sm bg-brand font-semibold text-white"><Phone className="size-5" /> {t("call")}</a>
          <a href={`https://wa.me/${HELP_PHONE.replace(/\D/g, "")}`} className="flex min-h-14 items-center justify-center gap-2 rounded-sm bg-peacock-600 font-semibold text-white"><MessageCircle className="size-5" /> WhatsApp</a>
        </div>
      ) : (
        <p className="text-sm text-ink-600">{t("contact_soon")}</p>
      )}
    </SellPage>
  );
}
