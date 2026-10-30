"use client";

import React, { useState } from "react";
import { cx } from "@/lib/format";

export interface TabItem {
  id?: string;
  value?: string;
  label: React.ReactNode;
  content?: React.ReactNode;
  count?: number;
  icon?: React.ReactNode;
}

export interface TabsProps<T = string> {
  items?: TabItem[];
  tabs?: (TabItem & { value?: T })[];
  value?: T;
  defaultValue?: T;
  onChange?: (val: T) => void;
  variant?: "underline" | "pills";
  orientation?: "horizontal" | "vertical";
  className?: string;
}

export function Tabs<T extends string = string>({
  items,
  tabs,
  value: controlledValue,
  defaultValue,
  onChange,
  variant = "underline",
  orientation = "horizontal",
  className,
}: TabsProps<T>) {
  const isVertical = orientation === "vertical";
  const rawList = tabs || items || [];
  const tabList = rawList.map((t) => {
    const tabObj = t as unknown as Record<string, unknown>;
    const tabId = ((tabObj.value || tabObj.id) as T) || ("tab" as T);
    return {
      id: tabId,
      label: tabObj.label as React.ReactNode,
      content: tabObj.content as React.ReactNode | undefined,
      count: tabObj.count as number | undefined,
      icon: tabObj.icon as React.ReactNode | undefined,
    };
  });

  const [uncontrolledValue, setUncontrolledValue] = useState<T>(
    defaultValue || tabList[0]?.id || ("" as T)
  );

  const activeValue = controlledValue !== undefined ? controlledValue : uncontrolledValue;

  const handleSelect = (id: T) => {
    if (controlledValue === undefined) {
      setUncontrolledValue(id);
    }
    onChange?.(id);
  };

  const activeTabItem = tabList.find((t) => t.id === activeValue);

  return (
    <div className="w-full flex flex-col">
      <div
        role="tablist"
        aria-orientation={orientation}
        className={cx(
          "flex gap-2 overflow-x-auto no-scrollbar",
          isVertical ? "flex-col border-s border-line" : variant === "underline" ? "border-b border-line" : "",
          className
        )}
      >
        {tabList.map((tab) => {
          const active = tab.id === activeValue;

          if (variant === "pills") {
            return (
              <button
                key={String(tab.id)}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => handleSelect(tab.id)}
                className={cx(
                  "inline-flex items-center gap-1.5 rounded-xs px-3.5 py-1.5 text-caption font-semibold transition-colors cursor-pointer select-none",
                  active
                    ? "bg-brand text-on-dark shadow-xs"
                    : "bg-surface-alt text-muted hover:text-text hover:bg-sand-200"
                )}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span
                    className={cx(
                      "rounded-full px-1.5 text-caption",
                      active ? "bg-white/20 text-white" : "bg-sand-300 text-muted"
                    )}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          }

          return (
            <button
              key={String(tab.id)}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => handleSelect(tab.id)}
              className={cx(
                "relative inline-flex items-center gap-2 pb-3 pt-2 text-eyebrow transition-colors cursor-pointer select-none whitespace-nowrap",
                isVertical ? "ps-4 pe-2 text-start" : "px-3 text-center",
                active
                  ? "text-brand font-semibold"
                  : "text-muted hover:text-text hover:border-line-strong"
              )}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="ms-1 rounded-full bg-sand-200 px-1.5 py-0.5 text-caption font-mono text-muted">
                  {tab.count}
                </span>
              )}
              {/* Animated underline indicator */}
              {active && !isVertical && (
                <span className="absolute inset-x-0 bottom-0 h-0.5 bg-brand animate-fade-in" />
              )}
              {active && isVertical && (
                <span className="absolute inset-y-0 start-0 w-0.5 bg-brand animate-fade-in" />
              )}
            </button>
          );
        })}
      </div>

      {activeTabItem?.content && (
        <div role="tabpanel" className="w-full">
          {activeTabItem.content}
        </div>
      )}
    </div>
  );
}
