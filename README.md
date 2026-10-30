# Webvision 2.0 — KARU

> **AI-Powered Handloom & Craft Verification Platform**  
> Empowering the hands that weave India's cultural heritage with verifiable authenticity, zero-commission commerce, and multimodal AI.

---

## 🏛️ Overview

**KARU** is a multimodal AI and digital commerce platform designed to protect and promote traditional Indian artisans and authentic handloom heritage. 

### Key Capabilities
- **Multimodal AI Pipeline (Snap & Speak):** Artisans photograph their craft and describe it in their native tongue. Multimodal models extract technical textile specifications, detect weaves, transcribe audio across 8 Indic languages, and compose verified listings.
- **Forensic Verification Engine:** Multi-layer verification analyzing textile metrics, yarn twist, warp/weft irregularity, and handloom signatures to protect artisans against mass-produced counterfeit textiles.
- **Dynamic Pricing & Market Intelligence:** Real-time benchmark ingestion and craft clustering ensuring fair artisan compensation.
- **Offline-First PWA:** Built for rural artisan clusters with low connectivity, leveraging IndexedDB offline queues and background synchronization.
- **Cryptographic Provenance (Karu ID):** Every authentic craft receives a unique verifiable ID with physical QR tags for tamper-proof provenance.

---

## 🗂️ Project Structure

```
Webvision_vedantgangrade18/
├── apps/
│   ├── api/                          # FastAPI Modular Backend (Python 3.12)
│   │   ├── app/
│   │   │   ├── core/                 # DB, Security, UUIDv7, Crockford-32, i18n
│   │   │   ├── modules/
│   │   │   │   ├── ai_pipeline/      # Snap+Speak orchestration & Gemini synthesis
│   │   │   │   ├── verification/     # 3-Layer forensic analysis engine
│   │   │   │   ├── pricing/          # Benchmark ingestion & clustering
│   │   │   │   ├── karu_ids/         # ID lifecycle & PDF tag sheet rendering
│   │   │   │   ├── orders/           # Atomic cart, checkout & reservation timers
│   │   │   │   ├── payments/         # Split payment & escrow holds
│   │   │   │   ├── artisans/         # Passport, KYC, Pehchan validation
│   │   │   │   └── admin/            # Command center API & audit logging
│   │   │   └── providers/            # Pluggable Gemini, Whisper, TinyFish, Razorpay
│   │   ├── migrations/               # Alembic asynchronous database migrations
│   │   └── tests/                    # 34 comprehensive test suites
│   └── web/                          # Next.js 16 App Router (React 19 & Tailwind CSS v4)
│       ├── app/
│       │   ├── sell/                 # Artisan PWA, voice capture & dashboard
│       │   └── api/                  # Route handlers & ISR revalidation
│       ├── components/               # High-craft design system (Radix + Lucide)
│       │   ├── artisan/              # Voice capture, media review & listing wizards
│       │   ├── karu/                 # Badges, provenance panels, voice recorder
│       │   └── ui/                   # Modular UI primitive components
│       ├── lib/                      # Query clients, Dexie offline store, API helpers
│       └── messages/                 # 8-language localization catalogues (en, hi, gu, mr, pa, ta, ml, ur)
└── .gitignore
```

---

## 💻 Tech Stack

| Domain | Technology |
|---|---|
| **Frontend** | Next.js 16.4 (App Router), React 19, TypeScript |
| **Styling** | Tailwind CSS v4.3, Custom Design System Tokens |
| **Backend API** | FastAPI, Python 3.12, Async SQLAlchemy 2.0, Pydantic v2 |
| **Database & Search** | PostgreSQL 16+, `pg_trgm`, Trigram Matching, UUIDv7 |
| **AI / Multimodal** | Google Gemini Multimodal Models, Whisper Audio Processing |
| **Offline Resilience** | Dexie.js (IndexedDB), Service Worker Sync |
| **Internationalization**| `next-intl` with 8 Indic Languages |

---

## ⚡ Quick Start

### 1. Backend Setup (`apps/api`)

```bash
cd apps/api

# Create & activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env

# Run database migrations & seed synthetic clusters
python -m app.scripts.seed

# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation available at `http://localhost:8000/docs`.

---

### 2. Frontend Setup (`apps/web`)

```bash
cd apps/web

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

Visit `http://localhost:3000` to access the artisan dashboard.

---

## 👥 Team Northern Blades

- **Vedant** — UI/UX Strategy & Product Architecture
- **Alshifa** — Indic Design Systems & Design Tokens
- **Sawant** — Backend Architecture, Concurrency & Escrow Rails
- **Nishant** — Multimodal AI Pipeline, Forensics & Web Agents

*Empowering the hands that weave India's cultural soul.*
