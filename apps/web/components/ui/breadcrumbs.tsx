import Link from "next/link";
import { ArrowLeft, ChevronRight } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Breadcrumbs({
  items,
  className,
}: {
  items: BreadcrumbItem[];
  className?: string;
}) {
  if (!items.length) return null;
  const parent = items.length > 1 ? items[items.length - 2] : null;

  return (
    <nav aria-label="Breadcrumb" className={cx("flex items-center", className)}>
      {/* Mobile Collapse View */}
      {parent && parent.href && (
        <div className="flex sm:hidden items-center">
          <Link
            href={parent.href}
            className="inline-flex items-center gap-1.5 text-caption font-medium text-muted hover:text-text"
          >
            <ArrowLeft className="size-3.5 flip-rtl" />
            <span>{parent.label}</span>
          </Link>
        </div>
      )}

      {/* Desktop / Full Breadcrumbs */}
      <ol className={cx("items-center gap-1.5 text-caption text-muted", parent ? "hidden sm:flex" : "flex")}>
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li key={index} className="inline-flex items-center gap-1.5">
              {index > 0 && (
                <ChevronRight className="size-3 text-ink-300 flip-rtl shrink-0" aria-hidden />
              )}
              {isLast || !item.href ? (
                <span className="font-semibold text-text truncate max-w-[24ch]" aria-current="page">
                  {item.label}
                </span>
              ) : (
                <Link
                  href={item.href}
                  className="hover:text-brand transition-colors truncate max-w-[20ch]"
                >
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
