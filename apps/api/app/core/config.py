"""Runtime settings. Every external service is optional: when its key is missing the
matching provider falls back to a deterministic fake (see app/providers)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "apps/api/.env"), env_file_encoding="utf-8", extra="ignore")

    env: Literal["local", "test", "staging", "prod"] = "local"
    app_name: str = "Karu API"

    # Public URLs
    public_base_url: str = "http://localhost:3000"  # what QR codes and share links point to
    # Browser-facing base for API-served URLs (upload parts, media, test KYC). In local dev the web app
    # proxies /api/v1 and /media, so pointing this at the web origin keeps everything same-origin.
    api_base_url: str = "http://localhost:3000"
    cdn_base_url: str = ""  # public media base; empty → served by the API at /media

    # Data stores
    database_url: str = "sqlite+aiosqlite:///./var/karu.db"
    redis_url: str = ""  # empty → in-memory rate limits, in-process jobs

    # Jobs: "inline" runs jobs in-process (dev, tests); "celery" sends them to Redis-backed workers
    task_mode: Literal["inline", "celery"] = "inline"
    run_scheduler: bool = True  # in-process periodic jobs when not using Celery Beat

    # Object storage
    storage_backend: Literal["local", "s3"] = "local"
    local_storage_dir: str = "./var/media"
    s3_endpoint: str = ""
    s3_region: str = "ap-south-1"
    s3_bucket_private: str = ""
    s3_bucket_public: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""

    # Security
    jwt_secret: str = "dev-only-change-me-dev-only-change-me"
    field_encryption_key: str = ""  # base64 32 bytes; empty → derived from jwt_secret (dev only)
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cookie_secure: bool = False
    admin_totp_required: bool = True
    web_revalidate_secret: str = ""
    web_internal_url: str = "http://localhost:3000"

    # AI / external providers
    openai_api_key: str = ""
    openai_stt_model: str = "whisper-1"
    stt_provider: Literal["auto", "whisper", "gemini", "vertex", "fake"] = "auto"
    gemini_api_key: str = ""
    gemini_model_extract: str = "gemini-2.5-flash"
    gemini_model_vision: str = "gemini-2.5-flash"
    gemini_model_image: str = "gemini-3-pro-image"
    vertex_project: str = ""
    vertex_location: str = "us-central1"
    vertex_image_location: str = "global"
    imagegen_backend: str = "auto"
    tinyfish_api_key: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    # Route linked-account business profile; verify against Razorpay's category list before live mode.
    razorpay_la_category: str = "ecommerce"
    razorpay_la_subcategory: str = "arts_and_collectibles"
    sms_provider_key: str = ""  # MSG91 auth key
    msg91_sender_id: str = "KARUAI"
    msg91_template_id: str = ""
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    email_api_key: str = ""  # Resend
    email_from: str = "Karu <hello@karu.ai>"
    kyc_provider_key: str = ""
    google_client_id: str = ""
    demo_syndication_credentials_ref: str = ""
    pehchan_lookup_url: str = "https://handicrafts.nic.in/"
    gi_registry_url: str = "https://search.ipindia.gov.in/GIRPublic/"

    sentry_dsn: str = ""
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @property
    def is_dev(self) -> bool:
        return self.env in ("local", "test")

    @property
    def media_public_base(self) -> str:
        return (self.cdn_base_url or f"{self.api_base_url}/media").rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
