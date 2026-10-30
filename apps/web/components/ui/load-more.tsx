import React from "react";
import { Button } from "./button";
import { cx } from "@/lib/format";

export interface LoadMoreProps {
  current: number;
  total: number;
  onLoadMore: () => void;
  loading?: boolean;
  className?: string;
}

export function LoadMore({
  current,
  total,
  onLoadMore,
  loading = false,
  className,
}: LoadMoreProps) {
  if (current >= total) return null;
  const percent = Math.min(100, Math.round((current / total) * 100));

  return (
    <div className={cx("flex flex-col items-center gap-3 py-8", className)}>
      <p className="text-caption text-muted">
        Showing <span className="font-semibold text-text tabular-nums">{current}</span> of{" "}
        <span className="font-semibold text-text tabular-nums">{total}</span> pieces
      </p>
      <div className="h-1 w-48 rounded-full bg-sand-200 overflow-hidden">
        <div
          className="h-full bg-brand transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
      <Button
        variant="secondary"
        size="M"
        onClick={onLoadMore}
        loading={loading}
        className="mt-2 min-w-40"
      >
        Load more
      </Button>
    </div>
  );
}
