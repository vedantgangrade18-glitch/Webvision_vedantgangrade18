"use client";

import { Loader2 } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "tertiary" | "ghost" | "link" | "danger" | "verified";
  size?: "L" | "M" | "S";
  loading?: boolean;
  block?: boolean;
  icon?: React.ReactNode;
  iconEnd?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    children,
    variant = "primary",
    size = "M",
    loading = false,
    block = false,
    icon,
    iconEnd,
    className,
    disabled,
    ...rest
  },
  ref
) {
  const resolvedVariant = variant === "tertiary" ? "ghost" : variant;

  const variantClasses = {
    primary: "bg-brand text-on-dark hover:bg-brand-hover active:bg-brand-hover disabled:bg-sand-300 disabled:text-ink-400",
    secondary: "border border-ink-900 bg-transparent text-ink-900 hover:bg-ink-900 hover:text-white active:bg-ink-950 disabled:border-sand-300 disabled:text-ink-400",
    ghost: "bg-transparent text-ink-900 hover:bg-brand-soft hover:text-brand active:bg-brand-soft/80 disabled:text-ink-400",
    link: "bg-transparent text-brand hover:text-brand-hover underline-offset-4 hover:underline p-0 h-auto font-medium",
    danger: "bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-700 disabled:bg-sand-300",
    verified: "bg-peacock-700 text-white hover:bg-peacock-800 active:bg-peacock-800 disabled:bg-sand-300",
  }[resolvedVariant];

  const sizeClasses = {
    L: "min-h-13 px-6 text-eyebrow gap-2.5",
    M: "min-h-11 px-4 text-eyebrow gap-2",
    S: "min-h-9 px-3 text-caption font-semibold gap-1.5",
  }[size];

  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center rounded-xs transition-colors duration-150 focus-visible:outline-none select-none cursor-pointer disabled:cursor-not-allowed",
        variant !== "link" && sizeClasses,
        variantClasses,
        block && "w-full",
        className
      )}
      {...rest}
    >
      {loading ? (
        <Loader2 className="size-4 animate-spin shrink-0" aria-hidden />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      <span>{children}</span>
      {!loading && iconEnd && <span className="shrink-0">{iconEnd}</span>}
    </button>
  );
});

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cx("size-5 animate-spin text-brand", className)} aria-hidden />;
}
