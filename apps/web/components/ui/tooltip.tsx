import React from "react";
import { cx } from "@/lib/format";

export interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  return (
    <div className={cx("group relative inline-flex", className)}>
      {children}
      <div
        role="tooltip"
        className="pointer-events-none absolute bottom-full start-1/2 -translate-x-1/2 mb-2 hidden group-hover:flex items-center rounded-xs bg-ink-900 px-2.5 py-1 text-caption text-white shadow-sm z-50 whitespace-nowrap"
      >
        <span>{content}</span>
      </div>
    </div>
  );
}
