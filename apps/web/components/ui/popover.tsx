"use client";

import React, { useEffect, useRef, useState } from "react";
import { cx } from "@/lib/format";

export interface PopoverProps {
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: "start" | "end" | "center";
  className?: string;
}

export function Popover({
  trigger,
  children,
  align = "start",
  className,
}: PopoverProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const alignClasses = {
    start: "start-0",
    end: "end-0",
    center: "start-1/2 -translate-x-1/2",
  }[align];

  return (
    <div ref={containerRef} className="relative inline-block">
      <div onClick={() => setOpen(!open)} className="cursor-pointer">
        {trigger}
      </div>
      {open && (
        <div
          role="dialog"
          className={cx(
            "absolute top-full z-50 mt-2 min-w-[200px] rounded-md border border-line bg-surface p-2 shadow-pop animate-in fade-in zoom-in-95 duration-150",
            alignClasses,
            className
          )}
        >
          {children}
        </div>
      )}
    </div>
  );
}
