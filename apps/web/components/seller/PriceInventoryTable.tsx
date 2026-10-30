"use client";

import { Check, HelpCircle, Info, Sparkles, TrendingUp } from "lucide-react";
import { useState } from "react";
import { cx, inr } from "@/lib/format";

interface PriceRow {
  size: string;
  priceInr: number | "";
  mrpInr: number | "";
  inventory: number;
  returnable: boolean;
  shipsInDays: number;
}

interface PriceInventoryTableProps {
  row: PriceRow;
  onChange: (updated: Partial<PriceRow>) => void;
  copyPriceToAllSizes: boolean;
  onToggleCopyPrice: (val: boolean) => void;
  benchmarkMin?: number;
  benchmarkMax?: number;
  recommendedPrice?: number;
  className?: string;
}

export function PriceInventoryTable({
  row,
  onChange,
  copyPriceToAllSizes,
  onToggleCopyPrice,
  benchmarkMin = 2600,
  benchmarkMax = 3400,
  recommendedPrice = 2800,
  className,
}: PriceInventoryTableProps) {
  const [showSources, setShowSources] = useState(false);

  const currentPrice = typeof row.priceInr === "number" ? row.priceInr : 0;
  const isBelow = currentPrice > 0 && currentPrice < benchmarkMin;
  const isInRange = currentPrice >= benchmarkMin && currentPrice <= benchmarkMax;
  const isAbove = currentPrice > benchmarkMax;

  // Percentage along slider (clamped between 5% and 95%)
  const positionPercent =
    currentPrice > 0
      ? Math.min(
          95,
          Math.max(5, ((currentPrice - benchmarkMin) / (benchmarkMax - benchmarkMin)) * 80 + 10)
        )
      : 50;

  return (
    <div className={cx("flex flex-col gap-4", className)}>
      {/* Copy price details checkbox */}
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer text-[12.5px] text-[#6B7080] hover:text-[#111827] select-none">
          <input
            type="checkbox"
            checked={copyPriceToAllSizes}
            onChange={(e) => onToggleCopyPrice(e.target.checked)}
            className="size-4 rounded border-[#E3E5EC] text-[#4B3BD1] focus:ring-[#4B3BD1]"
          />
          <span>Copy price details to all sizes</span>
        </label>
      </div>

      {/* Horizontally scrolling table card */}
      <div className="rounded-lg border border-[#E3E5EC] bg-white overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-start text-[13px] border-collapse min-w-[640px]">
            <thead>
              <tr className="bg-[#F8F9FC] border-b border-[#E3E5EC] text-[#6B7080] text-[12px] font-medium text-start">
                <th className="py-2.5 px-4 w-28">Size</th>
                <th className="py-2.5 px-4 w-40">
                  <span className="flex items-center gap-1">
                    <span>Meesho Price (₹)*</span>
                    <span className="text-[#A3A7B5]" title="What the buyer pays. You receive 100% of this amount.">
                      ⓘ
                    </span>
                  </span>
                </th>
                <th className="py-2.5 px-4 w-36">
                  <span className="flex items-center gap-1">
                    <span>MRP (₹)</span>
                    <span className="text-[#A3A7B5]" title="Original shop price. Shown struck-through if higher.">
                      ⓘ
                    </span>
                  </span>
                </th>
                <th className="py-2.5 px-4 w-32">
                  <span className="flex items-center gap-1">
                    <span>Inventory*</span>
                    <span className="text-[#A3A7B5]" title="Available physical pieces. Each gets a unique Meesho Product ID.">
                      ⓘ
                    </span>
                  </span>
                </th>
                <th className="py-2.5 px-4 w-28">Returnable</th>
                <th className="py-2.5 px-4 w-28">Ships in</th>
              </tr>
            </thead>
            <tbody>
              <tr className="hover:bg-gray-50/50">
                {/* Size */}
                <td className="py-3 px-4 font-semibold text-[#111827]">
                  {row.size || "Free Size"}
                </td>

                {/* Meesho Price */}
                <td className="py-3 px-4">
                  <div className="relative">
                    <span className="absolute start-3 top-1/2 -translate-y-1/2 text-[#6B7080] font-medium">
                      ₹
                    </span>
                    <input
                      type="number"
                      value={row.priceInr}
                      onChange={(e) =>
                        onChange({
                          priceInr: e.target.value === "" ? "" : Number(e.target.value),
                        })
                      }
                      placeholder="e.g. 2800"
                      className="w-full h-9 ps-7 pe-3 rounded border border-[#E3E5EC] text-[13.5px] font-semibold text-[#111827] focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1] focus:outline-none"
                    />
                  </div>
                </td>

                {/* MRP */}
                <td className="py-3 px-4">
                  <div className="relative">
                    <span className="absolute start-3 top-1/2 -translate-y-1/2 text-[#6B7080] font-medium">
                      ₹
                    </span>
                    <input
                      type="number"
                      value={row.mrpInr}
                      onChange={(e) =>
                        onChange({
                          mrpInr: e.target.value === "" ? "" : Number(e.target.value),
                        })
                      }
                      placeholder="e.g. 3200"
                      className="w-full h-9 ps-7 pe-3 rounded border border-[#E3E5EC] text-[13.5px] text-[#111827] focus:border-[#4B3BD1] focus:outline-none"
                    />
                  </div>
                </td>

                {/* Inventory */}
                <td className="py-3 px-4">
                  <input
                    type="number"
                    min="1"
                    max="999"
                    value={row.inventory}
                    onChange={(e) => onChange({ inventory: Math.max(1, Number(e.target.value) || 1) })}
                    className="w-24 h-9 px-3 rounded border border-[#E3E5EC] text-[13.5px] font-semibold text-[#111827] focus:border-[#4B3BD1] focus:outline-none"
                  />
                </td>

                {/* Returnable Switch */}
                <td className="py-3 px-4">
                  <button
                    type="button"
                    onClick={() => onChange({ returnable: !row.returnable })}
                    className={cx(
                      "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none",
                      row.returnable ? "bg-[#4B3BD1]" : "bg-gray-300"
                    )}
                  >
                    <span
                      className={cx(
                        "pointer-events-none inline-block size-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                        row.returnable ? "translate-x-4" : "translate-x-0"
                      )}
                    />
                  </button>
                </td>

                {/* Ships in days */}
                <td className="py-3 px-4">
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      min="1"
                      max="30"
                      value={row.shipsInDays}
                      onChange={(e) => onChange({ shipsInDays: Number(e.target.value) || 2 })}
                      className="w-14 h-9 px-2 text-center rounded border border-[#E3E5EC] text-[13px] text-[#111827] focus:border-[#4B3BD1] focus:outline-none"
                    />
                    <span className="text-[12px] text-[#6B7080]">days</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Price Advice Range Bar & Suggestion */}
      <div className="p-3.5 rounded-lg border border-[#E3E5EC] bg-[#F8F9FC] flex flex-col gap-2.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-[13px] text-[#111827]">
            <TrendingUp className="size-4 text-[#4B3BD1]" />
            <span className="font-semibold">Price advice:</span>
            <span>
              Shops sell similar handmade pieces for{" "}
              <strong className="font-semibold text-[#111827]">
                {inr(benchmarkMin)}–{inr(benchmarkMax)}
              </strong>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onChange({ priceInr: recommendedPrice })}
              className="px-2.5 py-1 rounded bg-[#EFEDFC] hover:bg-[#4B3BD1] text-[#4B3BD1] hover:text-white text-[12px] font-semibold transition-colors flex items-center gap-1"
            >
              <Sparkles className="size-3" />
              <span>Use {inr(recommendedPrice)}</span>
            </button>

            <button
              type="button"
              onClick={() => setShowSources((v) => !v)}
              className="text-[12px] text-[#6B7080] hover:text-[#4B3BD1] underline"
            >
              Sources
            </button>
          </div>
        </div>

        {/* Visual Range Bar with Current Indicator */}
        <div className="relative py-2">
          <div className="h-2 w-full rounded-full bg-gradient-to-r from-amber-200 via-emerald-200 to-indigo-200 relative">
            {/* Position indicator dot */}
            <div
              className="absolute -top-1.5 size-5 rounded-full bg-[#4B3BD1] border-2 border-white shadow-md -translate-x-1/2 transition-all duration-300 flex items-center justify-center text-white text-[8px]"
              style={{ left: `${positionPercent}%` }}
              title={`Your current price: ${inr(currentPrice)}`}
            />
          </div>

          <div className="flex justify-between text-[11px] text-[#7C8196] mt-1 font-mono">
            <span>{inr(benchmarkMin)} (Value)</span>
            <span className="text-[#16A34A] font-semibold">Recommended: {inr(recommendedPrice)}</span>
            <span>{inr(benchmarkMax)} (Premium)</span>
          </div>
        </div>

        {/* Sources Popover */}
        {showSources && (
          <div className="mt-1 p-2.5 bg-white border border-[#E3E5EC] rounded text-[12px] text-[#5C554D] flex flex-col gap-1.5">
            <div className="font-semibold text-[#111827]">Market Intelligence Benchmarks:</div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11.5px]">
              <div className="p-1.5 rounded bg-gray-50 border border-gray-100">
                <span className="font-medium text-[#111827]">Handloom Emporiums:</span> ₹2,950
              </div>
              <div className="p-1.5 rounded bg-gray-50 border border-gray-100">
                <span className="font-medium text-[#111827]">Artisan Clusters (Direct):</span> ₹2,600
              </div>
              <div className="p-1.5 rounded bg-gray-50 border border-gray-100">
                <span className="font-medium text-[#111827]">Craft Boutiques:</span> ₹3,400
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
