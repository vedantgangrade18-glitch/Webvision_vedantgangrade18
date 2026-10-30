import type { Metadata, Viewport } from "next";
import { getLocale } from "next-intl/server";
import { rtlLocales } from "@/i18n/config";
import { fontVariables } from "./fonts";
import "./globals.css";

const SITE = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: "Meesho — Supplier Hub", template: "%s · Meesho" },
  description: "Sell across India with 0% commission. Meesho Supplier & Seller Panel.",
  applicationName: "Meesho",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg", apple: "/icon-192.png" },
};

export const viewport: Viewport = {
  themeColor: "#1F2A6B",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

// The root layout stays provider-free so the QR proof page (/k) ships almost no client JS.
export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  return (
    <html lang={locale} dir={rtlLocales.has(locale) ? "rtl" : "ltr"} className={fontVariables} data-scroll-behavior="smooth">
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
