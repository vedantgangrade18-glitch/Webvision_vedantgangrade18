"use client";

import { type ReactNode } from "react";
import { cx } from "@/lib/format";

interface StatTileProps {
  label: string;
  value: number | string;
  delta?: string;
  active?: boolean;
  onClick?: () => void;
  className?: string;
}

export function StatTile({
  label,
  value,
  delta,
  active,
  onClick,
  className,
}: StatTileProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={cx(
        "flex flex-col justify-center min-w-[140px] sm:min-w-[170px] h-[74px] px-4 py-2.5 rounded-lg border text-start transition-all",
        active
          ? "border-[#4B3BD1] bg-[#EFEDFC]/60 shadow-xs ring-1 ring-[#4B3BD1]"
          : "border-[#E3E5EC] bg-white hover:border-[#C9CCD6]",
        onClick ? "cursor-pointer" : "cursor-default",
        className
      )}
    >
      <span className="text-[12px] font-medium text-[#6B7080] truncate leading-tight">
        {label}
      </span>
      <div className="flex items-baseline gap-2 mt-1">
        <span className={cx("text-[22px] font-bold leading-none", active ? "text-[#4B3BD1]" : "text-[#111827]")}>
          {value}
        </span>
        {delta && <span className="text-[11px] font-medium text-[#16A34A]">{delta}</span>}
      </div>
    </button>
  );
}
