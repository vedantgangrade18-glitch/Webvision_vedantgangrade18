"use client";

import { AlertCircle, CheckCircle2, Clock, FileText, PauseCircle, ShieldAlert } from "lucide-react";
import { type ReactNode } from "react";
import { cx } from "@/lib/format";

/* -------------------------------------------------------------------------- */
/* 1. Underline Tabs (Top level tabs like Single Uploads / Bulk Uploads)      */
/* -------------------------------------------------------------------------- */
export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

export function UnderlineTabs({
  tabs,
  activeId,
  onChange,
  className,
}: {
  tabs: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div className={cx("flex items-center gap-6 border-b border-[#E3E5EC]", className)}>
      {tabs.map((tab) => {
        const active = tab.id === activeId;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={cx(
              "pb-3 text-[14px] font-semibold transition-all relative whitespace-nowrap",
              active ? "text-[#4B3BD1]" : "text-[#6B7080] hover:text-[#111827]"
            )}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span className="ms-1.5 text-[12.5px] font-normal text-[#6B7080]">
                ({tab.count})
              </span>
            )}
            {active && (
              <span className="absolute bottom-0 inset-x-0 h-0.5 bg-[#4B3BD1] rounded-t-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 2. SubTabs (Text chips for Status Filters: All, Action needed, etc.)       */
/* -------------------------------------------------------------------------- */
export function SubTabs({
  tabs,
  activeId,
  onChange,
  className,
}: {
  tabs: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div className={cx("flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar", className)}>
      {tabs.map((tab) => {
        const active = tab.id === activeId;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={cx(
              "px-3 py-1.5 rounded-md text-[13px] font-medium transition-colors whitespace-nowrap flex items-center gap-1.5",
              active
                ? "bg-[#EFEDFC] text-[#4B3BD1] font-semibold ring-1 ring-[#4B3BD1]/20"
                : "text-[#6B7080] hover:bg-[#F1F2F6] hover:text-[#111827]"
            )}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span className={cx("text-[11.5px]", active ? "text-[#4B3BD1]" : "text-[#7C8196]")}>
                ({tab.count})
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 3. InfoStrip (Yellow tip bar with lightbulb icon)                          */
/* -------------------------------------------------------------------------- */
export function InfoStrip({
  children,
  icon,
  className,
}: {
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cx(
        "flex items-center gap-2.5 px-3.5 py-2.5 rounded-md border border-[#F3DFA0] bg-[#FFF7DD] text-[#744210] text-[12.5px] leading-snug",
        className
      )}
    >
      <span className="shrink-0 text-base leading-none">
        {icon || "💡"}
      </span>
      <div className="flex-1">{children}</div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* 4. StatusPill (§4 status mapping)                                         */
/* -------------------------------------------------------------------------- */
export type KaruStatus =
  | "draft"
  | "action_needed"
  | "processing"
  | "not_verified"
  | "verified"
  | "paused";

export function StatusPill({
  status,
  verificationStatus,
  quantityAvailable,
  label,
  className,
}: {
  status?: string;
  verificationStatus?: string;
  quantityAvailable?: number;
  label?: string;
  className?: string;
}) {
  // Determine normalized role
  let role: KaruStatus = "not_verified";
  let displayLabel = label;

  if (status === "draft") {
    role = "draft";
    displayLabel = displayLabel || "Draft";
  } else if (
    status === "action_needed" ||
    (quantityAvailable !== undefined && quantityAvailable === 0)
  ) {
    role = "action_needed";
    displayLabel = displayLabel || (quantityAvailable === 0 ? "Out of stock" : "Action needed");
  } else if (status === "processing" || verificationStatus === "checking") {
    role = "processing";
    displayLabel = displayLabel || "QC in progress";
  } else if (verificationStatus === "verified") {
    role = "verified";
    displayLabel = displayLabel || "Live · Verified";
  } else if (status === "paused") {
    role = "paused";
    displayLabel = displayLabel || "Paused";
  } else {
    role = "not_verified";
    displayLabel = displayLabel || "Not verified yet";
  }

  const styles: Record<
    KaruStatus,
    { bg: string; text: string; border: string; icon: ReactNode }
  > = {
    draft: {
      bg: "bg-gray-50",
      text: "text-gray-700",
      border: "border-gray-300",
      icon: <FileText className="size-3" />,
    },
    action_needed: {
      bg: "bg-[#FBEDE6]",
      text: "text-[#B9532E]",
      border: "border-[#F3D9CB]",
      icon: <AlertCircle className="size-3" />,
    },
    processing: {
      bg: "bg-[#EFEDFC]",
      text: "text-[#4B3BD1]",
      border: "border-[#4B3BD1]/20",
      icon: <Clock className="size-3 animate-spin" />,
    },
    not_verified: {
      bg: "bg-amber-50",
      text: "text-amber-800",
      border: "border-amber-200",
      icon: <ShieldAlert className="size-3" />,
    },
    verified: {
      bg: "bg-emerald-50",
      text: "text-emerald-700",
      border: "border-emerald-200",
      icon: <CheckCircle2 className="size-3" />,
    },
    paused: {
      bg: "bg-gray-100",
      text: "text-gray-600",
      border: "border-gray-300",
      icon: <PauseCircle className="size-3" />,
    },
  };

  const current = styles[role];

  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[12px] font-semibold border",
        current.bg,
        current.text,
        current.border,
        className
      )}
    >
      {current.icon}
      <span>{displayLabel}</span>
    </span>
  );
}
