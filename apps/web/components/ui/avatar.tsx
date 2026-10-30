import { UserRound } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface AvatarProps {
  src?: string | null;
  name?: string;
  size?: 24 | 32 | 40 | 56 | 96;
  verified?: boolean;
  className?: string;
}

export function Avatar({
  src,
  name,
  size = 40,
  verified = false,
  className,
}: AvatarProps) {
  const sizeClasses = {
    24: "size-6 text-caption",
    32: "size-8 text-xs",
    40: "size-10 text-caption font-semibold",
    56: "size-14 text-body font-semibold",
    96: "size-24 text-h2 font-semibold",
  }[size];

  const initials = name
    ? name
        .split(" ")
        .slice(0, 2)
        .map((p) => p[0])
        .join("")
        .toUpperCase()
    : "";

  return (
    <div
      className={cx(
        "relative inline-flex shrink-0 items-center justify-center rounded-full bg-khadi-200 text-ink-800 overflow-hidden select-none",
        sizeClasses,
        verified && "ring-2 ring-peacock-600 ring-offset-2 ring-offset-bg",
        className
      )}
    >
      {src ? (
        <img
          src={src}
          alt={name || "Avatar"}
          className="size-full object-cover"
          loading="lazy"
        />
      ) : initials ? (
        <span>{initials}</span>
      ) : (
        <UserRound className="size-1/2 text-muted" aria-hidden />
      )}
    </div>
  );
}
