"use client";

import Link from "next/link";
import { inr } from "@/lib/format";

interface SettlementBoxProps {
  priceInr: number | "";
  mrpInr?: number | "";
  title?: string;
  thumbnailUrl?: string;
  artisanName?: string;
  payoutStatus?: "active" | "pending";
  className?: string;
}

export function SettlementBox({
  priceInr,
  mrpInr,
  title = "Handloom Silk Saree",
  thumbnailUrl,
  artisanName = "Master Artisan",
  payoutStatus = "active",
  className,
}: SettlementBoxProps) {
  const numericPrice = typeof priceInr === "number" ? priceInr : 0;

  return (
    <div className="flex flex-col gap-4">
      {/* 1. Settlement Breakdown (0% Commission Guarantee) */}
      <div className="p-4 rounded-lg border border-[#E3E5EC] bg-white shadow-xs flex flex-col gap-2.5">
        <h4 className="font-semibold text-[13.5px] text-[#111827]">
          Your Earnings (Bank Settlement)
        </h4>

        <div className="flex flex-col gap-1.5 text-[12.5px] pt-1">
          <div className="flex justify-between text-[#5C554D]">
            <span>Meesho listing price</span>
            <span className="font-medium text-[#111827]">{inr(numericPrice)}</span>
          </div>

          <div className="flex justify-between text-[#5C554D]">
            <span>Meesho commission (0%)</span>
            <span className="font-medium text-[#16A34A]">₹0</span>
          </div>

          <div className="flex justify-between text-[#5C554D]">
            <span>Payment gateway & UPI fees</span>
            <span className="font-medium text-[#16A34A]">Paid by Meesho</span>
          </div>

          <div className="my-1 border-t border-[#E3E5EC]" />

          <div className="flex justify-between text-[14px] font-bold">
            <span className="text-[#111827]">You receive</span>
            <span className="text-[#4B3BD1]">{inr(numericPrice)}</span>
          </div>
        </div>

        <p className="text-[11px] text-[#6B7080] leading-tight pt-1">
          100% of proceeds reach your bank or UPI after the 7-day buyer return inspection closes.
        </p>

        {payoutStatus !== "active" && (
          <Link
            href="/sell/payouts"
            className="text-[11.5px] font-semibold text-[#4B3BD1] hover:underline pt-1"
          >
            Set up bank / UPI details →
          </Link>
        )}
      </div>

      {/* 2. Buyer Marketplace Preview Card */}
      <div className="p-4 rounded-lg border border-[#E3E5EC] bg-white shadow-xs flex flex-col gap-2.5">
        <h4 className="font-semibold text-[13.5px] text-[#111827]">
          How Buyers Will See It
        </h4>

        <div className="rounded-lg border border-[#E3E5EC] overflow-hidden bg-[#F8F9FC] p-3 flex gap-3">
          <div className="size-16 rounded overflow-hidden bg-gray-200 shrink-0">
            {thumbnailUrl ? (
              <img src={thumbnailUrl} alt={title} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-[10px] text-gray-400">
                Photo
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-semibold text-[#111827] truncate">{title}</p>
            <p className="text-[11px] text-[#6B7080] truncate">By {artisanName}</p>

            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-[14px] font-bold text-[#111827]">
                {inr(numericPrice)}
              </span>
              {typeof mrpInr === "number" && mrpInr > numericPrice && (
                <span className="text-[11px] text-[#A3A7B5] line-through">
                  {inr(mrpInr)}
                </span>
              )}
            </div>

            <span className="inline-flex items-center gap-1 mt-1 text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
              ● Live · Verified
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
