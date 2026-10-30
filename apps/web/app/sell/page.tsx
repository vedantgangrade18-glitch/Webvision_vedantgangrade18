"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Coins,
  ExternalLink,
  Eye,
  Inbox,
  Package,
  Plus,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
} from "lucide-react";
import Link from "next/link";
import { Suspense, useState } from "react";
import { PageHeader } from "@/components/seller/PageHeader";
import { PromoBanner } from "@/components/seller/PromoBanner";
import { StatTile } from "@/components/seller/StatTile";
import { api } from "@/lib/api";
import { inr } from "@/lib/format";
import { useMe } from "@/lib/hooks";

export default function SellerHomePage() {
  return (
    <Suspense>
      <SellerHomeContent />
    </Suspense>
  );
}

function SellerHomeContent() {
  const { data: me } = useMe();
  const [profileDismissed, setProfileDismissed] = useState(false);

  const { data: dash } = useQuery({
    queryKey: ["sell-dashboard-home"],
    queryFn: () =>
      api<{
        greeting_name: string;
        profile_completion: number;
        summary: {
          views_today: number;
          orders_to_ship: number;
          money_on_the_way: string;
        };
        open_requests: number;
      }>("/artisan/dashboard").catch(() => ({
        greeting_name: "Vedant",
        profile_completion: 85,
        summary: {
          views_today: 148,
          orders_to_ship: 3,
          money_on_the_way: "₹14,200",
        },
        open_requests: 2,
      })),
  });

  const d = dash || {
    greeting_name: "Vedant",
    profile_completion: 85,
    summary: {
      views_today: 148,
      orders_to_ship: 3,
      money_on_the_way: "₹14,200",
    },
    open_requests: 2,
  };

  return (
    <div className="flex flex-col min-w-0">
      <PageHeader
        title="Seller Dashboard"
        howToText="How to manage your workshop"
      />

      <div className="max-w-[1240px] w-full mx-auto px-4 sm:px-6 py-5 flex flex-col gap-5">
        {/* Top Greeting & Banner */}
        <div className="p-5 rounded-lg border border-[#E3E5EC] bg-white shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#4B3BD1]">
              Artisan Workshop Control Center
            </span>
            <h1 className="text-[20px] font-bold text-[#111827] mt-0.5">
              Namaste, {me?.display_name || d.greeting_name || "Master Artisan"}
            </h1>
            <p className="text-[12.5px] text-[#6B7080] mt-0.5">
              Welcome back to your workshop dashboard. Here is what is happening today.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Link
              href="/sell/new"
              className="px-4 py-2 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13px] font-semibold transition-colors shadow-xs flex items-center gap-1.5"
            >
              <Plus className="size-4" />
              <span>+ Add product</span>
            </Link>
          </div>
        </div>

        {/* PromoBanner */}
        <PromoBanner
          id="home-payout-setup"
          headline="Finish your bank payout details to receive ₹14,200"
          description="Your escrow funds are ready for direct NEFT/UPI settlement with 0% Meesho commission."
          actionText="Set up payouts"
          actionHref="/sell/payouts"
        />

        {/* Overview StatTiles */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <StatTile
            label="Today's views"
            value={d.summary.views_today}
            delta="+18% vs last week"
          />
          <StatTile
            label="Orders to pack"
            value={d.summary.orders_to_ship}
            delta="Ready for dispatch"
            active={d.summary.orders_to_ship > 0}
          />
          <StatTile
            label="Money on the way"
            value={d.summary.money_on_the_way}
            delta="Direct UPI transfer"
          />
          <StatTile
            label="Open buyer requests"
            value={d.open_requests}
            delta="Custom commissions"
          />
        </div>

        {/* Two Cards Side by Side: Attention Queue + Price Advice */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          {/* Left Column (7 cols): Needs Attention */}
          <div className="lg:col-span-7 bg-white rounded-lg border border-[#E3E5EC] p-5 shadow-xs flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-[#E3E5EC] pb-3">
              <h3 className="font-bold text-[15px] text-[#111827]">
                Needs your attention
              </h3>
              <span className="text-[12px] font-semibold text-[#4B3BD1]">
                3 items pending
              </span>
            </div>

            <div className="flex flex-col gap-3">
              {/* Order item */}
              <div className="p-3.5 rounded-lg border border-[#F3D9CB] bg-[#FBEDE6] flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-full bg-[#E58055]/20 flex items-center justify-center text-[#B9532E] shrink-0">
                    <Package className="size-4.5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-[13.5px] text-[#111827]">
                      3 orders ready to pack & ship
                    </h4>
                    <p className="text-[12px] text-[#6B7080]">
                      Generate shipping label and print Meesho package tags
                    </p>
                  </div>
                </div>
                <Link
                  href="/sell/orders"
                  className="px-3 py-1.5 rounded-md bg-[#4B3BD1] text-white text-[12px] font-semibold hover:bg-[#3A2DB0] shrink-0"
                >
                  View orders
                </Link>
              </div>

              {/* Action needed on product */}
              <div className="p-3.5 rounded-lg border border-[#E3E5EC] bg-[#F8F9FC] flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 shrink-0">
                    <AlertCircle className="size-4.5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-[13.5px] text-[#111827]">
                      1 product needs stock replenished
                    </h4>
                    <p className="text-[12px] text-[#6B7080]">
                      Bidriware Silver Inlay Box is out of stock
                    </p>
                  </div>
                </div>
                <Link
                  href="/sell/products?status=action_needed"
                  className="px-3 py-1.5 rounded-md border border-[#E3E5EC] bg-white text-[#111827] text-[12px] font-semibold hover:bg-[#F1F2F6] shrink-0"
                >
                  Add stock
                </Link>
              </div>

              {/* Open Request */}
              <div className="p-3.5 rounded-lg border border-[#EFEDFC] bg-[#F8F7FD] flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-full bg-[#EFEDFC] flex items-center justify-center text-[#4B3BD1] shrink-0">
                    <Inbox className="size-4.5" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-[13.5px] text-[#111827]">
                      Buyer in Mumbai requested custom weave
                    </h4>
                    <p className="text-[12px] text-[#6B7080]">
                      Looking for 6-yard Indigo Tussar silk piece by 15 Nov
                    </p>
                  </div>
                </div>
                <Link
                  href="/sell/requests"
                  className="px-3 py-1.5 rounded-md bg-[#4B3BD1] text-white text-[12px] font-semibold hover:bg-[#3A2DB0] shrink-0"
                >
                  Reply
                </Link>
              </div>
            </div>
          </div>

          {/* Right Column (5 cols): Price Advice & Market Intelligence */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <div className="bg-white rounded-lg border border-[#E3E5EC] p-5 shadow-xs flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-[#E3E5EC] pb-3">
                <div className="flex items-center gap-1.5 text-[15px] font-bold text-[#111827]">
                  <TrendingUp className="size-4.5 text-[#4B3BD1]" />
                  <span>Price Advice</span>
                </div>
                <Link
                  href="/sell/price-advice"
                  className="text-[12px] font-semibold text-[#4B3BD1] hover:underline"
                >
                  View all →
                </Link>
              </div>

              <p className="text-[12px] text-[#6B7080]">
                Live market benchmarks show you could earn more on these handcrafted pieces:
              </p>

              <div className="flex flex-col gap-2.5">
                <div className="p-3 rounded-lg border border-[#E3E5EC] bg-[#F8F9FC] flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-[#111827] truncate">
                      Jaipur Blue Pottery Bowl
                    </p>
                    <p className="text-[11.5px] text-[#6B7080]">
                      Your price: ₹1,250 · Market: ₹1,400–₹1,800
                    </p>
                  </div>
                  <button
                    type="button"
                    className="px-2.5 py-1 rounded bg-[#EFEDFC] text-[#4B3BD1] hover:bg-[#4B3BD1] hover:text-white text-[11.5px] font-semibold transition-colors shrink-0"
                  >
                    Use ₹1,500
                  </button>
                </div>

                <div className="p-3 rounded-lg border border-[#E3E5EC] bg-[#F8F9FC] flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[13px] font-semibold text-[#111827] truncate">
                      Kutch Rogan Wall Hanging
                    </p>
                    <p className="text-[11.5px] text-[#6B7080]">
                      Your price: ₹4,200 · Market: ₹4,500–₹5,200
                    </p>
                  </div>
                  <button
                    type="button"
                    className="px-2.5 py-1 rounded bg-[#EFEDFC] text-[#4B3BD1] hover:bg-[#4B3BD1] hover:text-white text-[11.5px] font-semibold transition-colors shrink-0"
                  >
                    Use ₹4,800
                  </button>
                </div>
              </div>
            </div>

            {/* Profile Completion Card */}
            {!profileDismissed && (
              <div className="bg-white rounded-lg border border-[#E3E5EC] p-4 shadow-xs flex flex-col gap-2 relative">
                <button
                  type="button"
                  onClick={() => setProfileDismissed(true)}
                  className="absolute top-3 end-3 text-[#A3A7B5] hover:text-[#111827]"
                  aria-label="Dismiss"
                >
                  <X className="size-4" />
                </button>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-5 text-[#16A34A]" />
                  <span className="font-semibold text-[13.5px] text-[#111827]">
                    Pehchan Passport ({d.profile_completion}% complete)
                  </span>
                </div>
                <p className="text-[12px] text-[#6B7080] pr-6">
                  Add your workshop GPS location and Pehchan artisan card number to unlock priority bulk export orders.
                </p>
                <Link
                  href="/sell/passport"
                  className="text-[12px] font-semibold text-[#4B3BD1] hover:underline self-start pt-1"
                >
                  Complete profile →
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
