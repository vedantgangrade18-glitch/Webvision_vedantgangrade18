import React from "react";
import { cx } from "@/lib/format";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  tone?: "surface" | "alt" | "brand-soft";
}

export function Card({
  className,
  children,
  tone = "surface",
  ...rest
}: CardProps) {
  const toneClasses = {
    surface: "bg-surface border-line",
    alt: "bg-surface-alt border-line-strong",
    "brand-soft": "bg-brand-soft border-terracotta-200",
  }[tone];

  return (
    <div
      className={cx(
        "rounded-sm border p-4 sm:p-5 transition-all duration-150",
        toneClasses,
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
