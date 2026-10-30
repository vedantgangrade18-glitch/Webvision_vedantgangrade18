import { Check } from "lucide-react";
import React from "react";
import { cx } from "@/lib/format";

export interface StepItem {
  id?: string;
  label?: React.ReactNode;
  title?: React.ReactNode;
  description?: React.ReactNode;
  detail?: React.ReactNode;
  status?: "done" | "current" | "upcoming" | "warn";
  state?: "done" | "current" | "todo" | "warn";
}

export function Stepper({
  steps,
  currentStep,
  orientation = "horizontal",
  className,
}: {
  steps: StepItem[];
  currentStep?: number;
  orientation?: "horizontal" | "vertical";
  className?: string;
}) {
  const isHoriz = orientation === "horizontal";

  return (
    <ol
      className={cx(
        "flex w-full",
        isHoriz ? "items-center justify-between" : "flex-col gap-4",
        className
      )}
    >
      {steps.map((step, idx) => {
        let rawStatus = step.status || step.state || "upcoming";
        if (currentStep !== undefined) {
          if (idx < currentStep) rawStatus = "done";
          else if (idx === currentStep) rawStatus = "current";
          else rawStatus = "upcoming";
        }
        const isDone = rawStatus === "done";
        const isCurrent = rawStatus === "current";
        const isWarn = rawStatus === "warn";
        const label = step.label || step.title;
        const desc = step.description || step.detail;

        return (
          <li
            key={step.id || idx}
            className={cx(
              "flex items-center gap-3 relative",
              isHoriz && "flex-1 last:flex-none"
            )}
          >
            <div className="flex items-center gap-3">
              <span
                className={cx(
                  "flex size-7 shrink-0 items-center justify-center rounded-full text-caption font-semibold transition-colors",
                  isDone
                    ? "bg-brand text-on-dark"
                    : isCurrent
                    ? "border-2 border-brand text-brand bg-surface"
                    : isWarn
                    ? "bg-gold-500 text-ink-900"
                    : "border border-line bg-surface-alt text-muted"
                )}
              >
                {isDone ? (
                  <Check className="size-4 stroke-[2.5]" />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </span>

              <div className="flex flex-col">
                <span
                  className={cx(
                    "text-body-s font-medium",
                    isCurrent ? "text-brand font-semibold" : "text-text"
                  )}
                >
                  {label}
                </span>
                {desc && (
                  <span className="text-caption text-muted">{desc}</span>
                )}
              </div>
            </div>

            {/* Connecting Line (Horizontal only) */}
            {isHoriz && (
              <div
                className={cx(
                  "ms-4 me-4 h-px flex-1 transition-colors",
                  isDone ? "bg-brand" : "bg-line"
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
