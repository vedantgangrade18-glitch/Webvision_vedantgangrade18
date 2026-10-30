"use client";

import { ChevronDown } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, invalid, disabled, children, ...rest },
  ref
) {
  return (
    <div className="relative w-full">
      <select
        ref={ref}
        disabled={disabled}
        className={cx(
          "w-full appearance-none rounded-xs border bg-surface min-h-12 px-3.5 pe-10 py-2.5 text-body text-text transition-colors duration-150 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed",
          invalid
            ? "border-danger-600 focus:ring-2 focus:ring-danger-600/20"
            : "border-line-strong focus:border-brand focus:ring-3 focus:ring-brand/15",
          className
        )}
        {...rest}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute end-3.5 top-1/2 -translate-y-1/2 size-4 text-muted shrink-0"
        aria-hidden
      />
    </div>
  );
});
