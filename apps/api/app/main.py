"""Karu API — modular monolith (Part 2 §1)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Register models and job handlers.
import app.models  # noqa: F401,E402
from app.core.config import get_settings
from app.core.db import Base, get_engine, sessionmaker
from app.core.errors import install_error_handlers
from app.modules.ai_pipeline import service as _ai  # noqa: F401,E402
from app.modules.auth import tasks as _auth_tasks  # noqa: F401,E402
from app.modules.media import service as _media  # noqa: F401,E402
from app.modules.notifications import service as _notify  # noqa: F401,E402
from app.modules.orders import service as _orders  # noqa: F401,E402
from app.modules.payments import service as _payments  # noqa: F401,E402
from app.modules.pricing import service as _pricing  # noqa: F401,E402
from app.modules.syndication import service as _syndication  # noqa: F401,E402
from app.modules.verification import engine as _verification  # noqa: F401,E402

logging.basicConfig(level=logging.INFO, format='{"t":"%(asctime)s","lvl":"%(levelname)s","log":"%(name)s","msg":"%(message)s"}')
log = logging.getLogger("karu")


async def _bootstrap() -> None:
    from app.modules.catalog.reference import ensure_reference_data

    s = get_settings()
    if s.database_url.startswith("sqlite"):
        Path(s.database_url.split("///")[-1]).parent.mkdir(parents=True, exist_ok=True)
        # Local/dev convenience; Postgres environments use Alembic migrations.
        async with get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with sessionmaker()() as db:
        await ensure_reference_data(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.core import jobs

    s = get_settings()
    if s.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=s.sentry_dsn, environment=s.env, traces_sample_rate=0.05, send_default_pii=False)
    await _bootstrap()
    stop = asyncio.Event()
    tasks: list[asyncio.Task] = []
    if s.task_mode == "inline":
        await jobs.resume_pending()
        if s.run_scheduler:
            tasks.append(asyncio.create_task(jobs.scheduler_loop(stop)))
    yield
    stop.set()
    for t in tasks:
        t.cancel()
    await get_engine().dispose()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Karu API", version="1.0.0", lifespan=lifespan, openapi_url="/api/v1/openapi.json",
                  docs_url="/api/v1/docs", redoc_url=None)
    install_error_handlers(app)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"], expose_headers=["ETag"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    from app.modules.admin.public_router import router as reports_router
    from app.modules.admin.router import router as admin_router
    from app.modules.artisans.router import router as artisans_router
    from app.modules.auth.router import router as auth_router
    from app.modules.catalog.router_artisan import router as listings_router
    from app.modules.catalog.router_public import router as catalog_router
    from app.modules.jobs.router import router as jobs_router
    from app.modules.media.router import router as media_router
    from app.modules.notifications.router import router as notifications_router
    from app.modules.orders.router import router as orders_router
    from app.modules.payments.router import router as payments_router
    from app.modules.requests.router import router as requests_router
    from app.modules.reviews.router import router as reviews_router
    from app.modules.syndication.service import router as syndication_router

    for r in (auth_router, artisans_router, media_router, listings_router, catalog_router, jobs_router, orders_router,
              payments_router, reviews_router, requests_router, notifications_router, admin_router, reports_router,
              syndication_router):
        app.include_router(r, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health():
        return {"ok": True, "env": s.env}

    if s.storage_backend == "local":
        public_dir = Path(s.local_storage_dir) / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=public_dir), name="media")
    return app


app = create_app()
