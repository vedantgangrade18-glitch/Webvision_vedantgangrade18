"use client";

import { Check } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  hint?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { label, hint, className, id, checked, ...rest },
  ref
) {
  return (
    <label htmlFor={id} className={cx("inline-flex items-start gap-2.5 cursor-pointer select-none", className)}>
      <div className="relative mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-xs border border-line-strong bg-surface transition-colors has-checked:border-brand has-checked:bg-brand">
        <input
          ref={ref}
          id={id}
          type="checkbox"
          checked={checked}
          className="peer sr-only"
          {...rest}
        />
        <Check className="size-3.5 text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
      </div>
      {(label || hint) && (
        <div className="flex flex-col">
          {label && <span className="text-body-s font-medium text-text leading-tight">{label}</span>}
          {hint && <span className="text-caption text-muted mt-0.5">{hint}</span>}
        </div>
      )}
    </label>
  );
});

export interface RadioProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  hint?: string;
}

export const Radio = React.forwardRef<HTMLInputElement, RadioProps>(function Radio(
  { label, hint, className, id, checked, ...rest },
  ref
) {
  return (
    <label htmlFor={id} className={cx("inline-flex items-start gap-2.5 cursor-pointer select-none", className)}>
      <div className="relative mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-line-strong bg-surface transition-colors has-checked:border-brand">
        <input
          ref={ref}
          id={id}
          type="radio"
          checked={checked}
          className="peer sr-only"
          {...rest}
        />
        <span className="size-2.5 rounded-full bg-brand opacity-0 peer-checked:opacity-100 transition-opacity" />
      </div>
      {(label || hint) && (
        <div className="flex flex-col">
          {label && <span className="text-body-s font-medium text-text leading-tight">{label}</span>}
          {hint && <span className="text-caption text-muted mt-0.5">{hint}</span>}
        </div>
      )}
    </label>
  );
});

export interface RadioCardProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type" | "title"> {
  title: React.ReactNode;
  description?: React.ReactNode;
  badge?: React.ReactNode;
  icon?: React.ReactNode;
}

export const RadioCard = React.forwardRef<HTMLInputElement, RadioCardProps>(function RadioCard(
  { title, description, badge, icon, className, id, checked, ...rest },
  ref
) {
  return (
    <label
      htmlFor={id}
      className={cx(
        "relative flex cursor-pointer items-start gap-3 rounded-xs border p-4 transition-all duration-150 select-none",
        checked
          ? "border-brand bg-brand-soft ring-1 ring-brand"
          : "border-line bg-surface hover:border-line-strong",
        className
      )}
    >
      <input
        ref={ref}
        id={id}
        type="radio"
        checked={checked}
        className="sr-only"
        {...rest}
      />
      <div className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-line-strong bg-surface">
        <span className={cx("size-2.5 rounded-full bg-brand transition-opacity", checked ? "opacity-100" : "opacity-0")} />
      </div>
      {icon && <span className="shrink-0 text-muted mt-0.5">{icon}</span>}
      <div className="flex flex-1 flex-col">
        <div className="flex items-center justify-between gap-2">
          <span className="text-body-s font-semibold text-text">{title}</span>
          {badge}
        </div>
        {description && <p className="text-caption text-muted mt-0.5">{description}</p>}
      </div>
    </label>
  );
});
