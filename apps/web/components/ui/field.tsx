import { AlertCircle } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function Field({
  label,
  htmlFor,
  hint,
  error,
  required,
  children,
  className,
}: FieldProps) {
  return (
    <div className={cx("flex flex-col gap-1.5", className)}>
      <label htmlFor={htmlFor} className="flex items-center gap-1 text-body-s font-medium text-text">
        <span>{label}</span>
        {required && <span className="text-danger-600 font-bold" aria-hidden>*</span>}
      </label>
      {children}
      {hint && !error && <p className="text-caption text-muted">{hint}</p>}
      {error && (
        <p className="flex items-center gap-1.5 text-caption text-danger-600 font-medium">
          <AlertCircle className="size-3.5 shrink-0" aria-hidden />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}
