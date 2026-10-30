"use client";

import React from "react";
import { cx } from "@/lib/format";

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: React.ReactNode;
  hint?: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
  id?: string;
  className?: string;
}

export function Switch({
  checked,
  onChange,
  label,
  hint,
  description,
  disabled = false,
  id,
  className,
}: SwitchProps) {
  const note = description || hint;

  return (
    <label
      htmlFor={id}
      className={cx(
        "inline-flex items-center justify-between gap-4 cursor-pointer select-none",
        disabled && "opacity-50 cursor-not-allowed",
        className
      )}
    >
      {(label || note) && (
        <div className="flex flex-col">
          {label && <span className="text-body-s font-medium text-text">{label}</span>}
          {note && <span className="text-caption text-muted">{note}</span>}
        </div>
      )}
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cx(
          "relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-out focus-visible:outline-none",
          checked ? "bg-brand" : "bg-sand-300"
        )}
      >
        <span
          className={cx(
            "pointer-events-none inline-block size-5 transform rounded-full bg-white shadow-xs transition duration-200 ease-out",
            checked ? "translate-x-5" : "translate-x-0"
          )}
        />
      </button>
    </label>
  );
}
