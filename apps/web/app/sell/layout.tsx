import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { SellerShell } from "@/components/seller/SellerShell";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: { default: "Sell on Meesho · Supplier Hub", template: "%s · Sell on Meesho" },
};

export default async function SellLayout({ children }: { children: React.ReactNode }) {
  const [locale, messages] = await Promise.all([getLocale(), getMessages()]);
  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <Providers pwa>
        <SellerShell>
          {children}
        </SellerShell>
      </Providers>
    </NextIntlClientProvider>
  );
}
