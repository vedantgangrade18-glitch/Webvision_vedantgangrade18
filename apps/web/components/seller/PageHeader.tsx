"use client";

import { ChevronLeft, Globe, HelpCircle, Menu, Play } from "lucide-react";
import Link from "next/link";
import { useLocale } from "next-intl";
import { type ReactNode, useState } from "react";
import { LanguageSwitcher } from "@/components/karu/language";
import { cx } from "@/lib/format";

interface PageHeaderProps {
  title: ReactNode;
  backHref?: string;
  howToText?: string;
  onOpenHowTo?: () => void;
  onOpenSupport?: () => void;
  onToggleMobileSidebar?: () => void;
  extraRight?: ReactNode;
}

export function PageHeader({
  title,
  backHref,
  howToText = "How to add a product",
  onOpenHowTo,
  onOpenSupport,
  onToggleMobileSidebar,
  extraRight,
}: PageHeaderProps) {
  const locale = useLocale();
  const [videoModalOpen, setVideoModalOpen] = useState(false);

  const handleHowToClick = () => {
    if (onOpenHowTo) {
      onOpenHowTo();
    } else {
      setVideoModalOpen(true);
    }
  };

  return (
    <>
      <header className="h-14 shrink-0 bg-white border-b border-[#E3E5EC] px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20">
        <div className="flex items-center gap-3 min-w-0">
          {/* Mobile hamburger */}
          {onToggleMobileSidebar && (
            <button
              type="button"
              onClick={onToggleMobileSidebar}
              className="lg:hidden p-1.5 -ms-1 rounded-md text-[#6B7080] hover:text-[#111827] hover:bg-[#F1F2F6]"
              aria-label="Open sidebar menu"
            >
              <Menu className="size-5" />
            </button>
          )}

          {/* Optional Back button */}
          {backHref && (
            <Link
              href={backHref}
              className="inline-flex items-center justify-center size-8 rounded-full text-[#6B7080] hover:text-[#111827] hover:bg-[#F1F2F6] transition-colors"
              aria-label="Go back"
            >
              <ChevronLeft className="size-5" />
            </Link>
          )}

          {/* Title */}
          {typeof title === "string" ? (
            <h1 className="text-[18px] font-semibold text-[#111827] truncate tracking-tight">{title}</h1>
          ) : (
            title
          )}
        </div>

        {/* Right action links */}
        <div className="flex items-center gap-4 text-[13px]">
          {extraRight}

          {/* Video Guide link */}
          <button
            type="button"
            onClick={handleHowToClick}
            className="hidden sm:inline-flex items-center gap-1.5 font-medium text-[#4B3BD1] hover:text-[#3A2DB0] hover:underline"
          >
            <span className="flex items-center justify-center size-4.5 rounded-full bg-[#EFEDFC] text-[#4B3BD1]">
              <Play className="size-2.5 fill-current ms-0.5" />
            </span>
            <span>{howToText}</span>
          </button>

          {/* Support link */}
          <button
            type="button"
            onClick={onOpenSupport}
            className="inline-flex items-center gap-1 font-medium text-[#6B7080] hover:text-[#111827]"
          >
            <HelpCircle className="size-4 text-[#D97706]" />
            <span className="hidden md:inline">Need help?</span>
          </button>

          {/* Language Switcher */}
          <div className="border-s border-[#E3E5EC] ps-3">
            <LanguageSwitcher variant="compact" />
          </div>
        </div>
      </header>

      {/* Video Modal fallback */}
      {videoModalOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-white rounded-xl shadow-2xl max-w-xl w-full overflow-hidden border border-[#E3E5EC] animate-in fade-in duration-200">
            <div className="p-4 border-b border-[#E3E5EC] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Play className="size-4 text-[#4B3BD1]" />
                <h3 className="font-semibold text-[15px] text-[#111827]">Video Guide: {howToText}</h3>
              </div>
              <button
                type="button"
                onClick={() => setVideoModalOpen(false)}
                className="text-[#6B7080] hover:text-[#111827] p-1 rounded hover:bg-[#F1F2F6]"
              >
                ✕
              </button>
            </div>
            <div className="aspect-video bg-[#1B1F2E] flex flex-col items-center justify-center text-white p-6 text-center">
              <div className="size-16 rounded-full bg-[#4B3BD1] flex items-center justify-center mb-4 shadow-lg cursor-pointer hover:scale-105 transition-transform">
                <Play className="size-8 fill-current ms-1 text-white" />
              </div>
              <p className="font-medium text-base mb-1">Meesho Supplier Voice Academy</p>
              <p className="text-xs text-[#C9CCD6] max-w-sm">
                Learn how to snap clear photos and speak your product details in your mother tongue for instant cataloguing.
              </p>
            </div>
            <div className="p-4 bg-[#F8F9FC] border-t border-[#E3E5EC] flex justify-end">
              <button
                type="button"
                onClick={() => setVideoModalOpen(false)}
                className="px-4 py-2 bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white rounded-md text-[13px] font-semibold"
              >
                Got it, let&apos;s start
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
