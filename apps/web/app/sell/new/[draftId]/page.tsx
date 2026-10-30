"use client";

import {
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  HelpCircle,
  Info,
  Mic,
  Plus,
  RefreshCw,
  Sparkles,
  Upload,
  Video,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ImageUploader } from "@/components/seller/ImageUploader";
import { PageHeader } from "@/components/seller/PageHeader";
import { PriceInventoryTable } from "@/components/seller/PriceInventoryTable";
import { ProductStrip, type ProductChipItem } from "@/components/seller/ProductStrip";
import { SettlementBox } from "@/components/seller/SettlementBox";
import { StickyFooter } from "@/components/seller/StickyFooter";
import { VoiceField } from "@/components/seller/VoiceField";
import { cx, inr } from "@/lib/format";

export default function AddProductStep2Page() {
  const router = useRouter();
  const params = useParams();
  const draftId = (params?.draftId as string) || "draft-101";

  // Products in strip
  const [products, setProducts] = useState<ProductChipItem[]>([
    {
      id: draftId,
      title: "Bhagalpuri Handwoven Tussar Silk Saree",
      thumbnailUrl:
        "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80",
    },
  ]);
  const [activeProductId, setActiveProductId] = useState<string>(draftId);
  const [copyToAll, setCopyToAll] = useState(true);

  // Form Fields (Pre-filled by Karu Multimodal AI engine)
  const [productName, setProductName] = useState("Bhagalpuri Handwoven Tussar Silk Saree");
  const [size, setSize] = useState("Free Size");
  const [netWeight, setNetWeight] = useState("450");
  const [sellerCode, setSellerCode] = useState("BH-TSR-01");

  // Price & Inventory Row
  const [priceRow, setPriceRow] = useState({
    size: "Free Size",
    priceInr: 2800 as number | "",
    mrpInr: 3200 as number | "",
    inventory: 4,
    returnable: true,
    shipsInDays: 2,
  });
  const [copyPriceToAll, setCopyPriceToAll] = useState(true);

  // Product Details (Category Schema Attributes)
  const [material, setMaterial] = useState("Pure Tussar Silk");
  const [technique, setTechnique] = useState("Handloom (Pit Loom)");
  const [dye, setDye] = useState("Natural Madder & Haldi Dye");
  const [colour, setColour] = useState("Maroon with Golden Sheen");
  const [length, setLength] = useState("5.5 meters (with 0.8m blouse)");
  const [timeToMake, setTimeToMake] = useState("12 days");
  const [care, setCare] = useState("Dry Clean Recommended");
  const [craft, setCraft] = useState("Bhagalpuri Handloom Silk");

  // Description & Story (3 Languages)
  const [descLang, setDescLang] = useState<"source" | "en" | "hi">("source");
  const [descriptionSource, setDescriptionSource] = useState(
    "Authentic Bhagalpuri Tussar silk saree handwoven by traditional master artisans. Features a rich natural textured golden sheen, hand-spun wild silkworm yarns, and a traditional contrasting border. Designed for elegance, breathability, and cultural heritage."
  );
  const [descriptionEn, setDescriptionEn] = useState(
    "Handloom Bhagalpuri Tussar silk saree featuring natural gold luster and hand-spun texture. Woven over 12 days on a wooden pit loom."
  );
  const [descriptionHi, setDescriptionHi] = useState(
    "पारंपरिक भागलपुरी टसर सिल्क साड़ी, जिसे 12 दिनों में हाथ के करघे पर बुना गया है। शुद्ध प्राकृतिक रंग और सुनहरी चमक।"
  );

  // Tags
  const [tags, setTags] = useState<string[]>([
    "handloom",
    "tussar-silk",
    "bhagalpur",
    "pit-loom",
    "natural-dye",
  ]);
  const [newTagInput, setNewTagInput] = useState("");

  // Making video state
  const [videoUploaded, setVideoUploaded] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Uploaded Photos
  const [photos, setPhotos] = useState<string[]>([
    "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1610030469668-93510cb67655?auto=format&fit=crop&w=400&q=80",
    "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?auto=format&fit=crop&w=400&q=80",
  ]);

  const handleAddPhotos = (files: File[]) => {
    // Generate object URLs for preview
    const newUrls = files.map((f) => URL.createObjectURL(f));
    setPhotos((prev) => [...prev, ...newUrls].slice(0, 6));
  };

  const handleRemovePhoto = (idx: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleChangeFrontPhoto = (file: File) => {
    const url = URL.createObjectURL(file);
    setPhotos((prev) => [url, ...prev.slice(1)]);
  };

  const handleUseVariant = (variant: { url: string }) => {
    setPhotos((prev) => (prev.length < 6 ? [...prev, variant.url] : prev));
  };

  const handleAddTag = () => {
    if (newTagInput.trim() && !tags.includes(newTagInput.trim())) {
      setTags([...tags, newTagInput.trim().toLowerCase()]);
      setNewTagInput("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const handleAddProductChip = () => {
    const newId = `draft-${Date.now().toString().slice(-4)}`;
    setProducts((prev) => [
      ...prev,
      {
        id: newId,
        title: "Product " + (prev.length + 1),
      },
    ]);
    setActiveProductId(newId);
  };

  const handleSaveBack = () => {
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      router.push("/sell/products?status=draft");
    }, 600);
  };

  const handleSubmit = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      router.push(`/sell/new/${draftId}/done`);
    }, 1000);
  };

  const handleDiscard = () => {
    router.push("/sell/products");
  };

  return (
    <div className="flex flex-col min-h-dvh bg-[#F1F2F6]">
      {/* 56px White PageHeader */}
      <PageHeader
        title="Add Single Catalog"
        backHref="/sell/new"
        howToText="How to review & submit product"
      />

      {/* Stepper Bar */}
      <div className="bg-white border-b border-[#E3E5EC] px-6 py-2.5 flex items-center justify-center">
        <div className="flex items-center gap-8 max-w-lg w-full text-[13px] font-semibold">
          {/* Step 1 Done */}
          <Link
            href="/sell/new"
            className="flex items-center gap-2 text-[#16A34A] pb-1 hover:underline"
          >
            <span className="size-5 rounded-full bg-[#16A34A] text-white flex items-center justify-center text-[11px] font-bold">
              ✓
            </span>
            <span>Select Category</span>
          </Link>

          <div className="h-0.5 flex-1 bg-[#4B3BD1]" />

          {/* Step 2 Active */}
          <div className="flex items-center gap-2 text-[#4B3BD1] pb-1 border-b-2 border-[#4B3BD1]">
            <span className="size-5 rounded-full bg-[#4B3BD1] text-white flex items-center justify-center text-[11px] font-bold">
              2
            </span>
            <span>Add Product Details</span>
          </div>
        </div>
      </div>

      {/* Product Strip at top with Add Product button */}
      <ProductStrip
        products={products}
        activeId={activeProductId}
        onSelectProduct={setActiveProductId}
        onAddProduct={handleAddProductChip}
        copyToAll={copyToAll}
        onToggleCopyToAll={setCopyToAll}
      />

      {/* Main Two-Column Layout: Form (flex 1) + Sticky Right Column (340px) */}
      <div className="max-w-[1240px] w-full mx-auto px-4 sm:px-6 py-5 flex-1 flex flex-col lg:flex-row items-start gap-5">
        {/* LEFT COLUMN: Main Form Card */}
        <div className="flex-1 w-full bg-white rounded-lg border border-[#E3E5EC] p-5 sm:p-6 shadow-xs flex flex-col gap-6">
          {/* Header */}
          <div className="flex flex-col gap-1 border-b border-[#E3E5EC] pb-4">
            <h2 className="text-[18px] font-bold text-[#111827]">
              Add Product Details
            </h2>
            <p className="text-[12.5px] text-[#6B7080]">
              To change a field for one piece only, select it in the top product strip above.
            </p>
          </div>

          {/* AI Prefill Highlight Banner */}
          <div className="p-3.5 rounded-lg border border-[#EFEDFC] bg-[#F8F7FD] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5">
            <div className="flex items-center gap-2 text-[#4B3BD1]">
              <Sparkles className="size-4 shrink-0" />
              <span className="text-[13px] font-semibold">
                ✨ Filled by Meesho from your photos and voice. Please review each field.
              </span>
            </div>
            <button
              type="button"
              onClick={() => {}}
              className="px-3 py-1 rounded bg-white border border-[#4B3BD1]/30 hover:bg-[#EFEDFC] text-[#4B3BD1] text-[12px] font-semibold transition-colors flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className="size-3" />
              <span>Regenerate all</span>
            </button>
          </div>

          {/* SECTION 1: Product, size and inventory */}
          <section className="flex flex-col gap-4">
            <h3 className="text-[15px] font-bold text-[#111827] flex items-center gap-2">
              <span>Product, size and inventory</span>
            </h3>

            {/* Form grid: 2 columns on lg */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Product name */}
              <VoiceField
                id="product-name"
                label="Product Name"
                required
                tooltip="Clear descriptive title including craft and material"
                value={productName}
                onChange={setProductName}
                filledByKaru
              />

              {/* Size Select */}
              <div className="flex flex-col gap-1">
                <label className="text-[13px] font-medium text-[#111827] flex items-center gap-1">
                  <span>Size</span>
                  <span className="text-red-500 font-bold">*</span>
                  <span className="text-[#A3A7B5] cursor-help text-[11px]" title="Garment or piece dimensions">
                    ⓘ
                  </span>
                </label>
                <div className="relative">
                  <select
                    value={size}
                    onChange={(e) => setSize(e.target.value)}
                    className="w-full h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
                  >
                    <option value="Free Size">Free Size (Standard 5.5m)</option>
                    <option value="S">Small (S)</option>
                    <option value="M">Medium (M)</option>
                    <option value="L">Large (L)</option>
                    <option value="XL">Extra Large (XL)</option>
                    <option value="Custom">Custom Dimensions</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#6B7080]" />
                </div>
              </div>

              {/* Net weight (g) */}
              <div className="flex flex-col gap-1">
                <label className="text-[13px] font-medium text-[#111827] flex items-center gap-1">
                  <span>Net weight (gms)</span>
                  <span className="text-red-500 font-bold">*</span>
                  <span className="text-[#A3A7B5] cursor-help text-[11px]" title="Weight for shipping calculations">
                    ⓘ
                  </span>
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={netWeight}
                    onChange={(e) => setNetWeight(e.target.value)}
                    className="w-full h-9 ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
                  />
                  <span className="absolute end-3 top-1/2 -translate-y-1/2 text-[12px] text-[#6B7080]">
                    g
                  </span>
                </div>
              </div>

              {/* Seller Product code */}
              <div className="flex flex-col gap-1">
                <label className="text-[13px] font-medium text-[#111827] flex items-center gap-1">
                  <span>Style code / Product ID</span>
                  <span className="text-[11px] text-[#6B7080] font-normal">(optional)</span>
                  <span className="text-[#A3A7B5] cursor-help text-[11px]" title="Your internal workshop reference number">
                    ⓘ
                  </span>
                </label>
                <input
                  type="text"
                  value={sellerCode}
                  onChange={(e) => setSellerCode(e.target.value)}
                  placeholder="e.g. LOT-42"
                  className="w-full h-9 px-3 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1] focus:ring-1 focus:ring-[#4B3BD1]"
                />
              </div>
            </div>

            {/* Horizontally scrolling Price/Inventory Table */}
            <div className="mt-2">
              <PriceInventoryTable
                row={priceRow}
                onChange={(updated) => setPriceRow((prev) => ({ ...prev, ...updated }))}
                copyPriceToAllSizes={copyPriceToAll}
                onToggleCopyPrice={setCopyPriceToAll}
                benchmarkMin={2600}
                benchmarkMax={3400}
                recommendedPrice={2800}
              />
            </div>
          </section>

          <div className="border-t border-[#E3E5EC]" />

          {/* SECTION 2: Product Details (Category Attributes) */}
          <section className="flex flex-col gap-4">
            <h3 className="text-[15px] font-bold text-[#111827]">
              Product Details & Craft Specifications
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[13px]">
              {/* Material */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Material *</label>
                <div className="relative">
                  <select
                    value={material}
                    onChange={(e) => setMaterial(e.target.value)}
                    className="w-full h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                  >
                    <option value="Pure Tussar Silk">Pure Tussar Silk</option>
                    <option value="Mulberry Silk">Mulberry Silk</option>
                    <option value="Cotton-Silk Blend">Cotton-Silk Blend</option>
                    <option value="Khadi Cotton">Handspun Khadi Cotton</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#6B7080]" />
                </div>
              </div>

              {/* Technique */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Technique *</label>
                <div className="relative">
                  <select
                    value={technique}
                    onChange={(e) => setTechnique(e.target.value)}
                    className="w-full h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                  >
                    <option value="Handloom (Pit Loom)">Handloom (Pit Loom)</option>
                    <option value="Throw Shuttle Loom">Throw Shuttle Loom</option>
                    <option value="Jacquard Handloom">Jacquard Handloom</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#6B7080]" />
                </div>
              </div>

              {/* Dye */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Dye Process</label>
                <div className="relative">
                  <select
                    value={dye}
                    onChange={(e) => setDye(e.target.value)}
                    className="w-full h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                  >
                    <option value="Natural Madder & Haldi Dye">Natural Madder & Haldi Dye</option>
                    <option value="Fermented Indigo">Fermented Indigo</option>
                    <option value="Azo-Free Low Impact">Azo-Free Low Impact Dye</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#6B7080]" />
                </div>
              </div>

              {/* Colour */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Colour *</label>
                <div className="relative">
                  <select
                    value={colour}
                    onChange={(e) => setColour(e.target.value)}
                    className="w-full h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                  >
                    <option value="Maroon with Golden Sheen">Maroon with Golden Sheen</option>
                    <option value="Deep Indigo">Deep Indigo</option>
                    <option value="Peacock Green">Peacock Green</option>
                    <option value="Mustard Haldi">Mustard Haldi</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#6B7080]" />
                </div>
              </div>

              {/* Length */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Length / Dimensions</label>
                <input
                  type="text"
                  value={length}
                  onChange={(e) => setLength(e.target.value)}
                  className="h-9 px-3 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                />
              </div>

              {/* Time to make */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Time to Weave / Make</label>
                <input
                  type="text"
                  value={timeToMake}
                  onChange={(e) => setTimeToMake(e.target.value)}
                  className="h-9 px-3 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                />
              </div>

              {/* Care Instructions */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Care</label>
                <div className="relative">
                  <select
                    value={care}
                    onChange={(e) => setCare(e.target.value)}
                    className="w-full h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                  >
                    <option value="Dry Clean Recommended">Dry Clean Recommended</option>
                    <option value="Gentle Cold Handwash">Gentle Cold Handwash</option>
                    <option value="Spot Clean Only">Spot Clean Only</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#6B7080]" />
                </div>
              </div>

              {/* Craft Heritage */}
              <div className="flex flex-col gap-1">
                <label className="font-medium text-[#111827]">Craft Heritage *</label>
                <div className="relative">
                  <select
                    value={craft}
                    onChange={(e) => setCraft(e.target.value)}
                    className="w-full h-9 appearance-none ps-3 pe-8 rounded-md border border-[#E3E5EC] bg-white text-[13.5px] text-[#111827] focus:outline-none focus:border-[#4B3BD1]"
                  >
                    <option value="Bhagalpuri Handloom Silk">Bhagalpuri Handloom Silk</option>
                    <option value="Banarasi Kadhwa Brocade">Banarasi Kadhwa Brocade</option>
                    <option value="Chanderi Handloom">Chanderi Handloom</option>
                  </select>
                  <ChevronDown className="pointer-events-none absolute end-2.5 top-1/2 -translate-y-1/2 size-4 text-[#6B7080]" />
                </div>
              </div>
            </div>
          </section>

          <div className="border-t border-[#E3E5EC]" />

          {/* SECTION 3: Description and Story */}
          <section className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h3 className="text-[15px] font-bold text-[#111827]">
                Description & Craft Story
              </h3>

              {/* Language Tabs */}
              <div className="flex items-center gap-1 bg-[#F1F2F6] p-1 rounded-md text-[12px] font-semibold">
                <button
                  type="button"
                  onClick={() => setDescLang("source")}
                  className={cx(
                    "px-2.5 py-1 rounded transition-colors",
                    descLang === "source" ? "bg-white text-[#4B3BD1] shadow-2xs" : "text-[#6B7080]"
                  )}
                >
                  Your Language
                </button>
                <button
                  type="button"
                  onClick={() => setDescLang("en")}
                  className={cx(
                    "px-2.5 py-1 rounded transition-colors",
                    descLang === "en" ? "bg-white text-[#4B3BD1] shadow-2xs" : "text-[#6B7080]"
                  )}
                >
                  English
                </button>
                <button
                  type="button"
                  onClick={() => setDescLang("hi")}
                  className={cx(
                    "px-2.5 py-1 rounded transition-colors",
                    descLang === "hi" ? "bg-white text-[#4B3BD1] shadow-2xs" : "text-[#6B7080]"
                  )}
                >
                  हिन्दी
                </button>
              </div>
            </div>

            {/* VoiceField Textarea */}
            {descLang === "source" && (
              <VoiceField
                value={descriptionSource}
                onChange={setDescriptionSource}
                type="textarea"
                rows={4}
                maxChars={2000}
                filledByKaru
              />
            )}
            {descLang === "en" && (
              <VoiceField
                value={descriptionEn}
                onChange={setDescriptionEn}
                type="textarea"
                rows={4}
                maxChars={2000}
                filledByKaru
              />
            )}
            {descLang === "hi" && (
              <VoiceField
                value={descriptionHi}
                onChange={setDescriptionHi}
                type="textarea"
                rows={4}
                maxChars={2000}
                filledByKaru
              />
            )}

            {/* Tags Input */}
            <div className="flex flex-col gap-1.5 pt-1">
              <label className="text-[12.5px] font-medium text-[#6B7080]">
                Tags ({tags.length}/10)
              </label>
              <div className="flex flex-wrap items-center gap-2 p-2 rounded-md border border-[#E3E5EC] bg-white min-h-10">
                {tags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#EFEDFC] text-[#4B3BD1] text-[12px] font-semibold"
                  >
                    <span>#{t}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveTag(t)}
                      className="hover:text-red-600"
                    >
                      <X className="size-3" />
                    </button>
                  </span>
                ))}

                <div className="flex items-center gap-1 ms-1">
                  <input
                    type="text"
                    value={newTagInput}
                    onChange={(e) => setNewTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddTag();
                      }
                    }}
                    placeholder="+ add tag"
                    className="h-7 px-2 text-[12px] border-none focus:outline-none text-[#111827] placeholder:text-[#A3A7B5]"
                  />
                  {newTagInput && (
                    <button
                      type="button"
                      onClick={handleAddTag}
                      className="text-[11px] font-bold text-[#4B3BD1] uppercase"
                    >
                      Add
                    </button>
                  )}
                </div>
              </div>
            </div>
          </section>

          <div className="border-t border-[#E3E5EC]" />

          {/* SECTION 4: Returns and Verification */}
          <section className="flex flex-col gap-4">
            <h3 className="text-[15px] font-bold text-[#111827]">
              Returns & Authenticity Verification
            </h3>

            {/* Making Video Upload / Record */}
            <div className="p-4 rounded-lg border border-[#E3E5EC] bg-[#F8F9FC] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="size-11 rounded-full bg-[#EFEDFC] flex items-center justify-center text-[#4B3BD1] shrink-0">
                  <Video className="size-5" />
                </div>
                <div>
                  <h4 className="font-semibold text-[13.5px] text-[#111827]">
                    Product Video (Optional · Get Quality Verified)
                  </h4>
                  <p className="text-[12px] text-[#6B7080]">
                    Upload 30s–3 min video of you working on the loom/wheel to earn the verified badge.
                  </p>
                </div>
              </div>

              <label className="cursor-pointer px-4 py-2 rounded-md bg-white border border-[#4B3BD1] text-[#4B3BD1] hover:bg-[#EFEDFC] text-[12.5px] font-semibold transition-colors shrink-0 shadow-2xs">
                <span>{videoUploaded ? "✓ Video Attached" : "Upload Video"}</span>
                <input
                  type="file"
                  accept="video/*"
                  onChange={() => setVideoUploaded(true)}
                  className="hidden"
                />
              </label>
            </div>

            {/* Tiny Legal Text */}
            <p className="text-[11px] text-[#7C8196] leading-relaxed">
              By submitting, you confirm this product is genuine, specifications are accurate, and you agree to Meesho&apos;s supplier terms. Verified products receive higher discoverability and buyer trust.
            </p>
          </section>
        </div>

        {/* RIGHT COLUMN: Sticky Side Panel (340px) */}
        <div className="w-full lg:w-[340px] shrink-0 flex flex-col gap-5 sticky top-20">
          {/* Photos Manager */}
          <ImageUploader
            photos={photos}
            onAddPhotos={handleAddPhotos}
            onRemovePhoto={handleRemovePhoto}
            onChangeFrontPhoto={handleChangeFrontPhoto}
            onUseVariant={handleUseVariant}
          />

          {/* Settlement / Earnings Box */}
          <SettlementBox
            priceInr={priceRow.priceInr}
            mrpInr={priceRow.mrpInr}
            title={productName}
            thumbnailUrl={photos[0]}
            artisanName="Master Artisan"
          />
        </div>
      </div>

      {/* Sticky Footer Action Bar */}
      <StickyFooter
        onDiscard={handleDiscard}
        onSaveBack={handleSaveBack}
        onSubmit={handleSubmit}
        discardText="Discard Catalog"
        saveBackText="Save and go back"
        submitText="Submit Catalog"
        isSaving={isSaving}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
