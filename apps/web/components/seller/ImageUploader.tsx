"use client";

import { Check, Image as ImageIcon, Plus, Sparkles, Trash2, Upload, X } from "lucide-react";
import { useState } from "react";
import { cx } from "@/lib/format";

export interface PhotoVariant {
  id: string;
  url: string;
  label: string;
  ratio: string;
}

interface ImageUploaderProps {
  photos: string[];
  onAddPhotos: (files: File[]) => void;
  onRemovePhoto: (index: number) => void;
  onChangeFrontPhoto: (file: File) => void;
  aiVariants?: PhotoVariant[];
  onUseVariant?: (variant: PhotoVariant) => void;
  onDismissVariant?: (id: string) => void;
  isAiGenerating?: boolean;
  className?: string;
}

export function ImageUploader({
  photos,
  onAddPhotos,
  onRemovePhoto,
  onChangeFrontPhoto,
  aiVariants = [
    {
      id: "v1",
      url: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80",
      label: "Clean 4:5 Crop",
      ratio: "4:5",
    },
    {
      id: "v2",
      url: "https://images.unsplash.com/photo-1610030469668-93510cb67655?auto=format&fit=crop&w=400&q=80",
      label: "1:1 Square Detail",
      ratio: "1:1",
    },
    {
      id: "v3",
      url: "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=400&q=80",
      label: "Fabric Weave Macro",
      ratio: "4:5",
    },
  ],
  onUseVariant,
  onDismissVariant,
  isAiGenerating = false,
  className,
}: ImageUploaderProps) {
  const [activeVariants, setActiveVariants] = useState<PhotoVariant[]>(aiVariants);

  const handleDismiss = (id: string) => {
    setActiveVariants((prev) => prev.filter((v) => v.id !== id));
    onDismissVariant?.(id);
  };

  const handleUse = (v: PhotoVariant) => {
    onUseVariant?.(v);
  };

  return (
    <div className={cx("flex flex-col gap-4", className)}>
      {/* Yellow QC Guidelines Box */}
      <div className="p-3.5 rounded-lg border border-[#F3DFA0] bg-[#FFF7DD] text-[#744210] text-[12px] flex flex-col gap-1.5 shadow-2xs">
        <div className="flex items-center justify-between font-semibold text-[12.5px]">
          <span>Follow guidelines to pass quality check</span>
          <button type="button" className="text-[#4B3BD1] underline font-medium">
            View all
          </button>
        </div>
        <ol className="list-decimal list-inside space-y-0.5 text-[#5C554D] text-[11.5px]">
          <li>Images with text / watermarks are not acceptable.</li>
          <li>Product images should feature the craft clearly.</li>
          <li>Provide a clean front photo without props.</li>
        </ol>
      </div>

      {/* Recommended Shots Breakdown */}
      <div className="p-3 rounded-lg border border-[#E3E5EC] bg-white text-[12px] flex flex-col gap-2">
        <span className="font-semibold text-[#111827]">Add photos showing:</span>
        <div className="grid grid-cols-3 gap-2 text-center text-[11px] text-[#6B7080]">
          <div className="p-2 rounded bg-[#F8F9FC] border border-[#E3E5EC] flex flex-col items-center gap-1">
            <span className="font-medium text-[#111827]">Front</span>
            <span className="text-[#4B3BD1] font-semibold">● Required</span>
          </div>
          <div className="p-2 rounded bg-[#F8F9FC] border border-[#E3E5EC] flex flex-col items-center gap-1">
            <span className="font-medium text-[#111827]">Detail</span>
            <span className="text-[#16A34A]">Close-up</span>
          </div>
          <div className="p-2 rounded bg-[#F8F9FC] border border-[#E3E5EC] flex flex-col items-center gap-1">
            <span className="font-medium text-[#111827]">Making</span>
            <span className="text-[#D97706]">On loom</span>
          </div>
        </div>
      </div>

      {/* Uploaded Images Grid (72x90 px tiles) */}
      <div className="p-4 rounded-lg border border-[#E3E5EC] bg-white flex flex-col gap-3 shadow-xs">
        <span className="font-semibold text-[13px] text-[#111827]">
          Uploaded Images ({photos.length}/6)
        </span>

        <div className="flex flex-wrap gap-2.5">
          {photos.map((url, idx) => {
            const isFront = idx === 0;
            return (
              <div key={idx} className="flex flex-col items-center gap-1">
                <div className="relative w-[72px] h-[90px] rounded-md overflow-hidden border border-[#E3E5EC] bg-gray-50 group">
                  <img src={url} alt={`Upload ${idx + 1}`} className="w-full h-full object-cover" />
                  {!isFront && (
                    <button
                      type="button"
                      onClick={() => onRemovePhoto(idx)}
                      className="absolute top-1 end-1 p-0.5 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="size-3" />
                    </button>
                  )}
                  {isFront && (
                    <span className="absolute bottom-0 inset-x-0 bg-[#4B3BD1]/90 text-white text-[9px] font-bold text-center py-0.5 uppercase tracking-wider">
                      Front
                    </span>
                  )}
                </div>

                {isFront ? (
                  <label className="text-[11px] font-semibold text-[#4B3BD1] hover:underline cursor-pointer">
                    <span>CHANGE</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        if (e.target.files?.[0]) onChangeFrontPhoto(e.target.files[0]);
                      }}
                      className="hidden"
                    />
                  </label>
                ) : (
                  <span className="text-[10px] text-[#6B7080]">Image {idx + 1}</span>
                )}
              </div>
            );
          })}

          {/* + Add Images Tile */}
          {photos.length < 6 && (
            <label className="w-[72px] h-[90px] rounded-md border-2 border-dashed border-[#4B3BD1]/40 hover:border-[#4B3BD1] bg-[#EFEDFC]/30 hover:bg-[#EFEDFC]/70 cursor-pointer flex flex-col items-center justify-center text-[#4B3BD1] transition-colors">
              <Plus className="size-5" />
              <span className="text-[10.5px] font-semibold mt-1">Add</span>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={(e) => {
                  if (e.target.files) onAddPhotos(Array.from(e.target.files));
                }}
                className="hidden"
              />
            </label>
          )}
        </div>
      </div>

      {/* AI Enhanced Variants ("✨ Made by Meesho from your photo") */}
      <div className="p-3.5 rounded-lg border border-[#EFEDFC] bg-[#F8F7FD] flex flex-col gap-2.5">
        <div className="flex items-center gap-1.5 text-[12.5px] font-semibold text-[#4B3BD1]">
          <Sparkles className="size-4" />
          <span>✨ Enhanced by Meesho from your photo</span>
        </div>

        <p className="text-[11px] text-[#5C554D] leading-tight">
          One photo uploaded! Meesho cleaned the background and prepared verified multi-angle views.
        </p>

        {isAiGenerating ? (
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="w-[72px] h-[90px] rounded bg-gray-200 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {activeVariants.map((v) => (
              <div key={v.id} className="relative w-[72px] h-[90px] rounded-md overflow-hidden border border-[#E3E5EC] group bg-white shadow-2xs">
                <img src={v.url} alt={v.label} className="w-full h-full object-cover" />
                <div className="absolute inset-x-0 bottom-0 bg-black/75 p-1 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => handleUse(v)}
                    className="text-[9.5px] text-emerald-400 font-bold hover:underline"
                  >
                    + Use
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDismiss(v.id)}
                    className="text-[9.5px] text-gray-300 hover:text-white"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
