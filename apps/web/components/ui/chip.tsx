"use client";

import { X } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface FilterChipProps {
  label?: string;
  children?: React.ReactNode;
  selected?: boolean;
  active?: boolean;
  onClick?: () => void;
  onToggle?: () => void;
  onRemove?: () => void;
  count?: number;
  className?: string;
}

export function FilterChip({
  label,
  children,
  selected = false,
  active,
  onClick,
  onToggle,
  onRemove,
  count,
  className,
}: FilterChipProps) {
  const isSelected = selected || active || false;
  const handleClick = onToggle || onClick;
  return (
    <button
      type="button"
      onClick={handleClick}
      className={cx(
        "inline-flex items-center gap-1.5 rounded-xs border px-3 py-1.5 text-caption font-medium transition-colors cursor-pointer select-none",
        isSelected
          ? "border-ink-900 bg-ink-900 text-white"
          : "border-line-strong bg-surface text-ink-800 hover:border-ink-900",
        className
      )}
    >
      <span>{children || label}</span>
      {count !== undefined && (
        <span className={cx("text-caption", isSelected ? "text-white/80" : "text-muted")}>
          ({count})
        </span>
      )}
      {onRemove && (
        <span
          role="button"
          tabIndex={0}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ms-1 hover:opacity-75"
          aria-label={`Remove ${label || "filter"}`}
        >
          <X className="size-3.5" />
        </span>
      )}
    </button>
  );
}

export interface ChipProps {
  active?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  className?: string;
}

export function Chip({ active, onClick, children, className }: ChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cx(
        "inline-flex min-h-8.5 items-center gap-1.5 whitespace-nowrap rounded-xs border px-3 py-1.5 text-caption font-medium transition-colors cursor-pointer select-none",
        active
          ? "border-brand bg-brand text-white shadow-2xs"
          : "border-line-strong bg-surface text-ink-800 hover:border-ink-900",
        className
      )}
    >
      {children}
    </button>
  );
}

export interface TagProps {
  children: React.ReactNode;
  tone?: "default" | "brand" | "gold" | "peacock" | "dark";
  className?: string;
}

export function Tag({ children, tone = "default", className }: TagProps) {
  const toneClasses = {
    default: "border-line bg-surface text-text",
    brand: "border-terracotta-200 bg-brand-soft text-brand",
    gold: "border-gold-300 bg-gold-50 text-gold-900",
    peacock: "border-peacock-200 bg-verified-soft text-peacock-700",
    dark: "border-ink-800 bg-ink-900 text-white",
  }[tone];

  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-xs border px-2 py-0.5 text-caption font-semibold uppercase tracking-wider",
        toneClasses,
        className
      )}
    >
      {children}
    </span>
  );
}
