"use client";

import { Minus, Plus } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface QuantityStepperProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
  className?: string;
}

export function QuantityStepper({
  value,
  onChange,
  min = 1,
  max = 99,
  disabled = false,
  className,
}: QuantityStepperProps) {
  return (
    <div
      className={cx(
        "inline-flex items-center rounded-xs border border-line-strong bg-surface select-none",
        disabled && "opacity-50 pointer-events-none",
        className
      )}
    >
      <button
        type="button"
        disabled={disabled || value <= min}
        onClick={() => onChange(Math.max(min, value - 1))}
        className="flex size-11 items-center justify-center text-ink-700 hover:text-brand hover:bg-brand-soft active:bg-brand-soft/80 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
        aria-label="Decrease quantity"
      >
        <Minus className="size-4" />
      </button>
      <span
        aria-live="polite"
        className="min-w-10 px-2 text-center text-body-s font-semibold tabular-nums text-text"
      >
        {value}
      </span>
      <button
        type="button"
        disabled={disabled || value >= max}
        onClick={() => onChange(Math.min(max, value + 1))}
        className="flex size-11 items-center justify-center text-ink-700 hover:text-brand hover:bg-brand-soft active:bg-brand-soft/80 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
        aria-label="Increase quantity"
      >
        <Plus className="size-4" />
      </button>
    </div>
  );
}
