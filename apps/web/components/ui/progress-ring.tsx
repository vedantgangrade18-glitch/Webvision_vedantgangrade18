import React from "react";

export function ProgressRing({
  value,
  size = 36,
  children,
}: {
  value: number;
  size?: number;
  children?: React.ReactNode;
}) {
  const r = size / 2 - 2;
  const c = 2 * Math.PI * r;

  return (
    <span
      className="relative inline-flex items-center justify-center shrink-0"
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        className="absolute inset-0 -rotate-90"
        aria-hidden
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="var(--color-sand-200)"
          strokeWidth="3"
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="var(--color-brand)"
          strokeWidth="3"
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - value / 100)}
          strokeLinecap="round"
        />
      </svg>
      {children}
    </span>
  );
}
