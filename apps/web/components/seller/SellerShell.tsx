"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  CheckCircle2,
  ChevronRight,
  Headphones,
  Home,
  Inbox,
  MessageCircle,
  Package,
  PhoneCall,
  Plus,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { type ReactNode, useState } from "react";
import { SellerSidebar } from "@/components/seller/Sidebar";
import { UploadQueueBanner } from "@/components/artisan/shell";
import { cx } from "@/lib/format";
import { useMe } from "@/lib/hooks";

interface SellerShellProps {
  children: ReactNode;
}

export function SellerShell({ children }: SellerShellProps) {
  const t = useTranslations("sell.nav");
  const path = usePathname();
  const { data: me } = useMe();

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [noticesOpen, setNoticesOpen] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);

  // Exclude shell on onboarding route
  const isStart = path.startsWith("/sell/start");
  if (isStart) {
    return <div className="min-h-dvh bg-[#F1F2F6]">{children}</div>;
  }

  return (
    <div className="min-h-dvh bg-[#F1F2F6] flex flex-row relative antialiased font-sans text-[#111827]">
      {/* 1. Desktop Fixed Sidebar (232px, hidden on < lg) */}
      <div className="hidden lg:block w-[232px] shrink-0 sticky top-0 h-dvh">
        <SellerSidebar
          onOpenNotices={() => setNoticesOpen(true)}
          onOpenSupport={() => setSupportOpen(true)}
        />
      </div>

      {/* 2. Mobile Drawer Sidebar (< lg) */}
      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="relative w-[260px] max-w-[80%] h-full bg-[#1B1F2E] z-10 shadow-2xl flex flex-col">
            <div className="p-3 flex justify-end">
              <button
                type="button"
                onClick={() => setMobileSidebarOpen(false)}
                className="p-1 rounded text-[#7C8196] hover:text-white"
              >
                <X className="size-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <SellerSidebar
                onOpenNotices={() => {
                  setMobileSidebarOpen(false);
                  setNoticesOpen(true);
                }}
                onOpenSupport={() => {
                  setMobileSidebarOpen(false);
                  setSupportOpen(true);
                }}
                onCloseMobile={() => setMobileSidebarOpen(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* 3. Main Content Wrapper */}
      <div className="flex-1 flex flex-col min-w-0 min-h-dvh">
        {/* Offline & Upload Sync Queue Banner */}
        <UploadQueueBanner />

        {/* Page Content View */}
        <main className="flex-1 pb-20 lg:pb-8 flex flex-col">
          {children}
        </main>

        {/* Mobile Bottom Navigation (< lg) */}
        <nav
          className="fixed inset-x-0 bottom-0 z-40 border-t border-[#E3E5EC] bg-white pb-[env(safe-area-inset-bottom)] lg:hidden shadow-lg"
          aria-label="Artisan mobile navigation"
        >
          <ul className="mx-auto grid max-w-lg grid-cols-5 items-end">
            <li>
              <Link
                href="/sell"
                className={cx(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold",
                  path === "/sell" ? "text-[#4B3BD1]" : "text-[#6B7080]"
                )}
              >
                <Home className="size-5" />
                <span>Home</span>
              </Link>
            </li>
            <li>
              <Link
                href="/sell/orders"
                className={cx(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold",
                  path.startsWith("/sell/orders") ? "text-[#4B3BD1]" : "text-[#6B7080]"
                )}
              >
                <Package className="size-5" />
                <span>Orders</span>
              </Link>
            </li>
            <li className="flex justify-center">
              <Link
                href="/sell/new"
                className="-mt-5 flex size-13 items-center justify-center rounded-full bg-[#4B3BD1] text-white shadow-lg ring-4 ring-white hover:bg-[#3A2DB0] active:scale-95 transition-transform"
                aria-label="New Product"
              >
                <Plus className="size-6" />
              </Link>
            </li>
            <li>
              <Link
                href="/sell/requests"
                className={cx(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold",
                  path.startsWith("/sell/requests") ? "text-[#4B3BD1]" : "text-[#6B7080]"
                )}
              >
                <Inbox className="size-5" />
                <span>Requests</span>
              </Link>
            </li>
            <li>
              <Link
                href="/sell/passport"
                className={cx(
                  "flex min-h-14 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold",
                  ["/sell/passport", "/sell/settings", "/sell/payouts"].some((p) =>
                    path.startsWith(p)
                  )
                    ? "text-[#4B3BD1]"
                    : "text-[#6B7080]"
                )}
              >
                <UserRound className="size-5" />
                <span>Passport</span>
              </Link>
            </li>
          </ul>
        </nav>
      </div>

      {/* 4. Right Side Drawer: Notices (Notifications) */}
      {noticesOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-2xs transition-opacity"
            onClick={() => setNoticesOpen(false)}
          />
          <div className="relative w-full max-w-md h-full bg-white shadow-2xl z-10 flex flex-col border-s border-[#E3E5EC] animate-in slide-in-from-right duration-200">
            <div className="p-4 border-b border-[#E3E5EC] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell className="size-4 text-[#4B3BD1]" />
                <h3 className="font-semibold text-[15px] text-[#111827]">Artisan Notices</h3>
              </div>
              <button
                type="button"
                onClick={() => setNoticesOpen(false)}
                className="p-1 rounded text-[#6B7080] hover:text-[#111827] hover:bg-[#F1F2F6]"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 text-[13px]">
              <div className="p-3 rounded-lg border border-[#EFEDFC] bg-[#F8F7FD] flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[#4B3BD1]">Meesho Quality Verification Complete</span>
                  <span className="text-[11px] text-[#7C8196]">20m ago</span>
                </div>
                <p className="text-[12px] text-[#5C554D]">
                  Your Bhagalpuri Silk Saree passed catalog verification. Meesho Product ID generated!
                </p>
              </div>

              <div className="p-3 rounded-lg border border-[#F3D9CB] bg-[#FBEDE6] flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[#B9532E]">Order Ready to Pack</span>
                  <span className="text-[11px] text-[#7C8196]">2h ago</span>
                </div>
                <p className="text-[12px] text-[#5C554D]">
                  Buyer in Bengaluru purchased 1 piece of Terracotta Planter. Pack with physical tag sheet.
                </p>
              </div>

              <div className="p-3 rounded-lg border border-[#E3E5EC] bg-white flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[#111827]">Bank Payout Released</span>
                  <span className="text-[11px] text-[#7C8196]">Yesterday</span>
                </div>
                <p className="text-[12px] text-[#5C554D]">
                  ₹2,800 transferred to your linked UPI account with 0% commission deducted.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. Right Side Drawer: Support */}
      {supportOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-2xs transition-opacity"
            onClick={() => setSupportOpen(false)}
          />
          <div className="relative w-full max-w-md h-full bg-white shadow-2xl z-10 flex flex-col border-s border-[#E3E5EC] animate-in slide-in-from-right duration-200">
            <div className="p-4 border-b border-[#E3E5EC] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Headphones className="size-4 text-[#D97706]" />
                <h3 className="font-semibold text-[15px] text-[#111827]">Artisan Support Helpline</h3>
              </div>
              <button
                type="button"
                onClick={() => setSupportOpen(false)}
                className="p-1 rounded text-[#6B7080] hover:text-[#111827] hover:bg-[#F1F2F6]"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 text-[13px]">
              {/* WhatsApp direct */}
              <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50/50 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-emerald-800 font-semibold">
                  <MessageCircle className="size-4.5 text-emerald-600" />
                  <span>WhatsApp Artisan Concierge</span>
                </div>
                <p className="text-[12px] text-emerald-900 leading-normal">
                  Send photos or voice notes in Hindi, English, Gujarati, Tamil, Marathi, Punjabi, Bengali or Urdu.
                </p>
                <a
                  href="https://wa.me/919999999999"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[12.5px]"
                >
                  <span>Chat on WhatsApp</span>
                  <ChevronRight className="size-3.5" />
                </a>
              </div>

              {/* Toll-free phone */}
              <div className="p-4 rounded-lg border border-[#E3E5EC] bg-white flex flex-col gap-2">
                <div className="flex items-center gap-2 text-[#111827] font-semibold">
                  <PhoneCall className="size-4.5 text-[#4B3BD1]" />
                  <span>Toll-Free Voice Helpline</span>
                </div>
                <p className="text-[12px] text-[#6B7080]">
                  Available 9:00 AM – 7:00 PM IST (Monday to Saturday).
                </p>
                <a
                  href="tel:18001234567"
                  className="font-mono text-[15px] font-bold text-[#4B3BD1] hover:underline"
                >
                  1800-123-4567
                </a>
              </div>

              {/* Video tutorials */}
              <div className="p-4 rounded-lg border border-[#E3E5EC] bg-[#F8F9FC] flex flex-col gap-2">
                <span className="font-semibold text-[#111827]">Meesho Supplier Academy</span>
                <ul className="space-y-2 text-[12.5px] text-[#4B3BD1]">
                  <li className="hover:underline cursor-pointer">▶ How to photograph handloom weaves & apparel</li>
                  <li className="hover:underline cursor-pointer">▶ How to print & attach Meesho shipping labels</li>
                  <li className="hover:underline cursor-pointer">▶ How to verify your GST and supplier credentials</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
