"use client";

import { X } from "lucide-react";
import React, { useEffect, useRef } from "react";
import { cx } from "@/lib/format";

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  side?: "end" | "start" | "bottom";
  width?: "default" | "wide";
  className?: string;
}

export function Drawer({
  open,
  onClose,
  title,
  children,
  footer,
  side = "end",
  width = "default",
  className,
}: DrawerProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    else if (!open && el.open) el.close();
  }, [open]);

  const sideClasses = {
    end: "ms-auto me-0 h-full max-h-none w-full sm:max-w-md md:max-w-md rounded-none border-s border-line",
    start: "me-auto ms-0 h-full max-h-none w-full sm:max-w-md md:max-w-sm rounded-none border-e border-line",
    bottom: "mt-auto mb-0 w-full max-h-[85vh] rounded-t-lg border-t border-line",
  }[side];

  const widthOverride = width === "wide" && side === "end" ? "sm:max-w-lg md:max-w-xl" : "";

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className={cx(
        "fixed inset-0 m-0 bg-surface p-0 shadow-sheet backdrop:bg-ink-950/50 backdrop:backdrop-blur-xs",
        sideClasses,
        widthOverride,
        className
      )}
    >
      <div className="flex flex-col h-full">
        {/* Drag handle on mobile bottom drawer */}
        {side === "bottom" && (
          <div className="mx-auto mt-2.5 h-1 w-10 rounded-full bg-sand-300" />
        )}

        {/* Header */}
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <div className="min-w-0 flex-1">
            {typeof title === "string" ? (
              <h2 className="text-h3 text-text truncate">{title}</h2>
            ) : (
              title
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex size-9 shrink-0 items-center justify-center rounded-xs text-muted hover:bg-sand-100 hover:text-text cursor-pointer ms-3"
            aria-label="Close"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">{children}</div>

        {/* Sticky Footer */}
        {footer && (
          <div className="sticky bottom-0 border-t border-line bg-surface p-4 shadow-2xs">
            {footer}
          </div>
        )}
      </div>
    </dialog>
  );
}

/** Backward compatible Sheet */
export function Sheet({
  open,
  onClose,
  title,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={title}
      side="end"
      width={wide ? "wide" : "default"}
    >
      {children}
    </Drawer>
  );
}
