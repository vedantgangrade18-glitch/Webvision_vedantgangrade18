import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { ArtisanShell } from "@/components/artisan/shell";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: { default: "Karu for makers · Studio", template: "%s · Karu Studio" },
};

export default async function SellLayout({ children }: { children: React.ReactNode }) {
  const [locale, messages] = await Promise.all([getLocale(), getMessages()]);
  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <Providers pwa>
        <ArtisanShell>
          {children}
        </ArtisanShell>
      </Providers>
    </NextIntlClientProvider>
  );
}
