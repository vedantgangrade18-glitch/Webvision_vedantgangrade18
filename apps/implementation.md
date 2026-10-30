# Sell on Karu — Seller Panel Frontend Spec

> **What this file is.** The frontend build spec for the artisan dashboard ("Sell on Karu", routes under `/sell`). It replaces the *look and layout* of the artisan screens in `KARU_PRODUCT_SPEC.md` §4.1 / §7 with a **desktop seller-panel layout** (dark left sidebar, data tables, two-step "Add Product" form with a sticky right column), based on reference screenshots supplied by the team.
>
> **What it does not change.** The backend, data model, API and business rules stay exactly as in `KARU_PRODUCT_SPEC.md` and `KARU_TECHNICAL_SPEC.md`. Every screen here maps to existing endpoints (§12). If something in this file seems to need a new endpoint or column, it doesn't: use the mapping given, and do not invent backend fields.
>
> **Read with:** `KARU_PRODUCT_SPEC.md` (§3 concepts, §8 language, §9 tokens) and `KARU_TECHNICAL_SPEC.md` (§2 stack, §5 data model, §14 API).
>
> **Visual target (NB, 2026-10-30).** The seller dashboard must **look just like the reference seller panel** in the screenshots (a large Indian marketplace's supplier panel): same layout, density, sidebar, tables, two-step form, violet primary colour, cool grey background and sticky footer. When this file and the screenshots disagree on *looks*, the screenshots win. When they disagree on *data or behaviour*, this file and the backend specs win.
>
> **Brand rule.** Match the look exactly, but every name, logo, illustration and line of copy is Karu's own. Never show the other company's name or logo.
>
> **AI is part of the flow.** Unlike the reference (a manual form), Karu fills the form for the artisan: one photo becomes a full set of product images (§8.6 b), and a voice description fills the title, description and all product details (§7.3, §8.3). This uses Karu's existing AI/ML backend (technical spec §6); no new models or endpoints.

Version 0.2 · 2026-10-30 · Changes from 0.1: violet primary to match the reference, voice-to-fill made the main path, one photo → multiple images, phone layout confirmed. Open decisions in §15.

---

## 0. Build instructions for the coding agent

1. Stack (fixed by the technical spec): **Next.js App Router + TypeScript, Tailwind CSS with CSS variables, Radix/shadcn-style local components, Lucide icons, next-intl, TanStack Query, react-hook-form + zod.** Use logical Tailwind classes (`ms-`, `me-`, `ps-`, `pe-`, `start-`, `end-`) everywhere so Urdu RTL works.
2. All artisan routes live in a route group `app/(seller)/sell/...` that uses the **SellerShell** layout (§3).
3. Build in this order: tokens → SellerShell → shared components (§5) → Products list (§6) → Add Product step 1 (§7) → step 2 (§8) → the remaining pages (§9) → states and i18n pass (§10–11).
4. Use **mock data that matches the API types** (generate types from the OpenAPI schema with `openapi-typescript`) until the API is live. Put mocks behind one `NEXT_PUBLIC_USE_MOCKS` flag.
5. Every text string goes through next-intl. No hard-coded English in components.
6. Acceptance checklist is in §14. A screen is done only when every item for it passes.

---

## 1. Reference screens (what we are matching)

| Ref | What it shows | Karu screen |
|---|---|---|
| R1 | Panel home for catalogue: dark sidebar, page title + help links, promo banner, "Add" buttons, overview stat tiles, tabs, status sub-tabs, filter + search row, info strip, table with image, category, ID, date, count, status pill, action button | **Products** `/sell/products` (§6) |
| R2 | Step 1 "Select Category": search box, cascading category columns, right panel with breadcrumb, sample image and "Add Product Images" button, yellow guideline box, "Discard" bottom-left | **Add Product · Step 1** `/sell/new` (§7) |
| R3 | Step 2 "Add Product Details": stepper, product strip with "+ Add Product", "Copy input details to all products" checkbox, two-column label-left form, horizontally scrolling price/inventory table, attribute dropdowns, right column with image guidelines, uploaded images, price breakdown, buyer preview; sticky footer "Discard / Save and Go Back / Submit" | **Add Product · Step 2** `/sell/new/[draftId]` (§8) |
| — | Orange "Listify" panel seen in some screenshots | **Not part of the panel** (a browser extension). Do not build. |
| — | Bulk upload tab / Image bulk upload | **Not built** (no backend). Do not show. |

---

## 2. Design tokens

Use the tokens from `KARU_PRODUCT_SPEC.md` §9.2 as CSS variables. The panel adds a few **layout tokens** below. Components must only reference tokens, never raw hex, so the palette can be swapped in one file (`styles/tokens.css`).

### 2.1 Colour roles for the panel

| Role token | Default value | Used for |
|---|---|---|
| `--panel-sidebar-bg` | `#1B1F2E` (deep ink-navy) | Sidebar background |
| `--panel-sidebar-text` | `#C9CCD6` | Sidebar item text/icons |
| `--panel-sidebar-active-bg` | `#2A3050` | Active sidebar item background |
| `--panel-sidebar-active-text` | `#FFFFFF` | Active item text |
| `--panel-sidebar-section` | `#7C8196` | Sidebar section labels ("Manage business") |
| `--panel-page-bg` | `#F1F2F6` | Area behind cards (cool light grey, as in the reference) |
| `--panel-card-bg` | `#FFFFFF` | Cards, table, form panels |
| `--panel-border` | `#E3E5EC` | Card borders, table row dividers, input borders |
| `--panel-primary` | `#4B3BD1` (violet, as in the reference) | Primary buttons, active tab underline, selected category cell, links, mic button |
| `--panel-primary-hover` | `#3A2DB0` | Hover / pressed |
| `--panel-primary-tint` | `#EFEDFC` | Selected row/tab tint, chip backgrounds, "Filled by Karu" highlight |
| `--panel-info-strip-bg` | `#FFF7DD` | Yellow info strip and guideline boxes |
| `--panel-info-strip-border` | `#F3DFA0` | Its border |
| `--panel-info-icon` | `var(--color-haldi-500)` | Bulb / info icon |
| `--panel-banner-bg` | `#FBEDE6` (soft terracotta tint) | Promo banner background |
| `--panel-error` | `var(--color-danger-600)` | Required-field error border/text |
| `--panel-success` | `var(--color-peacock-600)` | Verified pill, step-done tick |
| `--panel-text` | `var(--color-ink-900)` | Body text |
| `--panel-text-muted` | `#6B7080` | Labels, table headers, helper text |
| `--panel-placeholder` | `#A3A7B5` | Input placeholders |

> **Decided (NB):** the panel uses the violet of the reference. Karu's own palette (product spec §9.2) stays for the buyer marketplace and the Karu ID page. Pick the final shade with an eyedropper on the screenshots if it needs to be closer; change only `--panel-primary*`.

### 2.2 Type (Latin; Indic per product spec §9.3)

Panel is dense, so it uses smaller sizes than the mobile spec. Font: **Noto Sans** (and the matching Noto script for the active locale).

| Token | Size / line-height / weight | Used for |
|---|---|---|
| `text-page-title` | 18 / 26 / 600 | "Products", "Add Single Product" |
| `text-section` | 15 / 22 / 600 | Card section titles ("Product, size and inventory") |
| `text-stat` | 22 / 28 / 700 | Overview tile numbers |
| `text-body` | 14 / 20 / 400 | Default |
| `text-label` | 13 / 18 / 500, muted | Form labels, table headers |
| `text-small` | 12 / 16 / 400 | Helper text, pills, sidebar section labels |
| `text-tiny` | 11 / 14 / 400 | Legal disclaimer, char counters |

Indic scripts: line-height × 1.15 (see product spec §9.3).

### 2.3 Spacing, radius, elevation

- 4 px grid. Card padding 16 (compact) / 24 (forms). Gap between cards 16.
- Radius: inputs 6, buttons 6, cards 8, pills full, image tiles 6.
- Elevation: cards use a 1 px `--panel-border` and no shadow. Only the sticky footer and dropdown menus get `0 -2px 8px rgba(20,24,40,.06)` / `0 4px 16px rgba(20,24,40,.12)`.
- Inputs: height **36 px** desktop, **44 px** below 768 px. Buttons: M 36 px, L 40 px. Touch targets on phone ≥ 44 px.

---

## 3. SellerShell (layout for every `/sell` page)

```
┌──────────────┬───────────────────────────────────────────────────────────────┐
│ [avatar] Name▾│  Page title                       ▶ How to … video   ⓘ Need help? │  ← PageHeader (56px, white)
│ 🔔 Notices(5) │───────────────────────────────────────────────────────────────│
│ ☎ Support    │                                                               │
│──────────────│   page content on --panel-page-bg, max-width 1200, padding 24 │
│ 🏠 Home       │                                                               │
│ MANAGE BUSINESS                                                               │
│ 📦 Orders     │                                                               │
│ ↩ Returns    │                                                               │
│ ₹ Price advice│                                                              │
│ 🗂 Products ◀ │   (active item: --panel-sidebar-active-bg)                     │
│ 🏷 Stock & IDs│                                                               │
│ ✔ Verification│                                                              │
│ 💳 Payouts    │                                                               │
│ ✉ Requests   │                                                               │
│ GROW         │                                                               │
│ 🔗 Share & QR │                                                               │
│ 🪪 Passport   │                                                               │
│ ⚙ Settings   │                                                               │
│──────────────│                                                               │
│ [Karu logo]  │                                                               │
│ Sell on Karu │                                                               │
└──────────────┴───────────────────────────────────────────────────────────────┘
```

### 3.1 Sidebar

- Width **232 px**, fixed, full height, `--panel-sidebar-bg`, own scroll (thin scrollbar).
- **Top block:** artisan avatar (32 px, with the profile-completion ring from product spec §4.1) + public name + chevron → menu: *View passport*, *Language*, *Log out*. Under it two small outlined buttons side by side: **Notices (N)** (opens notifications drawer) and **Support** (opens help drawer).
- **Items** (icon 18 px + label 14 px, row height 36 px, radius 6, 8 px horizontal inset):

| Section | Item | Route | Screen |
|---|---|---|---|
| — | Home | `/sell` | A05 (§9.1) |
| Manage business | Orders | `/sell/orders` | A13 |
| | Returns | `/sell/orders?tab=returns` | A13 returns tab |
| | Price advice | `/sell/price-advice` | A11 price tab, all products |
| | **Products** | `/sell/products` | A05 list / §6 |
| | Stock & Karu IDs | `/sell/stock` | A11 stock tab, all products |
| | Verification | `/sell/verification` | A12, all products |
| | Payouts | `/sell/payouts` | A14 |
| | Requests | `/sell/requests` | A16 (badge with open count) |
| Grow | Share & QR | `/sell/share` | A19 |
| | Passport & profile | `/sell/passport` | A15 |
| | Settings | `/sell/settings` | A17 |

- Badges: small pill on the right of an item (Orders: count *to pack*; Requests: open count). Source: `GET /artisan/dashboard`.
- Bottom: Karu wordmark (light) + "Sell on Karu" caption.
- `[DEMO]` flag `syndication.demo` adds "Also list on…" under Grow.

### 3.2 PageHeader

- 56 px white bar across the content area, bottom border.
- Left: optional back chevron (`‹`) + page title.
- Right: **"▶ How to …"** link (opens a modal with the voice-narrated help clip for that page, product spec §4.1 Help) and **"ⓘ Need help?"** (opens Support drawer). Add a **language switcher** (globe icon + current language in its own script) here; product spec requires it in the header.

### 3.3 Responsive

| Width | Behaviour |
|---|---|
| ≥ 1280 | As drawn. Content max-width 1200 centred. |
| 1024–1279 | Sidebar 208 px; Add Product right column 300 px. |
| 768–1023 | Sidebar collapses to a 64 px icon rail with tooltips; right column moves below the form. |
| < 768 | Sidebar hidden; hamburger in PageHeader opens it as a drawer. **Bottom nav** from product spec §5 appears: Home · Orders · **+** · Requests · Me. Tables become stacked cards (§5.6). Footer action bar stays sticky. **[Decided]** |

---

## 4. Status vocabulary (one mapping, used everywhere)

The reference panel uses "QC" statuses. Karu's equivalents come from `listings.status` + `listings.verification_status`. Use this exact mapping for tabs, pills and filters.

| Tab / pill label (en) | Rule (API fields) | Pill style |
|---|---|---|
| **Draft** | `status = draft` | grey outline, file icon |
| **Action needed** | `status = draft` with missing required fields, **or** `verification_status = not_verified`, **or** `quantity_available = 0` | terracotta tint, alert icon |
| **Processing** | `status = processing` (AI filling) **or** `verification_status = checking` | indigo tint, animated dots |
| **Not verified yet** | `status = published` and `verification_status in (none, not_verified)` | neutral `--color-unverified`, never red |
| **Live · Verified** | `status = published` and `verification_status = verified` | peacock tint, check icon |
| **Paused** | `status = paused` | grey, pause icon |

Never use "fake", "error" or "failed" for verification. Copy follows product spec §8.3.

---

## 5. Shared components

| Component | Spec |
|---|---|
| **StatTile** | Bordered box 180×72, label `text-small` muted on top, number `text-stat`. Optional delta caption. Used in "Overview". |
| **PromoBanner** | Full-width card, `--panel-banner-bg`, 88 px tall. Left: small illustration (Karu's own spot illustration, 64 px). Middle: headline 18/600 + one line `text-small`. Right: primary button. Dismissible (×), dismissal remembered per session. One banner at a time, priority: payout setup needed → orders to ship → add making video → general tip. Copy keys in §11. |
| **Tabs (underline)** | Text tabs with count in brackets, active = `--panel-primary` text + 2 px underline. Used for top-level tabs. |
| **SubTabs (text chips)** | Smaller (13 px) text tabs with counts, active = primary text + tint background. Used for status filters. |
| **FilterRow** | "Filter by:" label + Select (Category) + optional Select (Craft) on the left; SearchInput ("Search by product code", magnifier on the end) on the right. |
| **InfoStrip** | Full-width, `--panel-info-strip-bg`, 1 px border, bulb icon, one line of `text-small`. |
| **DataTable** | White card, sticky header row (`text-label` muted, 40 px), body rows 72 px with 48 px thumbnail, 1 px dividers, hover tint. Columns per page. Pagination footer: "Rows per page 10/20/50" + "1–20 of 312" + prev/next. Cursor pagination from the API. Below 768 px each row renders as a card (thumbnail left, key fields stacked, action button full-width). |
| **StatusPill** | Per §4. |
| **FormRow** | Two-column label-left layout: label cell 140 px, right-aligned, `text-label`, red `*` for required, ⓘ tooltip icon; input cell flexible. Two FormRows per line on ≥ 1024 px (grid `[140px 1fr 140px 1fr]`, gap 16/24), one per line below. Error: red border + message below input. |
| **VoiceField** | Text input or textarea with a **mic button inside the end of the field** (20 px icon, indigo). Tap → listening state (pulsing ring) → `POST /stt` → text inserted. Every free-text field in the panel is a VoiceField (product spec §8.2). |
| **SelectField** | Radix Select / Combobox with search when > 10 options, chevron, placeholder "Select". |
| **CategoryColumns** | §7.2. |
| **ProductStrip** | §8.2. |
| **PriceInventoryTable** | §8.4. |
| **ImageUploader** | §8.6. |
| **PriceRangeBar** | As product spec §9.6, compact variant (height 8, labels below). |
| **SettlementBox** | §8.6 (c). |
| **StickyFooter** | 64 px white bar fixed to the bottom of the content area, top shadow. Left: outlined "Discard". Right: outlined "Save and go back" + primary "Submit". |
| **Drawer** | Right-side 400 px for Notices and Support. |
| **EmptyState / Skeleton / ErrorState / UploadQueueBanner** | As product spec §9.6. |

---

## 6. Products page — `/sell/products` (matches R1)

### 6.1 Wireframe

```
PageHeader:  Products                               ▶ How to add a product   ⓘ Need help?
┌───────────────────────────────────────────────────────────────────────────────────┐
│ [illus] Get verified, sell for more                                [Get verified] │ PromoBanner
│         Add a making video. Verified pieces usually sell at a higher price.       │
└───────────────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Have something new to sell? Start here.                                           │
│ [ + Add product ]                                                                 │
│                                                                                   │
│ Overview                                                                          │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                    │
│ │Total products│ │Live·Verified│ │Not verified │ │Out of stock │                    │
│ │ 42          │ │ 18          │ │ 21          │ │ 3           │                    │
│ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘                    │
└───────────────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────────────┐
│ All (42)  Action needed (6)  Processing (2)  Not verified yet (21)  Live·Verified (18)  Draft (4)  Paused (1)
│ Filter by: [Select category ▾] [Select craft ▾]               [Search by product code 🔍]
│ 💡 Products that need action are fixed fastest from the Edit screen. Fix them to go live sooner.
│ S.no │ Image │ Category        │ Product code │ Created on        │ Karu IDs │ Status          │ Actions        │
│ 1    │ [img] │ Sarees › Silk   │ AB12CD3      │ 6 Mar 2026, 7:58 PM│ 3 (2 left)│ ● Not verified │ [Edit product] │
│ 2    │ [img] │ Pottery › Bowls │ —            │ 5 Mar 2026, 1:12 PM│ —        │ ○ Draft        │ [Continue]     │
│ …                                                                                 │
│ Rows per page 20 ▾                                               1–20 of 42  ‹ ›  │
└───────────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Details

- **Top card:** helper line + primary button **"+ Add product"** → `/sell/new`. (No "Add in bulk" button. §15 Q5.)
- **Overview tiles** from `GET /artisan/dashboard` (add counts are already in "summary counts"); if a count is missing in the response, compute it from `GET /listings/mine` totals per status. Tiles are clickable and apply the matching SubTab.
- **SubTabs** = §4 statuses with counts. URL keeps state: `?status=action_needed&category=…&q=…&page=…`.
- **Table columns:**

| Column | Source | Notes |
|---|---|---|
| S.no | row index | |
| Image | primary `listing_media` thumbnail | 48×60 (4:5), rounded 6 |
| Category | `category.name` (localised) with parent: "Sarees › Silk" | 2 lines max |
| Product code | `short_code` | Copy icon on hover; "—" for drafts |
| Created on | `created_at` | Format "6 Mar 2026, 7:58 PM", localised |
| Karu IDs | `quantity_total` (`quantity_available` left) | "Out of stock" in terracotta when 0 |
| Price | `price_inr` with price-advice dot (green in range / amber below / grey unknown) from `price_position` | Optional column; show on ≥ 1280 |
| Status | StatusPill §4 | |
| Actions | Primary small button: Draft → **Continue**; Action needed → **Fix now**; else **Edit product**. Kebab menu: View on Karu, Share, Pause/Resume, Add stock, Delete | Delete opens confirm dialog (soft delete, product spec §4.1) |

- Row click (outside buttons) → `/sell/products/{id}` (manage product, §9.3).
- Sort: newest first. Empty state: illustration + "You haven't added any products yet" + "+ Add product".

---

## 7. Add Product · Step 1 "Select category" — `/sell/new` (matches R2)

### 7.1 Wireframe

```
PageHeader: ‹ Add product                                  ▶ How to add a product   ⓘ Need help?
  (1) Select category ──── (2) Add product details          ← Stepper (step 1 active, underline)

Search category
[🔍 Handloom saree  in Clothing & Textiles                          ]

┌Your categories┐┌Level 2──────────┐┌Level 3──────────┐┌Level 4───────┐ ┌ Right panel ───────────────┐
│■ Your categories│ Sarees        ▸│ Silk sarees    ▸│ Banarasi     │ │ Clothing › Sarees › Silk › │
│ Clothing & Text▸│ Dupattas      ▸│ Cotton sarees  ▸│ Bhagalpuri ◀ │ │ Bhagalpuri                 │
│ Home & Living  ▸│ Shawls        ▸│ Linen sarees   ▸│ Kanjivaram   │ │ [sample good photo]        │
│ Pottery        ▸│ …              │ …               │ …            │ │ Add clear photos of the    │
│ Jewellery      ▸│                │                 │              │ │ front of your product.     │
│ Art & Paintings▸│                │                 │              │ │ [ ⬆ Add product photos ]   │
│ …               │                │                 │              │ │                            │
└────────────────┘└────────────────┘└─────────────────┘└──────────────┘ │ ── after photos ──         │
                                                                         │ 🎤 Describe it by voice    │
                                                                         │ 💡 Guidelines (yellow box) │
                                                                         └────────────────────────────┘
StickyFooter: [Discard]
```

### 7.2 CategoryColumns

- Data: `GET /catalog/categories` (tree with `parent_id`). Cache with TanStack Query (staleTime 24 h).
- Column 1: **"Your categories"** (pinned first, bookmark icon; categories the artisan used before, from `GET /listings/mine` distinct categories) then all top-level categories.
- Each column 200 px wide, 320 px tall, own scroll, row height 40, items with children show `▸`. Selected item: `--panel-primary` background, white text. Clicking an item opens the next column; leaf selection enables the right panel.
- **Search** box above: debounced 250 ms, searches localised names across the tree client-side, shows results as rows "Leaf **in** Top-level" (like R2). Picking a result expands the columns to that path.
- Breadcrumb in the right panel shows the full path.

### 7.3 Right panel (sticky, 320 px)

1. Breadcrumb (grey card header).
2. Sample photo for the category (from `categories.icon` or a static per-category asset) + line "Add clear photos of the front of your product."
3. **"⬆ Add product photos"** primary button → file picker (`accept="image/*"`, `multiple`; on mobile `capture="environment"` option). Client compression with `browser-image-compression` to ≤ 500 KB each, max **6** photos (`limits.v1.photos_max`).
4. After photos are picked: thumbnails row + the **"🎤 Describe your product"** voice card. This is the main path, so it is shown open and prominent (not collapsed):
   - Big round violet mic button (64 px), live waveform, timer, max 120 s (`limits.v1.voice_note_max_s`), in the artisan's language or dialect.
   - Prompt shown and read aloud: "Tell us what it is, what it's made of, its size and colour, how long it took, and your price."
   - After stop: play back, **Re-record**, or **Use this**. Skip link: "Skip, I'll type it".
   - The recording is uploaded as a `voice` media item and sent with the draft (item 6). Karu's backend transcribes it (STT, technical spec §6.1) and extracts every field from the transcript + photos (Gemini, §6.2).
   - Mic permission denied → inline help + "Type instead".
5. Yellow **Guidelines** box: "General guidelines" (1. One clear photo is enough. Karu makes the other images from it. You can add up to 6. 2. All photos must be of the product in the category you chose.) and "Photo guidelines · View all" (1. No text or watermarks on the main photo. 2. Use daylight and a plain background. 3. Show the whole piece, without other objects.).
6. **Continue** button (primary, appears when ≥ 1 photo uploaded) → creates the draft:
   - Upload media: `POST /media/uploads` → parts → `/complete` (resumable; UploadQueueBanner if offline).
   - `POST /listings` with `{category_id, media_ids, voice_media_id?}` → returns `{listing_id, job_id}`.
   - Navigate to `/sell/new/{listing_id}` immediately; step 2 shows "Karu is filling in your details…" until the job completes (SSE `GET /jobs/{id}/events`).

> **Multiple photos = one product.** In Karu one listing is one product (batch). To add a second, different product in the same category, use "+ Add product" on step 2 (§8.2).

- **Discard** (footer) → confirm dialog → if a draft exists `DELETE /listings/{id}`, back to `/sell/products`.

---

## 8. Add Product · Step 2 "Add product details" — `/sell/new/[draftId]` (matches R3)

### 8.1 Wireframe

```
PageHeader: ‹ Add product                                        ▶ How to …   ⓘ Need help?
  (✓) Select category ──── (2) Add product details
┌ProductStrip────────────────────────────────────┐
│ [thumb] Product 1 ▔▔▔▔   [+ Add product]       │
└────────────────────────────────────────────────┘
┌ Form card (flex 1) ───────────────────────────────────────┐ ┌ Right column (340, sticky) ────┐
│ Add product details                                       │ │ 💡 Follow these to get verified│
│ ☑ Copy input details to all products                      │ │    faster (yellow)             │
│   To change a field for one product only, select it above│ │ Photo guidelines   View all    │
│                                                           │ │ ① No text/watermark on main    │
│ ✨ Filled by Karu from your photos and voice. Check each   │ │ ② … ③ …                       │
│    field. [🔄 Regenerate all]                              │ │ Add photos showing:            │
│ Product, size and inventory                               │ │ [▣] Front · main photo         │
│  Product name* ⓘ [Bhagalpuri silk saree…   🎤 🔄]  Size* ⓘ [Free size ▾]                     │
│  Net weight* ⓘ  [450] g                    Your code ⓘ [optional          ]                   │
│ ☑ Copy price details to all sizes                         │ │ [▣] Detail · close-up of work  │
│ ┌Size────┬Karu price*ⓘ┬MRP ⓘ──┬Stock*──┬Returnable┬ … ┐  │ │ [▣] Making · you at work       │
│ │Free size│[ 2,800 ]  │[3,200] │[ 3 ]  │ [● on]   │   │  │ │ Uploaded photos                │
│ └─────────┴───────────┴────────┴───────┴──────────┴───┘  │ │ [img][img][img][ + Add ]       │
│  ◄═══════════════════════════════►                        │ │ Front photo* CHANGE            │
│ Price advice: Shops sell similar handmade sarees for     │ │────────────────────────────────│
│ ₹2,600–₹3,400.  [▬▬▬▬▬●▬▬]  [Use ₹2,800]  Updated 3h ago  │ │ Your earnings                  │
│                                                           │ │ Karu price          ₹2,800    │
│ Product details                                           │ │ Karu commission (0%)    ₹0    │
│  Material* [Silk ▾]           Technique* [Handloom ▾]     │ │ Payment fees     Paid by Karu │
│  Dye       [Natural ▾]        Colour*    [Maroon ▾]       │ │ You receive         ₹2,800    │
│  Length    [5.5] m            Time to make [12] days      │ │────────────────────────────────│
│  Care      [Dry clean ▾]      Craft*     [Bhagalpuri silk▾]│ │ How buyers will see it         │
│                                                           │ │ [thumb] Bhagalpuri silk saree  │
│ Description and story                                     │ │ ₹2,800  ● Not verified yet    │
│  [Your language | English | Hindi]                        │ └────────────────────────────────┘
│  [textarea …                          🎤 🔄]  412/2000    │
│  Tags [silk ×] [handloom ×] [+ add]                       │
│                                                           │
│ Returns and verification                                  │
│  Returnable  [● on]  Listings that accept returns usually │
│              sell more. You decide.                       │
│  Making video (optional)  [⬆ Upload or record]            │
│   Get Karu Verified: 30 s–3 min of you making this piece. │
│                                                           │
│ small grey legal text (tiny)                              │
└───────────────────────────────────────────────────────────┘
StickyFooter: [Discard]                                   [Save and go back] [Submit]
```

### 8.2 ProductStrip

- Horizontal strip of product chips (thumbnail 40 px + "Product N"), active chip has a 3 px primary underline. Scroll arrows when overflowing.
- **"+ Add product"** → modal with the photo uploader (§7.3 items 3–5) → creates a **new draft listing** in the same category (`POST /listings`) and adds a chip. Each chip is its own listing id.
- **"Copy input details to all products"** checkbox (default on): when on, edits to shared fields (everything except photos, product name, voice note) are applied to every draft in the strip client-side, then each draft is PATCHed. When off, edits apply to the active product only.
- Submit publishes every draft in the strip that passes validation; failures stay with an error badge on their chip.

### 8.3 AI prefill (Snap + Speak inside the form)

- While the extraction job runs: every field shows a skeleton shimmer and a top InfoStrip "Karu is filling in your details from your photos and voice… usually under 20 seconds". The artisan can still type.
- On completion: `GET /listings/{id}` fills **the whole form**: product name, description (source language + English + Hindi), every category attribute (material, technique, colour, size, dimensions, time to make, care …), craft, tags, suggested price and the image set (§8.6 b). Every AI-filled field gets a small violet "✨ Filled by Karu" tag until the artisan edits it. Fields with low `field_confidence` get an amber left border and helper "Please check this". If `notes_for_artisan` / `missing_fields` come back (e.g. "Say the length of the saree"), show them in an InfoStrip at the top with a mic button next to each, so the artisan can answer by voice.
- **"🎤 Describe again"** button in the form header (always visible, violet outline): records a new description. The new transcript fills the description field (via `POST /stt`), then the artisan can tap **Regenerate all** so Karu re-reads it and updates the other fields.
- **Mic on every field:** each text field has its own mic (VoiceField → `POST /stt`, ≤ 15 s); dropdowns have a mic too: the spoken word is matched to the closest option (client-side fuzzy match on localised option labels) and selected, or the dropdown opens filtered to it if unsure.
- Each AI-filled field has a small **🔄 Regenerate** icon → `POST /listings/{id}/regenerate {field}`; "Regenerate all" in the section header. Respect `limits.v1.regenerate_per_listing_per_day` (disable with tooltip when reached).
- If extraction fails or there is no voice note: the form is simply empty with mic buttons; nothing blocks.

### 8.4 Form sections and field mapping

All saves are `PATCH /listings/{id}` (debounced autosave every 3 s of inactivity + on blur; "Saved" / "Saving…" caption next to the stepper). Only fields listed here exist; do not add GST, HSN, brand, manufacturer, packer or importer fields (§15 Q4).

**(a) Product, size and inventory**

| Label | Control | Required | API field |
|---|---|---|---|
| Product name | VoiceField, max 120 | ✓ | `title[source_lang]` |
| Size | Select from category `attribute_schema.size` (default "Free size") | ✓ if schema has size | `attributes.size` |
| Net weight (g) | Number | ✓ | `shipping.weight_g` |
| Your product code | Text, optional, helper "Your own code to find it later" | — | `attributes.seller_code` |

**PriceInventoryTable** (one row per listing; horizontal scroll inside the card on narrow screens, with the scrollbar visible as in R3):

| Column | Control | Required | API field |
|---|---|---|---|
| Size | read-only text | — | `attributes.size` |
| Karu price ⓘ ("What the buyer pays") | ₹ number, Indian grouping | ✓ | `price_inr` |
| MRP ⓘ ("Shop price, optional. Shown struck-through if higher") | ₹ number | — | `compare_at_inr` |
| Stock ⓘ ("Each piece gets its own Karu ID") | Number stepper, min 1 | ✓ | publish body `quantity` |
| Returnable | Switch | — | publish body `returnable` (default on) |
| Ships in (days) | Number | — | `shipping.ships_in_days` |

- "Copy price details to all sizes" checkbox above the table is shown only when more than one product is in the strip with the same size; it copies the row to them.
- Under the table: **PriceRangeBar** with advice text from `GET /listings/{id}/price-advice` and button **"Use ₹X"** → `POST /listings/{id}/price-advice/accept` and fills Karu price. Show "Updated N hours ago" and a "Sources" link (popover with 3–5 sites and prices). Copy rules: product spec §3.4 (never "you are underpricing", always "Shops sell similar …").

**(b) Product details** — rendered dynamically from the selected category's `attribute_schema` (JSON schema: key, label per locale, type `select|number|text|multiselect`, options, unit, required). Common keys: material, technique, dye, colour, dimensions/length, time_to_make_days, care, craft (`craft_id`, Select from crafts). Two FormRows per line. Values → `attributes.{key}`; craft → `craft_id`.

**(c) Description and story**

- Language tabs: *Your language* (source) · English · Hindi. Source tab is editable VoiceField textarea (max 2000, counter bottom-right like R3). English/Hindi tabs show the auto-translation, editable, with "Translated by Karu" caption. → `description{lang}`.
- Tags: chip input, max 10 → `tags`.

**(d) Returns and verification**

- Returnable switch (mirrors the table column) + nudge copy (product spec §8.4).
- **Making video** (optional): upload or record button → resumable upload → `POST /listings/{id}/making-video {media_id}`. Guidance text from product spec F3. Shows progress bar and "You can leave this page; upload continues" when large.

**(e) Legal text** (`text-tiny`, muted, above the footer): "By submitting, you confirm this product is made by you or your workshop, the details are true, and you agree to Karu's seller terms. Photos, voice and making video may be shown on the product's Karu ID page as described in your consent settings."

### 8.5 Validation

- zod schema per category, generated from `attribute_schema` + fixed fields.
- Required-field errors show only after the first Submit attempt or on blur of a touched field: red border, red helper text, and the chip in ProductStrip gets a red dot. On Submit with errors, scroll to and focus the first invalid field.
- Price must be > 0; MRP, if set, must be ≥ price; stock 1–999.

### 8.6 Right column (sticky, 340 px; below the form on < 1024 px)

**(a) Guidelines card** — yellow: "Follow these to get verified faster" + numbered photo guidelines + "View all" link (modal with full guidelines and good/bad examples).

**(b) Photos card**
- "Add photos showing:" list with small icon tiles: *Front · main photo* (required), *Detail · close-up of the work*, *Making · you at work* (optional, helps verification). Clicking one opens the picker tagged with that role.
- "Uploaded photos" grid of 72×90 tiles: first tile labelled **"Front photo\*"** with a **CHANGE** link; others "Photo 2…6" with an × delete button on hover; last tile **"+ Add"** while under 6. Drag to reorder (first = primary). Each tile shows upload progress and a retry icon on failure.
- **One photo → multiple images.** The artisan needs to upload only **one** photo. Karu's image pipeline (technical spec §6.3: crop to subject, background clean, auto-levels, 4:5 and 1:1 variants) returns several `enhanced_photo` media items for it. Show them in a row titled **"✨ Made by Karu from your photo"** directly under the uploaded photos: each tile has **Use** (adds it to the listing's images) and **×** (dismiss). Default: the cleaned 4:5 version is pre-selected as the Front photo and the 1:1 version as Photo 2; the artisan's original stays as Photo 3. While processing, show 3 shimmering tiles with "Karu is preparing your photos…".
- These are edits of the real photo only (no AI-invented scenes or extra angles). Originals are always kept for verification, so the artisan can switch back to the original any time with "Use original".
- If the artisan uploads more photos, each one gets its own set of variants.

**(c) SettlementBox "Your earnings"** (replaces the reference panel's settlement breakdown):

| Row | Value |
|---|---|
| Karu price | `price_inr` |
| Karu commission (0%) | ₹0 |
| Payment fees | "Paid by Karu" |
| **You receive** | **= `price_inr`** (bold, primary) |

Caption: "Money reaches your bank or UPI after the return window ends." Link "Set up payouts" if `payout_status != active`.

**(d) Buyer preview** — compact ProductCard (thumb, title 2 lines, price, MRP struck if set, VerifiedBadge state, maker name) exactly as the marketplace will show it.

### 8.7 Footer actions

| Button | Action |
|---|---|
| **Discard** (outlined, left) | Confirm dialog "Delete this draft? Photos and details will be removed." → `DELETE /listings/{id}` for every draft in the strip → `/sell/products` |
| **Save and go back** (outlined) | Flush autosave → `/sell/products?status=draft` with toast "Saved as draft" |
| **Submit** (primary) | Validate → `POST /listings/{id}/publish {quantity, returnable}` for each valid draft → success page §8.8 |

### 8.8 Submitted — `/sell/new/[draftId]/done`

Centred white card: product thumb, "Your Bhagalpuri silk saree is live!", "3 Karu IDs created" (list of codes, collapsible), verification status pill ("Checking… usually under 10 minutes" with live SSE update), and buttons: **Share** (→ share sheet A19), **Add making video** (if none), **Add another product**, **Go to products**.

---

## 9. Other pages (same shell, same patterns)

Every page below uses: PageHeader → optional PromoBanner → Overview StatTiles (where listed) → Tabs/SubTabs → FilterRow → DataTable. Keep identical spacing to §6.

### 9.1 Home — `/sell`
- Greeting card ("Namaste, Ramesh") + one PromoBanner by priority (§5).
- Overview tiles: *Today's views*, *Orders to pack*, *Money on the way*, *Open requests* (from `GET /artisan/dashboard`).
- Two cards side by side: **"Needs your attention"** (list rows: orders to pack, products needing action, payout setup, open requests, each with a button) and **"Price advice"** (top 3 products with amber dot, "Use ₹X").
- Profile-completion card (dismissible, once per session; product spec §4.1).

### 9.2 Orders — `/sell/orders`
- Tabs: To pack (n) · Shipped (n) · Delivered (n) · Returns (n) → `GET /artisan/orders?status=`.
- Columns: Order no. · Image · Product · Karu ID · Buyer (first name, city) · Ordered on · Amount · Status · Action (**Mark shipped** → modal: courier + tracking no., both VoiceFields → `POST /artisan/orders/items/{id}/ship`).
- Returns tab columns: Order no. · Product · Reason · Requested on · Status · Action (**Confirm received** → `POST /artisan/returns/{id}/receive`).
- Row click → right Drawer with order detail (address, timeline).

### 9.3 Manage product — `/sell/products/[id]`
- PageHeader: ‹ product title, StatusPill, kebab (Pause/Resume, Delete).
- Underline Tabs: **Overview · Price advice · Verification · Edit · Stock & Karu IDs · Sales & payouts · Share** (product spec §4.1 A11).
- **Edit** tab reuses the Step 2 form (§8.4) in edit mode, footer becomes [Cancel] [Save changes].
- **Stock & Karu IDs**: "Add stock" (number → `POST /listings/{id}/stock`), DataTable of `GET /listings/{id}/karu-ids` (Karu ID · Status · Created · Order), "Print tags (PDF)" → `GET /listings/{id}/tags.pdf` [PILOT].
- **Verification**: horizontal 3-step stepper *Photos checked · Your record · Making video* with each step's status and tip from `artisan_tips`; video upload; **Try again** → `POST /listings/{id}/verify`. No raw scores (product spec §15.6).

### 9.4 Price advice — `/sell/price-advice`
- SubTabs: All · Below range · In range · Above range · No data (from `price_position`).
- Columns: Image · Product · Your price · Similar handmade range · Position dot · Updated · Action (**Use ₹X** / **View sources**).

### 9.5 Stock & Karu IDs — `/sell/stock`
- Tiles: Total pieces · Available · Sold · Out-of-stock products.
- Columns: Image · Product · Available / Total · Status · Action (**Add stock**). Out of stock rows highlighted terracotta text.

### 9.6 Verification — `/sell/verification`
- Tiles: Verified · Checking · Not verified yet · Passport state.
- SubTabs by verification status; columns: Image · Product · Status · Missing step (e.g. "Making video") · Action (**Add making video** / **Try again** / **View**).

### 9.7 Payouts — `/sell/payouts`
- If `payout_status != active`: setup card first (UPI or bank, VoiceFields, KYC status chip) → `POST /artisan/payouts/setup`.
- Tiles: Paid out · On hold (return window) · Failed.
- Columns: Date · Order no. · Product · Amount · Status (on hold until DD MMM / sent / failed) from `GET /artisan/payouts`.

### 9.8 Requests — `/sell/requests`
- Tabs: Make this again (n) · Bulk opportunities (n).
- Make-again columns: Product · Buyer city · Quantity · Needed by · Note · Status · Action (**Reply** → modal price + days + message → `POST /artisan/requests/{id}/reply`, **Decline**).
- Bulk columns: Category · Quantity · Target price · Deadline · Action (**I can make…** → `POST /artisan/bulk-opportunities/{id}/respond`). Only shown for verified artisans; others see an InfoStrip explaining how to get verified.

### 9.9 Share & QR — `/sell/share`
- Product picker (DataTable with Select) → share panel: format chooser (WhatsApp status 9:16 · Instagram post 4:5 · Link only · Clean image), preview from `POST /listings/{id}/share-image`, buttons Share (Web Share API) / Copy link / Download. Product spec §4.5.

### 9.10 Passport & profile — `/sell/passport`
- Left: PassportCard (product spec §9.6) with "Download image". Right: "How to get verified" checklist. Below: public profile form (photo, story VoiceField, crafts, years, cluster) → `PATCH /artisan/profile`.

### 9.11 Settings — `/sell/settings`
- Sections as product spec A17 in white cards with FormRows: Language, Voice prompts, Notifications (WhatsApp/SMS/in-app), Privacy (hide voice clip), Account (log out, delete account with confirm).

### 9.12 Onboarding — `/sell/start`
- Not in the reference. Keep product spec F1 (language → phone → OTP → details → consent), rendered as a centred 480 px white card on `--panel-page-bg` with the Karu logo above, so it matches the panel style.

---

## 10. States (every page)

| State | Treatment |
|---|---|
| Loading | Skeletons in the exact shape of tiles, table rows (5) and form rows. No spinners on full pages. |
| Empty | EmptyState inside the table card: Karu spot illustration + one sentence + one action. |
| Error | Inline ErrorState in the card: "Something went wrong. [Try again]". Toast for failed mutations. |
| Offline | UploadQueueBanner pinned under PageHeader: "Waiting for network. Saved on this device." Forms keep working; drafts and media are queued (IndexedDB + Background Sync, tech spec §9.2). |
| Processing | Pills with animated dots; SSE updates rows live without reload. |
| Permission denied (mic/camera) | Inline helper under the control with "How to allow" link; fall back to typing / gallery. |

---

## 11. Language, RTL and copy

- 8 locales (`hi, en, pa, mr, gu, ur, ta, ml`); default from the artisan's `locale`. Switcher in PageHeader and in the sidebar user menu.
- **Urdu:** `dir="rtl"` on `<html>`. Sidebar moves to the right, chevrons and arrows mirror, tables read right-to-left, horizontal scroll starts at the right. Use logical properties only.
- Numbers: Western digits, Indian grouping `₹1,00,000`. Dates: "6 Mar 2026, 7:58 PM" localised.
- Labels can be long in Tamil/Malayalam: label cells wrap to 2 lines (never truncate labels); table headers wrap.
- Copy keys (English source, translate all). Examples:

| Key | English |
|---|---|
| `products.title` | Products |
| `products.addCta` | Add product |
| `products.helper` | Have something new to sell? Start here. |
| `banner.verify.title` | Get verified, sell for more |
| `banner.verify.body` | Add a making video. Verified pieces usually sell at a higher price. |
| `banner.payout.title` | Finish payout setup to receive ₹{amount} |
| `info.actionNeeded` | Products that need action are fixed fastest from the Edit screen. |
| `new.step1` / `new.step2` | Select category / Add product details |
| `new.addPhotos` | Add product photos |
| `new.filling` | Karu is filling in your details from your photos and voice… |
| `new.copyAll` | Copy input details to all products |
| `new.discard` / `new.saveBack` / `new.submit` | Discard / Save and go back / Submit |
| `earnings.title` | Your earnings |
| `earnings.receive` | You receive |
| `status.notVerified` | Not verified yet |

Tone: product spec §8.3 (warm, simple, never blaming).

---

## 12. Screen → API map (nothing new on the backend)

| Screen | Reads | Writes |
|---|---|---|
| Shell | `GET /me`, `GET /artisan/dashboard` | `PATCH /me` (locale) |
| Home | `GET /artisan/dashboard`, `GET /listings/mine` | — |
| Products | `GET /listings/mine`, `GET /catalog/categories` | `POST /listings/{id}/pause|resume`, `DELETE /listings/{id}` |
| Add · step 1 | `GET /catalog/categories` | `POST /media/uploads*`, `POST /listings` |
| Add · step 2 | `GET /listings/{id}`, `GET /jobs/{id}/events`, `GET /listings/{id}/price-advice` | `PATCH /listings/{id}`, `POST /listings/{id}/regenerate`, `POST /listings/{id}/price-advice/accept`, `POST /listings/{id}/making-video`, `POST /stt`, `POST /listings/{id}/publish` |
| Manage product | `GET /listings/{id}`, `/karu-ids`, `/verification`, `/price-advice` | `POST /listings/{id}/stock`, `/verify`, `/share-image`, `GET /tags.pdf` |
| Orders | `GET /artisan/orders` | `POST /artisan/orders/items/{id}/ship`, `POST /artisan/returns/{id}/receive` |
| Payouts | `GET /artisan/payouts` | `POST /artisan/payouts/setup` |
| Requests | `GET /artisan/requests`, `GET /artisan/bulk-opportunities` | `POST /artisan/requests/{id}/reply`, `POST /artisan/bulk-opportunities/{id}/respond` |
| Passport | `GET /artisan/passport`, `GET /artisan/profile` | `PATCH /artisan/profile` |

Errors arrive as `{error: {code, message_key, details}}`; show `message_key` through next-intl.

---

## 13. File structure (suggested)

```
apps/web/app/(seller)/sell/
  layout.tsx                 # SellerShell
  page.tsx                   # Home
  products/page.tsx          # §6
  products/[id]/page.tsx     # §9.3
  new/page.tsx               # §7
  new/[draftId]/page.tsx     # §8
  new/[draftId]/done/page.tsx
  orders/ payouts/ requests/ price-advice/ stock/ verification/ share/ passport/ settings/ start/
apps/web/components/seller/
  Sidebar.tsx PageHeader.tsx StatTile.tsx PromoBanner.tsx Tabs.tsx SubTabs.tsx FilterRow.tsx
  InfoStrip.tsx DataTable.tsx StatusPill.tsx FormRow.tsx VoiceField.tsx CategoryColumns.tsx
  ProductStrip.tsx PriceInventoryTable.tsx ImageUploader.tsx SettlementBox.tsx StickyFooter.tsx
apps/web/styles/tokens.css   # §2
apps/web/messages/{locale}.json
```

---

## 14. Acceptance checklist

**Shell**
- [ ] Sidebar 232 px dark, sections and items as §3.1, active item highlighted, badges from API.
- [ ] PageHeader with title, help-video link, Need help, language switcher.
- [ ] Responsive behaviour per §3.3 at 1440, 1100, 900, 390 px.
- [ ] Urdu renders mirrored with no layout breaks.

**Products (§6)**
- [ ] Banner, "+ Add product", 4 overview tiles, 7 status sub-tabs with counts.
- [ ] Filter by category/craft, search by product code, URL holds filter state.
- [ ] Table columns and actions as §6.2; mobile shows cards.

**Add product (§7–8)**
- [ ] Category search + 4-level cascading columns + breadcrumb panel.
- [ ] 1–6 photos, compressed ≤ 500 KB, resumable, offline-queued; prominent voice description card ≤ 120 s.
- [ ] One uploaded photo shows a "Made by Karu from your photo" row of variants with Use / ×, cleaned version pre-selected as Front photo.
- [ ] Voice description fills name, description (3 languages), all attributes, tags and price; "Filled by Karu" tags; missing-info prompts answerable by mic; mic on every field including dropdowns.
- [ ] Violet primary and cool grey background match the screenshots side by side.
- [ ] Draft created, step 2 shows AI-fill shimmer, then pre-filled fields with low-confidence highlights.
- [ ] Two-column label-left form, required `*`, ⓘ tooltips, mic in every text field, regenerate per field.
- [ ] Price/inventory table scrolls horizontally inside its card; price advice bar with "Use ₹X".
- [ ] Right column: guidelines, photo grid with Front photo + CHANGE + reorder, earnings box (0% commission), buyer preview.
- [ ] Product strip with "+ Add product" and "Copy input details to all products".
- [ ] Autosave; footer Discard / Save and go back / Submit; validation scrolls to first error.
- [ ] Success page with Karu IDs, live verification status and Share.

**All pages**
- [ ] Loading, empty, error, offline states (§10).
- [ ] No hard-coded strings; all 8 locales load.
- [ ] No other brand's name, logo or copy anywhere.
- [ ] WCAG 2.2 AA contrast; keyboard navigation through sidebar, tabs, table, form; visible focus ring.

---

## 15. Decisions taken on defaults (team may change)

| # | Question | Default used in this spec |
|---|---|---|
| Q1 | Phone layout | **Decided:** desktop matches the reference; phone collapses the sidebar into a drawer and adds the bottom nav. |
| Q2 | Manual form vs AI | **Decided:** same form as the reference, filled by Karu's AI from photo + voice; mic on every field; one photo becomes multiple images. |
| Q3 | Colour | **Decided:** violet primary like the reference (§2.1). |
| Q4 | Fields the backend doesn't have | GST, HSN, brand, manufacturer, packer, importer dropped. MRP → `compare_at_inr`. "Returns price" → Returnable switch. Settlement box shows 0% commission. |
| Q5 | Bulk upload and third-party template panel | Not built. |
