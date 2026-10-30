"use client";

import React from "react";
import { cx } from "@/lib/format";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  className?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (row: T) => string;
  renderCard?: (row: T) => React.ReactNode;
  emptyNode?: React.ReactNode;
  className?: string;
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  renderCard,
  emptyNode,
  className,
}: DataTableProps<T>) {
  if (!data.length) {
    return (
      <div className="rounded-sm border border-line bg-surface p-8 text-center text-muted">
        {emptyNode || "No items found."}
      </div>
    );
  }

  return (
    <div className={cx("w-full overflow-hidden rounded-sm border border-line bg-surface", className)}>
      {/* Mobile Card Layout if provided */}
      {renderCard && (
        <div className="flex flex-col divide-y divide-line md:hidden">
          {data.map((row) => (
            <div key={keyExtractor(row)} className="p-4">
              {renderCard(row)}
            </div>
          ))}
        </div>
      )}

      {/* Desktop / Standard Table */}
      <div className={cx("overflow-x-auto", renderCard ? "hidden md:block" : "block")}>
        <table className="w-full text-start text-body-s">
          <thead className="sticky top-0 border-b border-line bg-sand-50/80 text-eyebrow text-muted backdrop-blur-xs">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={cx("px-4 py-3.5 text-start font-semibold", col.className)}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {data.map((row) => (
              <tr
                key={keyExtractor(row)}
                className="transition-colors hover:bg-surface-alt/70"
              >
                {columns.map((col) => (
                  <td key={col.key} className={cx("px-4 py-3.5 text-text", col.className)}>
                    {col.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
