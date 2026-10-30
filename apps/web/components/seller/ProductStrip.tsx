"use client";

import { CheckSquare, Plus, Square } from "lucide-react";
import { cx } from "@/lib/format";

export interface ProductChipItem {
  id: string;
  title: string;
  thumbnailUrl?: string;
  hasErrors?: boolean;
}

interface ProductStripProps {
  products: ProductChipItem[];
  activeId: string;
  onSelectProduct: (id: string) => void;
  onAddProduct: () => void;
  copyToAll: boolean;
  onToggleCopyToAll: (val: boolean) => void;
  className?: string;
}

export function ProductStrip({
  products,
  activeId,
  onSelectProduct,
  onAddProduct,
  copyToAll,
  onToggleCopyToAll,
  className,
}: ProductStripProps) {
  return (
    <div className={cx("bg-white border-b border-[#E3E5EC] px-4 py-3 flex flex-col gap-2.5", className)}>
      <div className="flex items-center justify-between gap-4">
        {/* Horizontal scroll of products */}
        <div className="flex items-center gap-3 overflow-x-auto pb-1 no-scrollbar">
          {products.map((p, idx) => {
            const isActive = p.id === activeId;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => onSelectProduct(p.id)}
                className={cx(
                  "flex items-center gap-2 px-3 py-1.5 rounded-md border text-[13px] font-medium transition-all relative shrink-0",
                  isActive
                    ? "border-[#4B3BD1] bg-[#EFEDFC] text-[#4B3BD1] font-semibold ring-1 ring-[#4B3BD1]/30"
                    : "border-[#E3E5EC] bg-white text-[#111827] hover:bg-[#F1F2F6]"
                )}
              >
                <div className="size-6 rounded overflow-hidden bg-gray-100 shrink-0">
                  {p.thumbnailUrl ? (
                    <img src={p.thumbnailUrl} alt={p.title} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[10px] text-gray-400">
                      #{idx + 1}
                    </div>
                  )}
                </div>
                <span>Product {idx + 1}</span>
                {p.hasErrors && <span className="size-1.5 rounded-full bg-red-500" />}
              </button>
            );
          })}

          {/* Add Product Button */}
          <button
            type="button"
            onClick={onAddProduct}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-dashed border-[#4B3BD1] text-[#4B3BD1] hover:bg-[#EFEDFC] text-[13px] font-medium transition-colors shrink-0"
          >
            <Plus className="size-3.5" />
            <span>Add Product</span>
          </button>
        </div>

        {/* Copy input details to all products checkbox */}
        <div className="hidden md:flex items-center gap-2 shrink-0">
          <label className="flex items-center gap-2 cursor-pointer text-[12.5px] text-[#6B7080] hover:text-[#111827] select-none">
            <input
              type="checkbox"
              checked={copyToAll}
              onChange={(e) => onToggleCopyToAll(e.target.checked)}
              className="size-4 rounded border-[#E3E5EC] text-[#4B3BD1] focus:ring-[#4B3BD1]"
            />
            <span>Copy input details to all products</span>
          </label>
        </div>
      </div>
    </div>
  );
}
