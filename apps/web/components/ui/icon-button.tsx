"use client";

import React from "react";
import { cx } from "@/lib/format";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  "aria-label": string;
  variant?: "plain" | "surface" | "overlay";
  size?: "md" | "lg";
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  {
    children,
    "aria-label": ariaLabel,
    variant = "plain",
    size = "md",
    className,
    disabled,
    ...rest
  },
  ref
) {
  const variantClasses = {
    plain: "text-ink-700 hover:text-brand hover:bg-brand-soft active:bg-brand-soft/80",
    surface: "border border-line bg-surface text-ink-800 shadow-2xs hover:border-brand hover:text-brand",
    overlay: "bg-surface/90 text-ink-900 shadow-sm backdrop-blur-md hover:bg-surface hover:scale-105 active:scale-95",
  }[variant];

  const sizeClasses = {
    md: "size-11", // 44px
    lg: "size-12", // 48px
  }[size];

  return (
    <button
      ref={ref}
      aria-label={ariaLabel}
      disabled={disabled}
      className={cx(
        "inline-flex items-center justify-center rounded-full transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shrink-0",
        sizeClasses,
        variantClasses,
        className
      )}
      {...rest}
    >
      {children}
    </button>
  );
});
