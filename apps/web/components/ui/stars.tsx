import { Star } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export function Stars({
  value = 5,
  max = 5,
  size = 16,
  label,
  onChange,
  className,
}: {
  value?: number;
  max?: number;
  size?: number;
  label?: string;
  onChange?: (v: number) => void;
  className?: string;
}) {
  return (
    <div
      className={cx("inline-flex items-center gap-0.5 text-gold-500", className)}
      role={onChange ? "radiogroup" : "img"}
      aria-label={label || `${value} out of ${max} stars`}
    >
      {[...Array(max)].map((_, i) => {
        const starVal = i + 1;
        const filled = value >= starVal;
        const half = !filled && value >= starVal - 0.5;

        const starIcon = (
          <Star
            style={{ width: size, height: size }}
            className={cx(
              filled
                ? "fill-gold-500 text-gold-500"
                : half
                ? "fill-gold-500/50 text-gold-500"
                : "fill-ink-200 text-ink-200"
            )}
          />
        );

        return onChange ? (
          <button
            key={i}
            type="button"
            role="radio"
            aria-checked={value === starVal}
            aria-label={`${starVal}`}
            onClick={() => onChange(starVal)}
            className="flex items-center justify-center cursor-pointer p-0.5"
          >
            {starIcon}
          </button>
        ) : (
          <span key={i}>{starIcon}</span>
        );
      })}
    </div>
  );
}

export function RatingSummary({
  rating,
  count,
  className,
}: {
  rating: number;
  count: number;
  className?: string;
}) {
  return (
    <div className={cx("flex items-center gap-2 text-body-s", className)}>
      <Stars value={rating} size={14} />
      <span className="font-semibold text-text tabular-nums">{rating.toFixed(1)}</span>
      <span className="text-muted">({count} verified)</span>
    </div>
  );
}
