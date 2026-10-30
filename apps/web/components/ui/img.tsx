import React from "react";
import { Emblem } from "@/components/karu/ornaments";
import { cx } from "@/lib/format";
import type { ImageSet } from "@/lib/types";

export interface ImageFrameProps {
  image?: ImageSet | null;
  alt: string;
  aspect?: "4/5" | "1/1" | "4/3" | "3/4" | "16/10" | "21/9";
  priority?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function ImageFrame({
  image,
  alt,
  aspect = "4/5",
  priority = false,
  className,
  children,
}: ImageFrameProps) {
  const aspectClasses = {
    "4/5": "aspect-[4/5]",
    "1/1": "aspect-square",
    "4/3": "aspect-[4/3]",
    "3/4": "aspect-[3/4]",
    "16/10": "aspect-[16/10]",
    "21/9": "aspect-[21/9]",
  }[aspect];

  const src = image?.card || image?.large || undefined;

  return (
    <div
      className={cx(
        "relative overflow-hidden rounded-sm bg-sand-100",
        aspectClasses,
        className
      )}
    >
      {src ? (
        <img
          src={src}
          srcSet={
            image?.thumb && image?.card && image?.large
              ? `${image.thumb} 400w, ${image.card} 800w, ${image.large} 1600w`
              : undefined
          }
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          alt={alt}
          loading={priority ? "eager" : "lazy"}
          fetchPriority={priority ? "high" : "auto"}
          className="size-full object-cover transition-transform duration-500 ease-out"
        />
      ) : (
        <div className="flex size-full items-center justify-center bg-sand-100 text-muted">
          <Emblem size={32} tone="brand" className="opacity-40" />
        </div>
      )}
      {children}
    </div>
  );
}
