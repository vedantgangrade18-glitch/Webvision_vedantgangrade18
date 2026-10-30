"""DPDP: hard-delete PII 30 days after a self-delete; sold Karu IDs keep anonymised history
("Made by a Karu artisan in Bhagalpur")."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import utcnow
from app.core.jobs import periodic
from app.modules.auth.models import Consent, RefreshToken, User


@periodic("auth.purge_deleted", every_s=24 * 3600)
async def purge_deleted(db: AsyncSession) -> None:
    from app.modules.artisans.models import ArtisanProfile
    from app.modules.orders.models import Address

    cutoff = utcnow() - timedelta(days=30)
    users = (await db.execute(select(User).where(User.status == "deleted", User.deleted_at < cutoff,
                                                 User.phone_enc.is_not(None) | User.email.is_not(None)))).scalars().all()
    for u in users:
        u.phone_enc = u.phone_hash = u.email = u.google_sub = None
        u.display_name = None
        u.totp_secret_enc = None
        await db.execute(delete(Address).where(Address.user_id == u.id))
        await db.execute(delete(RefreshToken).where(RefreshToken.user_id == u.id))
        await db.execute(delete(Consent).where(Consent.user_id == u.id))
        p = (await db.execute(select(ArtisanProfile).where(ArtisanProfile.user_id == u.id))).scalar_one_or_none()
        if p:
            p.public_name = "A Karu artisan"
            p.legal_name_enc = p.dob_enc = p.aadhaar_last4_enc = p.pehchan_card_no_enc = p.payout_details_enc = None
            p.village_town = p.pin_code = None
            p.lat = p.lng = None
            p.story_text = {}
            p.story_voice_media_id = p.profile_photo_media_id = None
            p.linked_social_urls = []
            p.payout_masked = None
