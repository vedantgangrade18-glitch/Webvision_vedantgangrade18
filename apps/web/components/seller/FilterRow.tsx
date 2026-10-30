"use client";

import { ChevronDown, Search, X } from "lucide-react";
import { cx } from "@/lib/format";

interface FilterRowProps {
  categories?: { id: string; name: string }[];
  crafts?: { id: string; name: string }[];
  selectedCategory?: string;
  selectedCraft?: string;
  onSelectCategory?: (val: string) => void;
  onSelectCraft?: (val: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  placeholder?: string;
  className?: string;
}

export function FilterRow({
  categories = [],
  crafts = [],
  selectedCategory = "",
  selectedCraft = "",
  onSelectCategory,
  onSelectCraft,
  searchQuery,
  onSearchChange,
  placeholder = "Search by product code...",
  className,
}: FilterRowProps) {
  return (
    <div
      className={cx(
        "flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 py-1",
        className
      )}
    >
      {/* Left Filters */}
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-[13px] font-medium text-[#6B7080] shrink-0">
          Filter by:
        </span>

        {/* Category dropdown */}
        <div className="relative">
          <select
            value={selectedCategory}
            onChange={(e) => onSelectCategory?.(e.target.value)}
            className="h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13px] text-[#111827] focus:outline-none focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
          >
            <option value="">Select category</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-3.5 text-[#6B7080]" />
        </div>

        {/* Craft dropdown */}
        <div className="relative">
          <select
            value={selectedCraft}
            onChange={(e) => onSelectCraft?.(e.target.value)}
            className="h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13px] text-[#111827] focus:outline-none focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
          >
            <option value="">Select craft</option>
            {crafts.map((cr) => (
              <option key={cr.id} value={cr.id}>
                {cr.name}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-3.5 text-[#6B7080]" />
        </div>
      </div>

      {/* Right Search Input with Magnifier */}
      <div className="relative w-full md:w-72 shrink-0">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
          className="w-full h-9 ps-3.5 pe-9 rounded-md border border-[#E3E5EC] bg-white text-[13px] text-[#111827] placeholder:text-[#A3A7B5] focus:outline-none focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
        />
        {searchQuery ? (
          <button
            type="button"
            onClick={() => onSearchChange("")}
            className="absolute end-2.5 top-1/2 -translate-y-1/2 text-[#A3A7B5] hover:text-[#111827]"
          >
            <X className="size-3.5" />
          </button>
        ) : (
          <Search className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#A3A7B5]" />
        )}
      </div>
    </div>
  );
}
