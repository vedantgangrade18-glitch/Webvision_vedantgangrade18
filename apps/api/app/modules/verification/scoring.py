"""Pure scoring functions for the three-layer verification engine (Part 2 §7).

    KARU_SCORE = W1·L1 + W2·L2 + W3·L3            (default 0.35 / 0.25 / 0.40)
    VERIFIED  ⇔ ¬hard_fail ∧ score ≥ threshold ∧ L1 ≥ L1_floor ∧ L3 ≥ L3_floor

Without a making video L3 = 0, so the best possible score is 0.35·100 + 0.25·100 = 60 < 70:
a product cannot be verified without a video (Part 1 §3.3 rule 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


# ---- L1 ------------------------------------------------------------------------------------

def l1_score(handmade_probability: float, originality_penalty: float, max_penalty: float = 40) -> float:
    """L1 = 100·h − penalty (penalty capped), clamped 0–100."""
    penalty = clamp(originality_penalty, 0, max_penalty)
    return round(clamp(100 * handmade_probability - penalty), 2)


# ---- L2 ------------------------------------------------------------------------------------

@dataclass
class ArtisanRecord:
    aadhaar_verified: bool = False
    pehchan_verified: bool = False
    gi_authorised: bool = False
    verified_listings: int = 0
    reviews_count: int = 0
    avg_rating: float | None = None
    completed_orders: int = 0
    confirmed_fake_reports: int = 0
    hard_fail_history: int = 0
    not_as_described_rate: float = 0.0

    @property
    def is_new(self) -> bool:
        """New = no prior completed orders, no prior verified listing and no reviews."""
        return self.completed_orders == 0 and self.verified_listings == 0 and self.reviews_count == 0


@dataclass
class L2Result:
    score: float
    mode: str  # computed|new_artisan_constant
    parts: dict = field(default_factory=dict)


def l2_score(rec: ArtisanRecord, new_artisan_constant: float = 50) -> L2Result:
    if rec.is_new:
        return L2Result(float(new_artisan_constant), "new_artisan_constant", {"constant": new_artisan_constant})
    identity = (15 if rec.aadhaar_verified else 0) + (10 if rec.pehchan_verified else 0) + (5 if rec.gi_authorised else 0)
    identity = min(identity, 30)
    verified = min(rec.verified_listings * 4, 16)
    rating = 0.0
    if rec.reviews_count >= 3 and rec.avg_rating is not None:
        rating = clamp((rec.avg_rating - 3) * 8, -16, 16)
    orders = min(rec.completed_orders * 1, 8)
    history = min(verified + rating + orders, 40)
    penalties = rec.confirmed_fake_reports * 30 + rec.hard_fail_history * 20
    if rec.not_as_described_rate > 0.10:
        penalties += 10
    penalties = min(penalties, 60)
    score = clamp(30 + identity + history - penalties)
    return L2Result(round(score, 2), "computed", {
        "base": 30, "identity": identity, "verified_listings": verified, "rating": round(rating, 2),
        "orders": orders, "penalties": -penalties,
    })


# ---- L3 ------------------------------------------------------------------------------------

def l3_score(process: float, match: float, originality: float, weights: dict | None = None) -> float:
    w = weights or {"process": 0.40, "match": 0.35, "originality": 0.25}
    return round(clamp(w["process"] * process + w["match"] * match + w["originality"] * originality), 2)


def similarity_to_match_score(cos: float, lo: float = 0.55, hi: float = 0.92) -> float:
    """Map embedding cosine similarity to 0–100 with a simple calibrated ramp."""
    if cos <= lo:
        return 0.0
    if cos >= hi:
        return 100.0
    return round(100 * (cos - lo) / (hi - lo), 2)


# ---- Karu Score ------------------------------------------------------------------------------

@dataclass
class Decision:
    karu_score: float
    verdict: str  # verified|not_verified
    reasons: list[str]


def karu_score(l1: float | None, l2: float | None, l3: float | None, weights: dict) -> float:
    return round(weights["L1"] * (l1 or 0) + weights["L2"] * (l2 or 0) + weights["L3"] * (l3 or 0), 2)


def decide(l1: float | None, l2: float | None, l3: float | None, *, hard_fail: bool, cfg: dict) -> Decision:
    score = karu_score(l1, l2, l3, cfg["weights"])
    reasons = []
    if hard_fail:
        reasons.append("hard_fail")
    if score < cfg["threshold"]:
        reasons.append("below_threshold")
    floors = cfg.get("floors", {})
    if (l1 or 0) < floors.get("L1", 0):
        reasons.append("l1_floor")
    if (l3 or 0) < floors.get("L3", 0):
        reasons.append("l3_floor")
    return Decision(score, "not_verified" if reasons else "verified", reasons)


def artisan_tips(l1: float | None, l2: float | None, l3: float | None, *, has_video: bool, aadhaar_verified: bool,
                 l1_quality_failed: bool, hard_fail: bool, l3_detail: dict | None, cfg: dict) -> tuple[list[str], dict]:
    """Message keys for the 'what's missing' checklist + per-layer status (never numbers)."""
    if hard_fail:
        return ["tip.under_review"], {"L1": "under_review", "L2": "under_review", "L3": "under_review"}
    floors = cfg.get("floors", {})
    tips: list[str] = []
    status = {"L1": "ok", "L2": "ok", "L3": "ok"}
    if l1_quality_failed:
        tips.append("tip.retake_photos")
        status["L1"] = "needs_work"
    elif (l1 or 0) < max(floors.get("L1", 40), 60):
        tips.append("tip.photos_look_machine_made")
        status["L1"] = "needs_work"
    if not has_video:
        tips.append("tip.add_video")
        status["L3"] = "missing"
    elif (l3 or 0) < max(floors.get("L3", 50), 60):
        detail = l3_detail or {}
        if detail.get("process", 100) < 60:
            tips.append("tip.video_show_process")
        if detail.get("match", 100) < 60:
            tips.append("tip.video_show_product")
        if not tips or tips[-1] not in ("tip.video_show_process", "tip.video_show_product"):
            tips.append("tip.video_show_process")
        status["L3"] = "needs_work"
    if not aadhaar_verified:
        tips.append("tip.verify_aadhaar")
        if (l2 or 0) < 50:
            status["L2"] = "needs_work"
    return tips, status
