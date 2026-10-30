"""Imports every model so `Base.metadata` is complete (Alembic, create_all, tests)."""

from app.modules.admin.models import AppConfig, AuditLog, ExternalCall, Report  # noqa: F401
from app.modules.artisans.models import ArtisanProfile, Passport  # noqa: F401
from app.modules.auth.models import AuthOtp, Consent, RefreshToken, User  # noqa: F401
from app.modules.catalog.models import AiExtraction, Category, Craft, Listing, ListingMedia, ListingVersion  # noqa: F401
from app.modules.jobs.models import Job  # noqa: F401
from app.modules.karu_ids.models import KaruId, KaruIdEvent, ScanAggregate  # noqa: F401
from app.modules.media.models import Media, Upload  # noqa: F401
from app.modules.notifications.models import Notification  # noqa: F401
from app.modules.orders.models import Address, BuyerProfile, CartItem, Order, OrderItem, Return  # noqa: F401
from app.modules.payments.models import Payment, Refund, Transfer, WebhookEvent  # noqa: F401
from app.modules.pricing.models import ListingPriceAdvice, PriceBenchmark, PriceSource  # noqa: F401
from app.modules.requests.models import BulkOpportunity, BulkRequest, BulkResponse, MakeAgainRequest  # noqa: F401
from app.modules.reviews.models import Follow, Review, Wishlist  # noqa: F401
from app.modules.syndication.models import SyndicationJob  # noqa: F401
from app.modules.verification.models import (  # noqa: F401
    EvidenceItem,
    ImageMatch,
    VerificationLayerResult,
    VerificationRun,
)
