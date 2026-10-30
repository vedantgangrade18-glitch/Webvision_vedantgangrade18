"use client";

import { Check, ChevronRight, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { CategoryColumns, type CategoryNode } from "@/components/seller/CategoryColumns";
import { PageHeader } from "@/components/seller/PageHeader";
import { StickyFooter } from "@/components/seller/StickyFooter";

const CATEGORIES_TREE: CategoryNode[] = [
  {
    id: "clothing",
    name: "Clothing & Textiles",
    children: [
      {
        id: "sarees",
        name: "Sarees",
        children: [
          {
            id: "silk-sarees",
            name: "Silk Sarees",
            children: [
              { id: "banarasi", name: "Banarasi Silk", isLeaf: true },
              { id: "bhagalpuri", name: "Bhagalpuri Tussar", isLeaf: true },
              { id: "kanjivaram", name: "Kanjivaram Silk", isLeaf: true },
              { id: "chanderi", name: "Chanderi Silk-Cotton", isLeaf: true },
            ],
          },
          {
            id: "cotton-sarees",
            name: "Cotton Sarees",
            children: [
              { id: "kota-doria", name: "Kota Doria", isLeaf: true },
              { id: "sambalpuri", name: "Sambalpuri Ikat", isLeaf: true },
              { id: "jamdani", name: "Jamdani Muslin", isLeaf: true },
            ],
          },
        ],
      },
      {
        id: "shawls",
        name: "Shawls & Stoles",
        children: [
          {
            id: "pashmina",
            name: "Pashmina",
            children: [
              { id: "sozni", name: "Sozni Embroidered", isLeaf: true },
              { id: "kani", name: "Kani Woven", isLeaf: true },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "home-living",
    name: "Home & Living",
    children: [
      {
        id: "pottery",
        name: "Pottery & Ceramics",
        children: [
          {
            id: "blue-pottery",
            name: "Jaipur Blue Pottery",
            children: [
              { id: "serving-bowls", name: "Bowls & Platters", isLeaf: true },
              { id: "ceramic-vases", name: "Vases & Urns", isLeaf: true },
            ],
          },
          {
            id: "terracotta",
            name: "Terracotta Clay",
            children: [
              { id: "clay-cookware", name: "Handi & Cookware", isLeaf: true },
              { id: "terracotta-pots", name: "Planters & Pots", isLeaf: true },
            ],
          },
        ],
      },
      {
        id: "carpets-rugs",
        name: "Carpets & Dhurries",
        children: [
          {
            id: "dhurries",
            name: "Panipat Cotton Dhurries",
            children: [
              { id: "geometric-rugs", name: "Geometric Floor Rugs", isLeaf: true },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "art-paintings",
    name: "Art & Paintings",
    children: [
      {
        id: "folk-art",
        name: "Traditional Folk Art",
        children: [
          {
            id: "madhubani",
            name: "Madhubani Paintings",
            children: [
              { id: "kachni", name: "Kachni Line Art", isLeaf: true },
              { id: "bharni", name: "Bharni Color Art", isLeaf: true },
            ],
          },
          {
            id: "rogan-art",
            name: "Kutch Rogan Art",
            children: [
              { id: "tree-of-life", name: "Tree of Life Wall Hanging", isLeaf: true },
            ],
          },
        ],
      },
    ],
  },
  {
    id: "jewellery",
    name: "Handcrafted Jewellery",
    children: [
      {
        id: "silver-craft",
        name: "Tribal Silver & Filigree",
        children: [
          {
            id: "tarakasi",
            name: "Cuttack Tarakasi Filigree",
            children: [
              { id: "silver-earrings", name: "Filigree Earrings", isLeaf: true },
            ],
          },
        ],
      },
    ],
  },
];

export default function AddProductStep1Page() {
  const router = useRouter();

  const [selectedLeafPath, setSelectedLeafPath] = useState<CategoryNode[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>("bhagalpuri");
  const [uploadedPhotos, setUploadedPhotos] = useState<File[]>([]);
  const [voiceNote, setVoiceNote] = useState<{ blob: Blob; transcript: string; duration: number } | null>(null);

  const handlePhotosSelected = (files: File[]) => {
    setUploadedPhotos((prev) => [...prev, ...files].slice(0, 6));
  };

  const handleContinue = () => {
    // Generate draft ID and navigate to Step 2
    const draftId = `draft-${Date.now().toString().slice(-4)}`;
    router.push(`/sell/new/${draftId}`);
  };

  const handleDiscard = () => {
    router.push("/sell/products");
  };

  return (
    <div className="flex flex-col min-h-dvh bg-[#F1F2F6]">
      {/* 56px PageHeader */}
      <PageHeader
        title="Add Single Catalog"
        backHref="/sell/products"
        howToText="How to select category & photos"
      />

      {/* Stepper Bar matching R2 & R3 */}
      <div className="bg-white border-b border-[#E3E5EC] px-6 py-2.5 flex items-center justify-center">
        <div className="flex items-center gap-8 max-w-lg w-full text-[13px] font-semibold">
          {/* Step 1 */}
          <div className="flex items-center gap-2 text-[#4B3BD1] pb-1 border-b-2 border-[#4B3BD1]">
            <span className="size-5 rounded-full bg-[#4B3BD1] text-white flex items-center justify-center text-[11px] font-bold">
              1
            </span>
            <span>Select Category</span>
          </div>

          <div className="h-0.5 flex-1 bg-[#E3E5EC]" />

          {/* Step 2 */}
          <div className="flex items-center gap-2 text-[#7C8196] pb-1">
            <span className="size-5 rounded-full border border-[#7C8196] text-[#7C8196] flex items-center justify-center text-[11px]">
              2
            </span>
            <span>Add Product Details</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-[1240px] w-full mx-auto px-4 sm:px-6 py-5 flex-1 flex flex-col">
        <CategoryColumns
          categories={CATEGORIES_TREE}
          onSelectLeaf={(path, id) => {
            setSelectedLeafPath(path);
            setSelectedCategoryId(id);
          }}
          onPhotosSelected={handlePhotosSelected}
          onVoiceRecorded={(blob, transcript, duration) => {
            setVoiceNote({ blob, transcript, duration });
          }}
          onContinue={handleContinue}
          uploadedPhotosCount={uploadedPhotos.length}
        />
      </div>

      {/* Sticky Footer */}
      <StickyFooter
        onDiscard={handleDiscard}
        onSubmit={handleContinue}
        discardText="Discard Catalog"
        submitText="Continue to Details →"
      />
    </div>
  );
}
