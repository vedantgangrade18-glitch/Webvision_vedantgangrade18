"use client";

import {
  ChevronLeft,
  ChevronRight,
  Copy,
  ExternalLink,
  MoreVertical,
  Pause,
  Play,
  QrCode,
  Share2,
  Trash2,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { type ReactNode, useState } from "react";
import { StatusPill } from "@/components/seller/Tabs";
import { cx, inr } from "@/lib/format";
import type { ImageSet } from "@/lib/types";

export interface ProductRowItem {
  id: string;
  code: string;
  title: string;
  categoryName: string;
  parentCategory?: string;
  thumbnailUrl?: string;
  imageSet?: ImageSet | null;
  createdAt: string;
  quantityTotal: number;
  quantityAvailable: number;
  priceInr: number | null;
  pricePosition?: "below" | "in_range" | "above" | "unknown";
  status: string; // draft, action_needed, processing, published, paused
  verificationStatus: string; // none, checking, not_verified, verified
}

interface DataTableProps {
  items: ProductRowItem[];
  totalCount: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  onRowClick?: (item: ProductRowItem) => void;
  onEdit?: (item: ProductRowItem) => void;
  onPauseResume?: (item: ProductRowItem) => void;
  onDelete?: (item: ProductRowItem) => void;
  className?: string;
}

export function ProductsDataTable({
  items,
  totalCount,
  currentPage = 1,
  pageSize = 20,
  onPageChange,
  onPageSizeChange,
  onRowClick,
  onEdit,
  onPauseResume,
  onDelete,
  className,
}: DataTableProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const handleCopyCode = (code: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;
  const startItem = totalCount > 0 ? (currentPage - 1) * pageSize + 1 : 0;
  const endItem = Math.min(currentPage * pageSize, totalCount);

  return (
    <div className={cx("bg-white rounded-lg border border-[#E3E5EC] overflow-hidden shadow-xs", className)}>
      {/* Desktop Table View (>= 768px) */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-start text-[13px] border-collapse">
          <thead>
            <tr className="bg-[#F8F9FC] border-b border-[#E3E5EC] text-[#6B7080] font-medium text-[12px] uppercase tracking-wider text-start">
              <th className="py-3 px-3.5 w-12 text-center">S.no</th>
              <th className="py-3 px-3 w-16 text-center">Image</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Product code</th>
              <th className="py-3 px-4">Created on</th>
              <th className="py-3 px-4">Product IDs</th>
              <th className="py-3 px-4">Price</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-end">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E3E5EC]">
            {items.map((row, idx) => {
              const rowNum = (currentPage - 1) * pageSize + idx + 1;
              const isOutOfStock = row.quantityAvailable === 0 && row.status === "published";

              return (
                <tr
                  key={row.id}
                  onClick={() => onRowClick?.(row)}
                  className="hover:bg-[#F8F9FC]/80 transition-colors cursor-pointer group"
                >
                  {/* S.no */}
                  <td className="py-3 px-3.5 text-center text-[#6B7080] font-mono text-[12px]">
                    {rowNum}
                  </td>

                  {/* Catalog Thumbnail (4:5 ratio) */}
                  <td className="py-3 px-3 text-center">
                    <div className="relative size-12 mx-auto rounded-md overflow-hidden bg-[#F1F2F6] border border-[#E3E5EC] shrink-0">
                      {row.thumbnailUrl ? (
                        <img
                          src={row.thumbnailUrl}
                          alt={row.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="flex items-center justify-center w-full h-full text-[#A3A7B5] text-[10px]">
                          No photo
                        </div>
                      )}
                    </div>
                  </td>

                  {/* Category & Title */}
                  <td className="py-3 px-4 max-w-[200px]">
                    <div className="font-semibold text-[#111827] line-clamp-1 group-hover:text-[#4B3BD1]">
                      {row.title || "Untitled Product"}
                    </div>
                    <div className="text-[12px] text-[#6B7080] truncate">
                      {row.parentCategory ? `${row.parentCategory} › ` : ""}
                      {row.categoryName}
                    </div>
                  </td>

                  {/* Product Code with Copy Icon */}
                  <td className="py-3 px-4">
                    {row.code ? (
                      <button
                        type="button"
                        onClick={(e) => handleCopyCode(row.code, e)}
                        className="inline-flex items-center gap-1.5 font-mono text-[12px] font-semibold text-[#111827] hover:text-[#4B3BD1] hover:underline"
                        title="Copy code"
                      >
                        <span>{row.code}</span>
                        <Copy className="size-3 text-[#A3A7B5] group-hover:text-[#4B3BD1]" />
                        {copiedCode === row.code && (
                          <span className="text-[10px] text-[#16A34A] font-sans">Copied!</span>
                        )}
                      </button>
                    ) : (
                      <span className="text-[#A3A7B5]">—</span>
                    )}
                  </td>

                  {/* Created On */}
                  <td className="py-3 px-4 text-[#6B7080] whitespace-nowrap text-[12px]">
                    {row.createdAt}
                  </td>

                  {/* Karu IDs / Stock count */}
                  <td className="py-3 px-4 whitespace-nowrap">
                    {row.status === "draft" ? (
                      <span className="text-[#A3A7B5]">—</span>
                    ) : (
                      <div className="flex flex-col">
                        <span className={cx("font-semibold", isOutOfStock ? "text-[#B9532E]" : "text-[#111827]")}>
                          {row.quantityTotal} pcs
                        </span>
                        <span className={cx("text-[11px]", isOutOfStock ? "text-[#B9532E] font-medium" : "text-[#6B7080]")}>
                          {isOutOfStock ? "Out of stock" : `${row.quantityAvailable} left`}
                        </span>
                      </div>
                    )}
                  </td>

                  {/* Price with Price Position Dot */}
                  <td className="py-3 px-4 whitespace-nowrap">
                    {row.priceInr ? (
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-[#111827]">{inr(row.priceInr)}</span>
                        {row.pricePosition === "in_range" && (
                          <span className="size-2 rounded-full bg-[#16A34A]" title="Price within market range" />
                        )}
                        {row.pricePosition === "below" && (
                          <span className="size-2 rounded-full bg-[#D97706]" title="Price below market range" />
                        )}
                        {row.pricePosition === "above" && (
                          <span className="size-2 rounded-full bg-[#4B3BD1]" title="Premium craft price" />
                        )}
                      </div>
                    ) : (
                      <span className="text-[#A3A7B5]">—</span>
                    )}
                  </td>

                  {/* Status Pill */}
                  <td className="py-3 px-4 whitespace-nowrap">
                    <StatusPill
                      status={row.status}
                      verificationStatus={row.verificationStatus}
                      quantityAvailable={row.quantityAvailable}
                    />
                  </td>

                  {/* Actions column */}
                  <td className="py-3 px-4 text-end whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-2">
                      {/* Main action button */}
                      <Link
                        href={row.status === "draft" ? `/sell/new/${row.id}` : `/sell/products/${row.id}`}
                        className={cx(
                          "px-3 py-1.5 rounded-md text-[12.5px] font-semibold transition-colors shadow-2xs",
                          row.status === "draft"
                            ? "bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white"
                            : row.status === "action_needed"
                            ? "bg-[#B9532E] hover:bg-[#9E482B] text-white"
                            : "border border-[#E3E5EC] bg-white hover:bg-[#F1F2F6] text-[#111827]"
                        )}
                      >
                        {row.status === "draft"
                          ? "Continue"
                          : row.status === "action_needed"
                          ? "Fix now"
                          : "Edit product"}
                      </Link>

                      {/* Dropdown Kebab menu */}
                      <div className="relative">
                        <button
                          type="button"
                          onClick={() => setActiveMenuId(activeMenuId === row.id ? null : row.id)}
                          className="p-1 rounded-md text-[#6B7080] hover:text-[#111827] hover:bg-[#F1F2F6]"
                          aria-label="More options"
                        >
                          <MoreVertical className="size-4" />
                        </button>

                        {activeMenuId === row.id && (
                          <div className="absolute end-0 top-full mt-1 w-44 py-1 bg-white border border-[#E3E5EC] rounded-lg shadow-lg z-30 text-[13px] text-[#111827] text-start">
                            <Link
                              href={`/sell/products/${row.id}`}
                              className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#F1F2F6]"
                            >
                              <ExternalLink className="size-3.5 text-[#6B7080]" />
                              <span>View details</span>
                            </Link>
                            <Link
                              href={`/sell/share?id=${row.id}`}
                              className="flex items-center gap-2 px-3 py-1.5 hover:bg-[#F1F2F6]"
                            >
                              <Share2 className="size-3.5 text-[#6B7080]" />
                              <span>Share & QR</span>
                            </Link>
                            {row.status === "published" && (
                              <button
                                type="button"
                                onClick={() => {
                                  setActiveMenuId(null);
                                  onPauseResume?.(row);
                                }}
                                className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-[#F1F2F6] text-start"
                              >
                                <Pause className="size-3.5 text-[#6B7080]" />
                                <span>Pause listing</span>
                              </button>
                            )}
                            {row.status === "paused" && (
                              <button
                                type="button"
                                onClick={() => {
                                  setActiveMenuId(null);
                                  onPauseResume?.(row);
                                }}
                                className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-[#F1F2F6] text-start"
                              >
                                <Play className="size-3.5 text-[#16A34A]" />
                                <span>Resume listing</span>
                              </button>
                            )}
                            <div className="my-1 border-t border-[#E3E5EC]" />
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                onDelete?.(row);
                              }}
                              className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-red-50 text-red-600 text-start"
                            >
                              <Trash2 className="size-3.5 text-red-500" />
                              <span>Delete</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Card List View (< 768px) */}
      <div className="md:hidden divide-y divide-[#E3E5EC]">
        {items.map((row) => (
          <div
            key={row.id}
            onClick={() => onRowClick?.(row)}
            className="p-4 flex flex-col gap-3 hover:bg-[#F8F9FC] transition-colors"
          >
            <div className="flex items-start gap-3">
              <div className="relative size-16 rounded-md overflow-hidden bg-[#F1F2F6] border border-[#E3E5EC] shrink-0">
                {row.thumbnailUrl ? (
                  <img src={row.thumbnailUrl} alt={row.title} className="w-full h-full object-cover" />
                ) : (
                  <div className="flex items-center justify-center w-full h-full text-[#A3A7B5] text-[10px]">
                    No photo
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-semibold text-[14px] text-[#111827] truncate">
                    {row.title || "Untitled Product"}
                  </h4>
                  {row.priceInr && (
                    <span className="font-bold text-[14px] text-[#4B3BD1]">
                      {inr(row.priceInr)}
                    </span>
                  )}
                </div>
                <p className="text-[12px] text-[#6B7080] truncate mt-0.5">
                  {row.categoryName} {row.code && `· ${row.code}`}
                </p>
                <div className="mt-2">
                  <StatusPill
                    status={row.status}
                    verificationStatus={row.verificationStatus}
                    quantityAvailable={row.quantityAvailable}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1">
              <Link
                href={row.status === "draft" ? `/sell/new/${row.id}` : `/sell/products/${row.id}`}
                className="flex-1 text-center py-2 rounded-md bg-[#4B3BD1] text-white text-[13px] font-semibold"
              >
                {row.status === "draft" ? "Continue draft" : "Edit product"}
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination Footer */}
      <div className="p-3.5 bg-white border-t border-[#E3E5EC] flex flex-col sm:flex-row items-center justify-between gap-3 text-[13px] text-[#6B7080]">
        <div className="flex items-center gap-2">
          <span>Rows per page:</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
            className="h-8 ps-2 pe-6 rounded border border-[#E3E5EC] bg-white text-[12.5px] text-[#111827] focus:outline-none"
          >
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>
        </div>

        <div className="flex items-center gap-4">
          <span>
            {startItem}–{endItem} of {totalCount}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => onPageChange?.(currentPage - 1)}
              className="p-1 rounded border border-[#E3E5EC] text-[#111827] hover:bg-[#F1F2F6] disabled:opacity-40 disabled:pointer-events-none"
              aria-label="Previous page"
            >
              <ChevronLeft className="size-4" />
            </button>
            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() => onPageChange?.(currentPage + 1)}
              className="p-1 rounded border border-[#E3E5EC] text-[#111827] hover:bg-[#F1F2F6] disabled:opacity-40 disabled:pointer-events-none"
              aria-label="Next page"
            >
              <ChevronRight className="size-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
