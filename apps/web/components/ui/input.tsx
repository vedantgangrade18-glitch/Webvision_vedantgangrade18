"use client";

import React from "react";
import { cx } from "@/lib/format";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  prefixNode?: React.ReactNode;
  suffixNode?: React.ReactNode;
  invalid?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, prefixNode, suffixNode, invalid, disabled, ...rest },
  ref
) {
  return (
    <div
      className={cx(
        "flex min-h-12 w-full items-center rounded-xs border bg-surface transition-colors duration-150",
        invalid
          ? "border-danger-600 focus-within:ring-2 focus-within:ring-danger-600/20"
          : "border-line-strong focus-within:border-brand focus-within:ring-3 focus-within:ring-brand/15",
        disabled ? "opacity-50 cursor-not-allowed bg-sand-100/60" : ""
      )}
    >
      {prefixNode && (
        <span className="flex items-center ps-3 pe-1.5 text-muted select-none text-body-s">
          {prefixNode}
        </span>
      )}
      <input
        ref={ref}
        disabled={disabled}
        className={cx(
          "w-full bg-transparent px-3.5 py-2.5 text-body text-text placeholder:text-subtle focus:outline-none disabled:cursor-not-allowed",
          prefixNode ? "ps-1.5" : "",
          suffixNode ? "pe-1.5" : "",
          className
        )}
        {...rest}
      />
      {suffixNode && (
        <span className="flex items-center pe-3 ps-1.5 text-muted select-none text-body-s">
          {suffixNode}
        </span>
      )}
    </div>
  );
});
