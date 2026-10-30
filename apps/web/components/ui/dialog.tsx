"use client";

import { X } from "lucide-react";
import React, { useEffect, useRef } from "react";
import { cx } from "@/lib/format";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  size = "md",
  className,
}: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    else if (!open && el.open) el.close();
  }, [open]);

  const sizeClasses = {
    sm: "max-w-md",
    md: "max-w-lg",
    lg: "max-w-2xl",
  }[size];

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className={cx(
        "fixed inset-0 m-auto w-[calc(100%-2rem)] rounded-md border border-line bg-surface p-6 shadow-sheet backdrop:bg-ink-950/50 backdrop:backdrop-blur-xs",
        sizeClasses,
        className
      )}
    >
      <div className="flex flex-col gap-4">
        {(title || description) && (
          <div className="flex items-start justify-between gap-4 border-b border-line pb-3">
            <div>
              {title && <h2 className="text-h3 text-text">{title}</h2>}
              {description && <p className="text-body-s text-muted mt-1">{description}</p>}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="flex size-8 shrink-0 items-center justify-center rounded-xs text-muted hover:bg-sand-100 hover:text-text cursor-pointer"
              aria-label="Close"
            >
              <X className="size-4" />
            </button>
          </div>
        )}
        <div className="overflow-y-auto max-h-[75vh]">{children}</div>
      </div>
    </dialog>
  );
}
