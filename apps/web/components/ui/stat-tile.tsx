import React from "react";
import { cx } from "@/lib/format";

export interface StatTileProps {
  label: string;
  value: string | number;
  hint?: string;
  delta?: string | { value: string; positive: boolean };
  className?: string;
}

export function StatTile({
  label,
  value,
  hint,
  delta,
  className,
}: StatTileProps) {
  return (
    <div
      className={cx(
        "flex flex-col gap-1 rounded-sm border border-line bg-surface p-5 shadow-xs",
        className
      )}
    >
      <span className="text-eyebrow text-muted truncate">{label}</span>
      <p className="font-serif text-3xl sm:text-4xl font-medium tracking-tight text-ink-900 tabular-nums mt-1">
        {value}
      </p>
      {(hint || delta) && (
        <div className="flex items-center gap-2 mt-1 text-caption">
          {typeof delta === "string" ? (
            <span className="text-muted">{delta}</span>
          ) : delta ? (
            <span
              className={cx(
                "font-semibold",
                delta.positive ? "text-verified" : "text-danger"
              )}
            >
              {delta.positive ? "↑" : "↓"} {delta.value}
            </span>
          ) : null}
          {hint && <span className="text-muted">{hint}</span>}
        </div>
      )}
    </div>
  );
}
