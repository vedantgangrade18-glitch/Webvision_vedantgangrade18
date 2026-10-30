"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { FilterRow } from "@/components/seller/FilterRow";
import { PageHeader } from "@/components/seller/PageHeader";
import { PromoBanner } from "@/components/seller/PromoBanner";
import { StatTile } from "@/components/seller/StatTile";
import { InfoStrip, SubTabs, UnderlineTabs, type TabItem } from "@/components/seller/Tabs";
import { ProductsDataTable, type ProductRowItem } from "@/components/seller/DataTable";
import { api } from "@/lib/api";

const MOCK_PRODUCTS: ProductRowItem[] = [
  {
    id: "p-001",
    code: "KA-SLK-481",
    title: "Bhagalpuri Handwoven Tussar Silk Saree",
    categoryName: "Silk Sarees",
    parentCategory: "Clothing › Sarees",
    thumbnailUrl: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=300&q=80",
    createdAt: "30 Oct 2026, 11:20 AM",
    quantityTotal: 5,
    quantityAvailable: 4,
    priceInr: 2800,
    pricePosition: "in_range",
    status: "published",
    verificationStatus: "verified",
  },
  {
    id: "p-002",
    code: "KA-POT-112",
    title: "Jaipur Blue Pottery Floral Fruit Bowl",
    categoryName: "Blue Pottery",
    parentCategory: "Home & Living › Pottery",
    thumbnailUrl: "https://images.unsplash.com/photo-1610701596007-11502861dcfa?auto=format&fit=crop&w=300&q=80",
    createdAt: "29 Oct 2026, 04:45 PM",
    quantityTotal: 12,
    quantityAvailable: 9,
    priceInr: 1250,
    pricePosition: "in_range",
    status: "published",
    verificationStatus: "verified",
  },
  {
    id: "p-003",
    code: "KA-BDR-098",
    title: "Bidriware Silver Inlay Keepsake Box",
    categoryName: "Metal Craft",
    parentCategory: "Home & Living › Decor",
    thumbnailUrl: "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=300&q=80",
    createdAt: "28 Oct 2026, 06:15 PM",
    quantityTotal: 3,
    quantityAvailable: 0,
    priceInr: 3600,
    pricePosition: "above",
    status: "action_needed",
    verificationStatus: "verified",
  },
  {
    id: "p-004",
    code: "KA-SHW-204",
    title: "Kashmiri Hand-Embroidered Sozni Pashmina",
    categoryName: "Shawls",
    parentCategory: "Clothing › Shawls",
    thumbnailUrl: "https://images.unsplash.com/photo-1607344645866-009c320c5ab8?auto=format&fit=crop&w=300&q=80",
    createdAt: "26 Oct 2026, 02:10 PM",
    quantityTotal: 2,
    quantityAvailable: 2,
    priceInr: 9500,
    pricePosition: "in_range",
    status: "processing",
    verificationStatus: "checking",
  },
  {
    id: "p-005",
    code: "KA-RGN-552",
    title: "Kutch Rogan Painted Silk Wall Hanging",
    categoryName: "Textile Art",
    parentCategory: "Art & Paintings",
    thumbnailUrl: "https://images.unsplash.com/photo-1582562124811-c09040d0a901?auto=format&fit=crop&w=300&q=80",
    createdAt: "24 Oct 2026, 09:30 AM",
    quantityTotal: 4,
    quantityAvailable: 4,
    priceInr: 4200,
    pricePosition: "in_range",
    status: "published",
    verificationStatus: "not_verified",
  },
  {
    id: "p-006",
    code: "",
    title: "Channapatna Lacquer Wood Stacking Toy Set",
    categoryName: "Wooden Toys",
    parentCategory: "Toys & Games",
    thumbnailUrl: "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?auto=format&fit=crop&w=300&q=80",
    createdAt: "22 Oct 2026, 01:12 PM",
    quantityTotal: 1,
    quantityAvailable: 1,
    priceInr: null,
    pricePosition: "unknown",
    status: "draft",
    verificationStatus: "none",
  },
];

export default function ProductsPage() {
  return (
    <Suspense>
      <ProductsView />
    </Suspense>
  );
}

function ProductsView() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Top tabs (Single Uploads vs Bulk Uploads like R1)
  const [topTab, setTopTab] = useState<string>("single");

  // Status Filter chip state
  const statusParam = searchParams.get("status") || "all";
  const [selectedStatus, setSelectedStatus] = useState<string>(statusParam);

  // Category and Search filters
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedCraft, setSelectedCraft] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Pagination
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);

  // Fetch listings from API (falls back to mock if needed)
  const { data: apiData } = useQuery({
    queryKey: ["seller-products-list"],
    queryFn: () =>
      api<{ items: any[] }>("/listings/mine").catch(() => ({
        items: [],
      })),
  });

  // Merge items
  const allProducts = useMemo(() => {
    if (apiData?.items && apiData.items.length > 0) {
      return apiData.items.map((it, idx) => ({
        id: it.id,
        code: it.short_code || it.code || "",
        title: it.title || "Untitled Product",
        categoryName: it.category?.name || "Handloom",
        parentCategory: it.category?.parent_name,
        thumbnailUrl: it.thumbnail_url || it.image?.url || MOCK_PRODUCTS[idx % MOCK_PRODUCTS.length].thumbnailUrl,
        createdAt: it.created_at || "Recent",
        quantityTotal: it.quantity_total || it.quantity || 1,
        quantityAvailable: it.quantity_available ?? it.quantity ?? 1,
        priceInr: it.price_inr,
        pricePosition: it.price_position || "in_range",
        status: it.status || "published",
        verificationStatus: it.verification_status || "verified",
      })) as ProductRowItem[];
    }
    return MOCK_PRODUCTS;
  }, [apiData]);

  // Counts by status
  const counts = useMemo(() => {
    return {
      all: allProducts.length,
      action_needed: allProducts.filter(
        (p) => p.status === "action_needed" || (p.status === "published" && p.quantityAvailable === 0)
      ).length,
      processing: allProducts.filter(
        (p) => p.status === "processing" || p.verificationStatus === "checking"
      ).length,
      not_verified: allProducts.filter(
        (p) => p.status === "published" && p.verificationStatus !== "verified"
      ).length,
      verified: allProducts.filter(
        (p) => p.status === "published" && p.verificationStatus === "verified"
      ).length,
      draft: allProducts.filter((p) => p.status === "draft").length,
      paused: allProducts.filter((p) => p.status === "paused").length,
      out_of_stock: allProducts.filter((p) => p.quantityAvailable === 0 && p.status === "published").length,
    };
  }, [allProducts]);

  // Filtered rows
  const filteredProducts = useMemo(() => {
    return allProducts.filter((p) => {
      // Search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = p.title.toLowerCase().includes(q);
        const matchCode = p.code.toLowerCase().includes(q);
        const matchCat = p.categoryName.toLowerCase().includes(q);
        if (!matchTitle && !matchCode && !matchCat) return false;
      }

      // Category
      if (selectedCategory && !p.categoryName.includes(selectedCategory)) {
        return false;
      }

      // Status chip
      if (selectedStatus === "all") return true;
      if (selectedStatus === "action_needed") {
        return p.status === "action_needed" || (p.status === "published" && p.quantityAvailable === 0);
      }
      if (selectedStatus === "processing") {
        return p.status === "processing" || p.verificationStatus === "checking";
      }
      if (selectedStatus === "not_verified") {
        return p.status === "published" && p.verificationStatus !== "verified";
      }
      if (selectedStatus === "verified") {
        return p.status === "published" && p.verificationStatus === "verified";
      }
      if (selectedStatus === "draft") return p.status === "draft";
      if (selectedStatus === "paused") return p.status === "paused";

      return true;
    });
  }, [allProducts, searchQuery, selectedCategory, selectedStatus]);

  const topTabsList: TabItem[] = [
    { id: "single", label: "Single Uploads", count: allProducts.length },
    { id: "bulk", label: "Bulk Uploads", count: 0 },
  ];

  const subTabsList: TabItem[] = [
    { id: "all", label: "All", count: counts.all },
    { id: "action_needed", label: "Action Needed", count: counts.action_needed },
    { id: "processing", label: "QC in Progress", count: counts.processing },
    { id: "not_verified", label: "Not Verified Yet", count: counts.not_verified },
    { id: "verified", label: "QC Pass / Live", count: counts.verified },
    { id: "draft", label: "Draft", count: counts.draft },
    { id: "paused", label: "Paused", count: counts.paused },
  ];

  const categoriesOptions = [
    { id: "Silk Sarees", name: "Silk Sarees" },
    { id: "Pottery", name: "Blue Pottery" },
    { id: "Metal Craft", name: "Bidriware Metal" },
    { id: "Shawls", name: "Pashmina Shawls" },
    { id: "Textile Art", name: "Rogan Art" },
    { id: "Toys", name: "Wooden Toys" },
  ];

  const craftsOptions = [
    { id: "handloom", name: "Handloom Weaving" },
    { id: "pottery", name: "Jaipur Ceramic" },
    { id: "bidri", name: "Bidri Inlay" },
    { id: "embroidery", name: "Sozni Needlework" },
  ];

  return (
    <div className="flex flex-col min-w-0">
      {/* 56px White PageHeader */}
      <PageHeader
        title="Products & Catalogue"
        howToText="How to add a product"
        onOpenHowTo={() => {}}
      />

      {/* Main Container (max-width 1200, padding 24) */}
      <div className="max-w-[1240px] w-full mx-auto px-4 sm:px-6 py-5 flex flex-col gap-4">
        {/* 1. Soft Terracotta Promo Banner */}
        <PromoBanner
          id="products-verify-banner"
          headline="Get verified, sell for more"
          description="Add a quality video or certificate. Meesho Verified products sell 3.4x faster and command higher prices."
          actionText="Improve products here"
          actionHref="/sell/verification"
        />

        {/* 2. Start Here Card with + Add Product Button and Overview Tiles */}
        <div className="p-5 rounded-lg border border-[#E3E5EC] bg-white shadow-xs flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <p className="text-[13px] text-[#6B7080] font-medium">
                Have something new to sell? Start here.
              </p>
              <h2 className="text-[17px] font-bold text-[#111827]">
                Product Catalog Management
              </h2>
            </div>

            <div className="flex items-center gap-2.5">
              <Link
                href="/sell/new"
                className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-md bg-[#4B3BD1] hover:bg-[#3A2DB0] text-white text-[13.5px] font-semibold transition-colors shadow-xs"
              >
                <Plus className="size-4 stroke-[2.5]" />
                <span>+ Add product</span>
              </Link>
            </div>
          </div>

          <div className="border-t border-[#E3E5EC] pt-4">
            <p className="text-[12px] font-semibold text-[#6B7080] uppercase tracking-wider mb-2.5">
              Overview
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatTile
                label="Total products"
                value={counts.all}
                active={selectedStatus === "all"}
                onClick={() => setSelectedStatus("all")}
              />
              <StatTile
                label="Live · Verified"
                value={counts.verified}
                active={selectedStatus === "verified"}
                onClick={() => setSelectedStatus("verified")}
              />
              <StatTile
                label="Not verified"
                value={counts.not_verified}
                active={selectedStatus === "not_verified"}
                onClick={() => setSelectedStatus("not_verified")}
              />
              <StatTile
                label="Out of stock"
                value={counts.out_of_stock}
                active={selectedStatus === "action_needed"}
                onClick={() => setSelectedStatus("action_needed")}
              />
            </div>
          </div>
        </div>

        {/* 3. Main Data Table Card */}
        <div className="p-4 sm:p-5 rounded-lg border border-[#E3E5EC] bg-white shadow-xs flex flex-col gap-4">
          {/* Top underline tabs */}
          <UnderlineTabs
            tabs={topTabsList}
            activeId={topTab}
            onChange={(id) => setTopTab(id)}
          />

          {/* SubTabs (Status Filter chips) */}
          <SubTabs
            tabs={subTabsList}
            activeId={selectedStatus}
            onChange={(id) => {
              setSelectedStatus(id);
              setPage(1);
            }}
          />

          {/* Filter row: Category, Craft and Search */}
          <FilterRow
            categories={categoriesOptions}
            crafts={craftsOptions}
            selectedCategory={selectedCategory}
            selectedCraft={selectedCraft}
            onSelectCategory={setSelectedCategory}
            onSelectCraft={setSelectedCraft}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            placeholder="Search by product code or title..."
          />

          {/* Yellow InfoStrip */}
          <InfoStrip>
            Products that need action are fixed fastest from the Edit screen. Fix them to go live sooner.
          </InfoStrip>

          {/* Products DataTable */}
          <ProductsDataTable
            items={filteredProducts}
            totalCount={filteredProducts.length}
            currentPage={page}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            onRowClick={(item) => {
              if (item.status === "draft") {
                router.push(`/sell/new/${item.id}`);
              } else {
                router.push(`/sell/products/${item.id}`);
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
