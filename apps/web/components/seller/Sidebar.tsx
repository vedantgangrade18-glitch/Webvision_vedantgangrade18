"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  CheckCircle2,
  ChevronDown,
  Coins,
  Globe,
  HelpCircle,
  Home,
  Inbox,
  LogOut,
  Package,
  QrCode,
  RotateCcw,
  Scale,
  Settings,
  ShieldCheck,
  TrendingUp,
  User,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { Wordmark } from "@/components/karu/badges";
import { api } from "@/lib/api";
import { cx } from "@/lib/format";
import { useMe } from "@/lib/hooks";

interface SidebarProps {
  onOpenNotices?: () => void;
  onOpenSupport?: () => void;
  className?: string;
  onCloseMobile?: () => void;
}

export function SellerSidebar({
  onOpenNotices,
  onOpenSupport,
  className,
  onCloseMobile,
}: SidebarProps) {
  const t = useTranslations("sell.nav");
  const path = usePathname();
  const router = useRouter();
  const locale = useLocale();
  const { data: me } = useMe();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const { data: notes } = useQuery({
    queryKey: ["notifications-count"],
    queryFn: () => api<{ unread: number }>("/me/notifications?limit=1").catch(() => ({ unread: 5 })),
  });

  const { data: dash } = useQuery({
    queryKey: ["sell-dashboard-counts"],
    queryFn: () =>
      api<{
        profile_completion: number;
        counts?: { to_pack?: number; open_requests?: number };
      }>("/artisan/dashboard").catch(() => ({
        profile_completion: 85,
        counts: { to_pack: 3, open_requests: 2 },
      })),
  });

  const ordersBadge = dash?.counts?.to_pack ?? 3;
  const requestsBadge = dash?.counts?.open_requests ?? 2;
  const unreadNotes = notes?.unread ?? 5;

  const handleLinkClick = () => {
    if (onCloseMobile) onCloseMobile();
  };

  interface NavItem {
    href: string;
    icon: LucideIcon;
    label: string;
    exact?: boolean;
    badge?: number;
  }

  interface NavSection {
    title: string | null;
    items: NavItem[];
  }

  const navSections: NavSection[] = [
    {
      title: null,
      items: [
        { href: "/sell", icon: Home, label: t("home") || "Home", exact: true },
      ],
    },
    {
      title: "MANAGE BUSINESS",
      items: [
        { href: "/sell/orders", icon: Package, label: t("orders") || "Orders", badge: ordersBadge },
        { href: "/sell/orders?tab=returns", icon: RotateCcw, label: "Returns" },
        { href: "/sell/price-advice", icon: TrendingUp, label: "Price advice" },
        { href: "/sell/products", icon: Package, label: t("products") || "Products" },
        { href: "/sell/stock", icon: Scale, label: "Stock & IDs" },
        { href: "/sell/verification", icon: CheckCircle2, label: "Verification" },
        { href: "/sell/payouts", icon: Coins, label: t("payouts") || "Payouts" },
        { href: "/sell/requests", icon: Inbox, label: t("requests") || "Requests", badge: requestsBadge },
      ],
    },
    {
      title: "GROW",
      items: [
        { href: "/sell/share", icon: QrCode, label: "Share & QR" },
        { href: "/sell/passport", icon: ShieldCheck, label: t("passport") || "Passport" },
        { href: "/sell/settings", icon: Settings, label: t("settings") || "Settings" },
      ],
    },
  ];

  return (
    <aside
      className={cx(
        "flex flex-col w-[232px] shrink-0 bg-[#1B1F2E] text-[#C9CCD6] h-full overflow-y-auto select-none border-e border-[#2A3050]/50 custom-scrollbar z-30",
        className
      )}
    >
      {/* Top Artisan User Profile Block */}
      <div className="p-3 border-b border-[#2A3050]/60 relative">
        <button
          type="button"
          onClick={() => setUserMenuOpen((v) => !v)}
          className="flex items-center gap-2.5 w-full text-start p-1.5 rounded-md hover:bg-[#2A3050]/60 transition-colors"
          aria-expanded={userMenuOpen}
        >
          {/* Avatar with completion ring */}
          <div className="relative size-8 shrink-0 rounded-full bg-[#2A3050] flex items-center justify-center text-white ring-2 ring-[#4B3BD1]">
            <User className="size-4.5 text-white/90" />
            <span className="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full bg-[#16A34A] ring-2 ring-[#1B1F2E]" />
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold text-white truncate leading-tight">
              {me?.display_name || "Vedant (Master Weaver)"}
            </p>
            <p className="text-[11px] text-[#7C8196] truncate">
              {dash?.profile_completion ?? 85}% profile completed
            </p>
          </div>
          <ChevronDown className={cx("size-3.5 text-[#7C8196] transition-transform", userMenuOpen && "rotate-180")} />
        </button>

        {/* User dropdown popup */}
        {userMenuOpen && (
          <div className="absolute top-full start-3 end-3 mt-1 py-1.5 bg-[#23283B] border border-[#323957] rounded-lg shadow-xl z-50 text-[13px] text-white">
            <Link
              href="/sell/passport"
              onClick={() => {
                setUserMenuOpen(false);
                handleLinkClick();
              }}
              className="flex items-center gap-2 px-3 py-2 hover:bg-[#2A3050] text-[#C9CCD6] hover:text-white"
            >
              <ShieldCheck className="size-4 text-[#4B3BD1]" />
              <span>View passport & KYC</span>
            </Link>
            <Link
              href="/sell/settings"
              onClick={() => {
                setUserMenuOpen(false);
                handleLinkClick();
              }}
              className="flex items-center gap-2 px-3 py-2 hover:bg-[#2A3050] text-[#C9CCD6] hover:text-white"
            >
              <Globe className="size-4 text-[#4B3BD1]" />
              <span>Change language ({locale.toUpperCase()})</span>
            </Link>
            <div className="my-1 border-t border-[#323957]" />
            <button
              type="button"
              onClick={() => {
                setUserMenuOpen(false);
                router.push("/sell/start");
              }}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-red-500/10 text-red-400 text-start"
            >
              <LogOut className="size-4" />
              <span>Log out</span>
            </button>
          </div>
        )}

        {/* Notices & Support dual action buttons */}
        <div className="grid grid-cols-2 gap-2 mt-2.5">
          <button
            type="button"
            onClick={onOpenNotices}
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-[12px] font-medium border border-[#323957] hover:bg-[#2A3050] text-[#C9CCD6] hover:text-white transition-colors"
          >
            <Bell className="size-3.5 text-[#4B3BD1]" />
            <span>Notices</span>
            {unreadNotes > 0 && (
              <span className="ms-0.5 px-1.5 py-0.2 rounded-full bg-[#4B3BD1] text-white text-[10px] font-bold">
                {unreadNotes}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={onOpenSupport}
            className="flex items-center justify-center gap-1.5 px-2 py-1.5 rounded text-[12px] font-medium border border-[#323957] hover:bg-[#2A3050] text-[#C9CCD6] hover:text-white transition-colors"
          >
            <HelpCircle className="size-3.5 text-[#D97706]" />
            <span>Support</span>
          </button>
        </div>
      </div>

      {/* Main Navigation List */}
      <nav className="flex-1 py-3 px-2 flex flex-col gap-4">
        {navSections.map((sec, sIdx) => (
          <div key={sIdx} className="flex flex-col gap-0.5">
            {sec.title && (
              <p className="px-2.5 py-1 text-[11px] font-bold tracking-wider text-[#7C8196] uppercase">
                {sec.title}
              </p>
            )}
            {sec.items.map((it) => {
              const active = it.exact
                ? path === it.href
                : it.href.includes("?")
                ? path + (typeof window !== "undefined" ? window.location.search : "") === it.href
                : path.startsWith(it.href) && it.href !== "/sell";
              return (
                <Link
                  key={it.href}
                  href={it.href}
                  onClick={handleLinkClick}
                  className={cx(
                    "flex items-center justify-between h-9 px-2.5 rounded-md text-[13.5px] font-medium transition-colors group",
                    active
                      ? "bg-[#2A3050] text-white font-semibold shadow-xs"
                      : "text-[#C9CCD6] hover:bg-[#23283B] hover:text-white"
                  )}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <it.icon
                      className={cx(
                        "size-4.5 shrink-0 transition-colors",
                        active ? "text-[#4B3BD1] stroke-[2.2]" : "text-[#7C8196] group-hover:text-[#C9CCD6]"
                      )}
                    />
                    <span className="truncate">{it.label}</span>
                  </div>
                  {it.badge !== undefined && it.badge > 0 && (
                    <span
                      className={cx(
                        "px-1.5 py-0.5 text-[10px] font-bold rounded-full",
                        active ? "bg-[#4B3BD1] text-white" : "bg-[#2A3050] text-[#C9CCD6]"
                      )}
                    >
                      {it.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Sidebar Footer: Meesho Wordmark */}
      <div className="p-3.5 border-t border-[#2A3050]/60 flex items-center justify-between text-xs text-[#7C8196]">
        <div className="flex flex-col">
          <Wordmark light href="/sell" />
          <span className="text-[11px] text-[#7C8196] font-medium mt-0.5">Meesho Supplier Panel</span>
        </div>
        <span className="text-[10px] uppercase font-bold tracking-widest text-[#4B3BD1] bg-[#4B3BD1]/20 px-1.5 py-0.5 rounded">
          LIVE
        </span>
      </div>
    </aside>
  );
}
