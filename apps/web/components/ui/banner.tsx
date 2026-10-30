import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface BannerProps {
  children: React.ReactNode;
  tone?: "info" | "warn" | "success" | "danger";
  title?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function Banner({
  children,
  tone = "info",
  title,
  icon,
  action,
  className,
}: BannerProps) {
  const toneClasses = {
    info: "border-s-3 border-ink-500 bg-surface-alt text-text",
    warn: "border-s-3 border-gold-500 bg-gold-50 text-gold-950",
    success: "border-s-3 border-peacock-600 bg-verified-soft text-peacock-900",
    danger: "border-s-3 border-danger-600 bg-danger-50 text-danger-700",
  }[tone];

  const DefaultIcon = {
    info: Info,
    warn: AlertTriangle,
    success: CheckCircle2,
    danger: AlertCircle,
  }[tone];

  return (
    <div
      role="status"
      className={cx(
        "flex items-start justify-between gap-3.5 rounded-xs p-4 text-body-s",
        toneClasses,
        className
      )}
    >
      <div className="flex items-start gap-3">
        {icon ? (
          <span className="shrink-0 mt-0.5">{icon}</span>
        ) : (
          <DefaultIcon className="size-5 shrink-0 mt-0.5" aria-hidden />
        )}
        <div className="flex flex-col">
          {title && <span className="font-semibold text-text mb-0.5">{title}</span>}
          <div className="leading-relaxed">{children}</div>
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
