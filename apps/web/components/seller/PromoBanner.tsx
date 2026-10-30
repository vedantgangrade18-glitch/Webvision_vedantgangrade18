"use client";

import { Sparkles, X } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";
import { cx } from "@/lib/format";

interface PromoBannerProps {
  id?: string;
  headline: string;
  description: string;
  actionText: string;
  actionHref?: string;
  onAction?: () => void;
  className?: string;
  icon?: ReactNode;
}

export function PromoBanner({
  id = "default-promo-banner",
  headline,
  description,
  actionText,
  actionHref,
  onAction,
  className,
  icon,
}: PromoBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem(`karu_banner_${id}`);
      if (stored === "dismissed") setDismissed(true);
    }
  }, [id]);

  const handleDismiss = () => {
    setDismissed(true);
    if (typeof window !== "undefined") {
      sessionStorage.setItem(`karu_banner_${id}`, "dismissed");
    }
  };

  if (dismissed) return null;

  return (
    <div
      className={cx(
        "relative flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 sm:p-5 rounded-lg border border-[#F3DFA0] bg-[#FBEDE6] text-[#111827] shadow-xs",
        className
      )}
      role="banner"
    >
      <div className="flex items-center gap-3.5 min-w-0 pr-6 sm:pr-0">
        <div className="size-12 shrink-0 rounded-full bg-[#E58055]/15 flex items-center justify-center text-[#B9532E]">
          {icon || <Sparkles className="size-6 text-[#B9532E]" />}
        </div>
        <div className="min-w-0">
          <h4 className="text-[15px] sm:text-[16px] font-semibold text-[#111827] leading-snug">
            {headline}
          </h4>
          <p className="text-[12.5px] sm:text-[13px] text-[#5C554D] leading-normal">
            {description}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 self-end sm:self-center shrink-0">
        {actionHref ? (
          <Link
            href={actionHref}
            className="px-4 py-2 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13px] font-semibold transition-colors shadow-xs whitespace-nowrap"
          >
            {actionText}
          </Link>
        ) : (
          <button
            type="button"
            onClick={onAction}
            className="px-4 py-2 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13px] font-semibold transition-colors shadow-xs whitespace-nowrap"
          >
            {actionText}
          </button>
        )}

        <button
          type="button"
          onClick={handleDismiss}
          className="absolute top-3 end-3 sm:static p-1 text-[#8F857A] hover:text-[#111827] rounded hover:bg-[#F3D9CB]/40 transition-colors"
          aria-label="Dismiss banner"
        >
          <X className="size-4" />
        </button>
      </div>
    </div>
  );
}
