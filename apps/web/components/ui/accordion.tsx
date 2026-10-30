import { ChevronDown, Plus } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface AccordionItemProps {
  value?: string;
  title: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  iconStyle?: "plus" | "chevron";
  badge?: React.ReactNode;
  className?: string;
}

export function AccordionItem({
  title,
  children,
  defaultOpen = false,
  iconStyle = "plus",
  badge,
  className,
}: AccordionItemProps) {
  return (
    <details
      open={defaultOpen}
      className={cx(
        "group border-b border-line py-3.5 transition-colors",
        className
      )}
    >
      <summary className="flex cursor-pointer items-center justify-between gap-4 select-none list-none text-body-s font-medium text-ink-900 focus-visible:outline-none hover:text-brand">
        <div className="flex items-center gap-2">
          <span>{title}</span>
          {badge}
        </div>
        {iconStyle === "plus" ? (
          <span className="flex size-5 shrink-0 items-center justify-center text-muted group-open:rotate-45 transition-transform duration-200">
            <Plus className="size-4" />
          </span>
        ) : (
          <ChevronDown className="size-4 shrink-0 text-muted group-open:rotate-180 transition-transform duration-200" />
        )}
      </summary>
      <div className="pt-2 pb-1 text-body-s leading-relaxed">
        {children}
      </div>
    </details>
  );
}

export interface AccordionProps {
  title?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean | string;
  iconStyle?: "plus" | "chevron";
  badge?: React.ReactNode;
  className?: string;
}

export function Accordion({
  title,
  children,
  defaultOpen,
  iconStyle = "plus",
  badge,
  className,
}: AccordionProps) {
  if (title) {
    return (
      <AccordionItem
        title={title}
        defaultOpen={typeof defaultOpen === "boolean" ? defaultOpen : false}
        iconStyle={iconStyle}
        badge={badge}
        className={className}
      >
        {children}
      </AccordionItem>
    );
  }
  return <div className={className}>{children}</div>;
}
