"use client";

import React from "react";
import { cx } from "@/lib/format";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, invalid, disabled, ...rest },
  ref
) {
  return (
    <textarea
      ref={ref}
      disabled={disabled}
      className={cx(
        "w-full rounded-xs border bg-surface p-3 text-body text-text placeholder:text-subtle transition-colors duration-150 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed",
        invalid
          ? "border-danger-600 focus:ring-2 focus:ring-danger-600/20"
          : "border-line-strong focus:border-brand focus:ring-3 focus:ring-brand/15",
        className
      )}
      {...rest}
    />
  );
});
