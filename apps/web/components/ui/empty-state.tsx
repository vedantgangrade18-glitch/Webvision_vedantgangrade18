import React from "react";
import { SpotArt } from "@/components/karu/ornaments";
import { cx } from "@/lib/format";

export interface EmptyStateProps {
  icon?: "loom" | "basket" | "thread" | "wheel" | "needle" | "parcel";
  art?: "loom" | "basket" | "thread" | "wheel" | "needle" | "parcel";
  title: React.ReactNode;
  description?: React.ReactNode;
  body?: React.ReactNode;
  action?: React.ReactNode;
  size?: "sm" | "lg";
  className?: string;
}

export function EmptyState({
  icon,
  art = "basket",
  title,
  description,
  body,
  action,
  size = "lg",
  className,
}: EmptyStateProps) {
  const isLg = size === "lg";
  const artName = icon || art;
  const desc = description || body;

  return (
    <div
      className={cx(
        "flex flex-col items-center justify-center text-center",
        isLg ? "py-16 px-4" : "py-8 px-2",
        className
      )}
    >
      <div className="mb-4 text-brand">
        <SpotArt name={artName} size={isLg ? 72 : 48} />
      </div>
      <h3 className={cx(isLg ? "text-h2" : "text-h3", "text-text")}>{title}</h3>
      {desc && (
        <div className="mt-2 max-w-md text-body-s text-muted leading-relaxed">
          {desc}
        </div>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
