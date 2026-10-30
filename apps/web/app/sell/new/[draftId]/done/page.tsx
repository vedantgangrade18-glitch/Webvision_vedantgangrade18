"use client";

import { CheckCircle2, Clock, Copy, ExternalLink, Plus, QrCode, Share2, ShieldCheck, Video } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { PageHeader } from "@/components/seller/PageHeader";
import { StatusPill } from "@/components/seller/Tabs";

export default function ProductSubmittedDonePage() {
  const params = useParams();
  const draftId = (params?.draftId as string) || "draft-101";

  const [copiedId, setCopiedId] = useState<string | null>(null);

  const karuIds = [
    `KA-SLK-771-01`,
    `KA-SLK-771-02`,
    `KA-SLK-771-03`,
    `KA-SLK-771-04`,
  ];

  const handleCopy = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="flex flex-col min-h-dvh bg-[#F1F2F6]">
      <PageHeader
        title="Catalog Submitted"
        backHref="/sell/products"
      />

      <div className="max-w-2xl w-full mx-auto px-4 py-12 flex flex-col items-center">
        {/* Main Success Card */}
        <div className="w-full bg-white rounded-xl border border-[#E3E5EC] p-6 sm:p-8 shadow-sm flex flex-col items-center text-center">
          {/* Green Check Circle */}
          <div className="size-16 rounded-full bg-emerald-50 border-2 border-emerald-200 flex items-center justify-center text-emerald-600 mb-4 animate-in zoom-in duration-300">
            <CheckCircle2 className="size-9" />
          </div>

          <h2 className="text-[22px] font-bold text-[#111827]">
            Your Product is Live!
          </h2>
          <p className="text-[13.5px] text-[#6B7080] mt-1 max-w-md">
            Bhagalpuri Handwoven Tussar Silk Saree has been published to Meesho Marketplace with 0% commission.
          </p>

          {/* Verification Status Pill */}
          <div className="mt-4 flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFEDFC] border border-[#4B3BD1]/20 text-[#4B3BD1] text-[12.5px] font-semibold">
            <Clock className="size-4 animate-spin" />
            <span>Meesho Quality Verification checking · usually under 10 minutes</span>
          </div>

          {/* Product IDs Tag Section */}
          <div className="w-full mt-6 p-4 rounded-lg border border-[#E3E5EC] bg-[#F8F9FC] flex flex-col gap-2.5 text-start">
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-bold text-[#111827]">
                4 Product Stock IDs Created
              </span>
              <span className="text-[11px] text-[#6B7080]">
                One unique tag per physical piece
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-1">
              {karuIds.map((id) => (
                <div
                  key={id}
                  className="flex items-center justify-between p-2 rounded bg-white border border-[#E3E5EC] text-[12px] font-mono font-semibold text-[#111827]"
                >
                  <span className="truncate">{id}</span>
                  <button
                    type="button"
                    onClick={() => handleCopy(id)}
                    className="p-1 text-[#7C8196] hover:text-[#4B3BD1]"
                    title="Copy Product ID"
                  >
                    <Copy className="size-3.5" />
                  </button>
                </div>
              ))}
            </div>

            {copiedId && (
              <span className="text-[11px] text-[#16A34A] font-medium text-center">
                Copied {copiedId} to clipboard!
              </span>
            )}
          </div>

          {/* Action Buttons */}
          <div className="w-full flex flex-col sm:flex-row items-center justify-center gap-3 mt-8">
            <Link
              href={`/sell/share?id=${draftId}`}
              className="w-full sm:w-auto px-5 py-2.5 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13.5px] font-semibold transition-colors flex items-center justify-center gap-2 shadow-xs"
            >
              <Share2 className="size-4" />
              <span>Share & QR Sheet</span>
            </Link>

            <Link
              href="/sell/new"
              className="w-full sm:w-auto px-5 py-2.5 rounded-md border border-[#4B3BD1] text-[#4B3BD1] hover:bg-[#EFEDFC] text-[13.5px] font-semibold transition-colors flex items-center justify-center gap-2"
            >
              <Plus className="size-4" />
              <span>+ Add another product</span>
            </Link>

            <Link
              href="/sell/products"
              className="w-full sm:w-auto px-5 py-2.5 rounded-md border border-[#E3E5EC] text-[#111827] hover:bg-[#F1F2F6] text-[13.5px] font-semibold transition-colors"
            >
              <span>Go to products</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
