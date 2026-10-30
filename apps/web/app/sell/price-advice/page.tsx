"use client";

import { Check, Sparkles, TrendingUp } from "lucide-react";
import { Suspense, useState } from "react";
import { PageHeader } from "@/components/seller/PageHeader";
import { StatTile } from "@/components/seller/StatTile";
import { InfoStrip, SubTabs, type TabItem } from "@/components/seller/Tabs";
import { cx, inr } from "@/lib/format";

interface PriceAdviceItem {
  id: string;
  title: string;
  thumbnailUrl: string;
  currentPrice: number;
  benchmarkMin: number;
  benchmarkMax: number;
  recommendedPrice: number;
  position: "below" | "in_range" | "above";
  updatedAt: string;
}

const MOCK_ADVICE: PriceAdviceItem[] = [
  {
    id: "pa-1",
    title: "Bhagalpuri Handwoven Tussar Silk Saree",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=300&q=80",
    currentPrice: 2800,
    benchmarkMin: 2600,
    benchmarkMax: 3400,
    recommendedPrice: 2800,
    position: "in_range",
    updatedAt: "3 hours ago",
  },
  {
    id: "pa-2",
    title: "Jaipur Blue Pottery Floral Fruit Bowl",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=300&q=80",
    currentPrice: 1250,
    benchmarkMin: 1400,
    benchmarkMax: 1850,
    recommendedPrice: 1550,
    position: "below",
    updatedAt: "1 hour ago",
  },
  {
    id: "pa-3",
    title: "Bidriware Silver Inlay Keepsake Box",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=300&q=80",
    currentPrice: 3600,
    benchmarkMin: 2900,
    benchmarkMax: 3500,
    recommendedPrice: 3500,
    position: "above",
    updatedAt: "4 hours ago",
  },
  {
    id: "pa-4",
    title: "Kutch Rogan Painted Silk Wall Hanging",
    thumbnailUrl:
      "https://images.unsplash.com/photo-1582562124811-c09040d0a901?auto=format&fit=crop&w=300&q=80",
    currentPrice: 4200,
    benchmarkMin: 4500,
    benchmarkMax: 5400,
    recommendedPrice: 4800,
    position: "below",
    updatedAt: "Yesterday",
  },
];

export default function PriceAdvicePage() {
  return (
    <Suspense>
      <PriceAdviceContent />
    </Suspense>
  );
}

function PriceAdviceContent() {
  const [activeTab, setActiveTab] = useState<string>("all");
  const [items, setItems] = useState<PriceAdviceItem[]>(MOCK_ADVICE);
  const [appliedId, setAppliedId] = useState<string | null>(null);

  const tabs: TabItem[] = [
    { id: "all", label: "All Products", count: items.length },
    { id: "below", label: "Below Range", count: items.filter((i) => i.position === "below").length },
    { id: "in_range", label: "In Range", count: items.filter((i) => i.position === "in_range").length },
    { id: "above", label: "Above Range", count: items.filter((i) => i.position === "above").length },
  ];

  const filtered = items.filter((it) => (activeTab === "all" ? true : it.position === activeTab));

  const handleApplyPrice = (id: string, newPrice: number) => {
    setItems((prev) =>
      prev.map((it) =>
        it.id === id ? { ...it, currentPrice: newPrice, position: "in_range" } : it
      )
    );
    setAppliedId(id);
    setTimeout(() => setAppliedId(null), 2500);
  };

  return (
    <div className="flex flex-col min-w-0">
      <PageHeader
        title="Price Advice & Market Intelligence"
        howToText="How Meesho suggests fair prices"
      />

      <div className="max-w-[1240px] w-full mx-auto px-4 sm:px-6 py-5 flex flex-col gap-4">
        {/* Info Strip */}
        <InfoStrip>
          Meesho scans marketplace benchmarks, supplier catalogs, and regional demand to ensure you price competitively for maximum volume and profit.
        </InfoStrip>

        {/* Overview Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatTile
            label="Total Analyzed"
            value={items.length}
            active={activeTab === "all"}
            onClick={() => setActiveTab("all")}
          />
          <StatTile
            label="Below Market Range"
            value={items.filter((i) => i.position === "below").length}
            active={activeTab === "below"}
            onClick={() => setActiveTab("below")}
          />
          <StatTile
            label="Optimal Fair Range"
            value={items.filter((i) => i.position === "in_range").length}
            active={activeTab === "in_range"}
            onClick={() => setActiveTab("in_range")}
          />
          <StatTile
            label="Premium Craft Level"
            value={items.filter((i) => i.position === "above").length}
            active={activeTab === "above"}
            onClick={() => setActiveTab("above")}
          />
        </div>

        {/* Main Card */}
        <div className="p-4 sm:p-5 rounded-lg border border-[#E3E5EC] bg-white shadow-xs flex flex-col gap-4">
          <SubTabs
            tabs={tabs}
            activeId={activeTab}
            onChange={(id) => setActiveTab(id)}
          />

          <div className="overflow-x-auto">
            <table className="w-full text-start text-[13px] border-collapse">
              <thead>
                <tr className="bg-[#F8F9FC] border-b border-[#E3E5EC] text-[#6B7080] font-medium text-[12px] uppercase tracking-wider text-start">
                  <th className="py-3 px-3 w-16 text-center">Image</th>
                  <th className="py-3 px-4">Product</th>
                  <th className="py-3 px-4">Your Price</th>
                  <th className="py-3 px-4">Market Benchmark Range</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Updated</th>
                  <th className="py-3 px-4 text-end">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E3E5EC]">
                {filtered.map((row) => (
                  <tr key={row.id} className="hover:bg-[#F8F9FC]/80 transition-colors">
                    <td className="py-3 px-3 text-center">
                      <div className="size-12 mx-auto rounded-md overflow-hidden bg-gray-100 border border-[#E3E5EC]">
                        <img src={row.thumbnailUrl} alt={row.title} className="w-full h-full object-cover" />
                      </div>
                    </td>

                    <td className="py-3 px-4 max-w-[220px]">
                      <span className="font-semibold text-[#111827] line-clamp-1">
                        {row.title}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-bold text-[#111827] whitespace-nowrap">
                      {inr(row.currentPrice)}
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="font-semibold text-[#111827]">
                        {inr(row.benchmarkMin)}–{inr(row.benchmarkMax)}
                      </span>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      {row.position === "below" && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11.5px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                          <span className="size-1.5 rounded-full bg-amber-600" />
                          <span>Below Range</span>
                        </span>
                      )}
                      {row.position === "in_range" && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11.5px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                          <span className="size-1.5 rounded-full bg-emerald-600" />
                          <span>In Fair Range</span>
                        </span>
                      )}
                      {row.position === "above" && (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11.5px] font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200">
                          <span className="size-1.5 rounded-full bg-indigo-600" />
                          <span>Premium Masterpiece</span>
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-[#6B7080] text-[12px] whitespace-nowrap">
                      {row.updatedAt}
                    </td>

                    <td className="py-3 px-4 text-end whitespace-nowrap">
                      {appliedId === row.id ? (
                        <span className="text-[12px] text-[#16A34A] font-semibold flex items-center justify-end gap-1">
                          <Check className="size-4" />
                          <span>Updated!</span>
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleApplyPrice(row.id, row.recommendedPrice)}
                          className="px-3 py-1.5 rounded-md bg-[#EFEDFC] hover:bg-[#4B3BD1] text-[#4B3BD1] hover:text-white text-[12px] font-semibold transition-colors shadow-2xs flex items-center gap-1 ms-auto"
                        >
                          <Sparkles className="size-3" />
                          <span>Use {inr(row.recommendedPrice)}</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
