"""Part 2 §7.4 worked examples and product rules, reproduced exactly."""

import pytest

from app.core.appconfig import DEFAULTS
from app.modules.verification import scoring

CFG = DEFAULTS["verification.v1"]


def test_new_artisan_good_photos_good_video_is_verified():
    d = scoring.decide(78, 50, 82, hard_fail=False, cfg=CFG)
    assert d.karu_score == pytest.approx(72.6)
    assert d.verdict == "verified"


def test_new_artisan_without_video_is_not_verified():
    d = scoring.decide(78, 50, 0, hard_fail=False, cfg=CFG)
    assert d.karu_score == pytest.approx(39.8)
    assert d.verdict == "not_verified"


def test_established_artisan_synthetic_looking_photos_fails_l1_floor():
    d = scoring.decide(30, 85, 90, hard_fail=False, cfg=CFG)
    assert d.karu_score == pytest.approx(67.75)
    assert d.verdict == "not_verified"
    assert "l1_floor" in d.reasons


def test_no_video_can_never_verify():
    """Max without video = 0.35·100 + 0.25·100 = 60 < 70 (Part 1 §3.3 rule 2)."""
    d = scoring.decide(100, 100, 0, hard_fail=False, cfg=CFG)
    assert d.karu_score == pytest.approx(60)
    assert d.verdict == "not_verified"


def test_hard_fail_blocks_regardless_of_score():
    d = scoring.decide(100, 100, 100, hard_fail=True, cfg=CFG)
    assert d.karu_score == 100
    assert d.verdict == "not_verified"
    assert "hard_fail" in d.reasons


def test_floors_zero_means_pure_combined_score():
    cfg = {**CFG, "floors": {"L1": 0, "L3": 0}}
    assert scoring.decide(30, 85, 90, hard_fail=False, cfg=cfg).verdict == "not_verified"  # 67.75 < 70
    assert scoring.decide(35, 90, 95, hard_fail=False, cfg=cfg).verdict == "verified"  # 12.25+22.5+38 = 72.75


def test_l2_new_artisan_uses_constant():
    res = scoring.l2_score(scoring.ArtisanRecord(aadhaar_verified=True), new_artisan_constant=50)
    assert res.mode == "new_artisan_constant"
    assert res.score == 50


def test_l2_established_formula():
    rec = scoring.ArtisanRecord(aadhaar_verified=True, pehchan_verified=True, verified_listings=2, reviews_count=6,
                                avg_rating=4.5, completed_orders=10)
    res = scoring.l2_score(rec)
    # 30 + identity 25 + history (8 + 12 + 8 = 28) = 83
    assert res.mode == "computed"
    assert res.score == pytest.approx(83)


def test_l2_penalties_capped_and_clamped():
    rec = scoring.ArtisanRecord(completed_orders=3, confirmed_fake_reports=3, hard_fail_history=2, not_as_described_rate=0.5)
    res = scoring.l2_score(rec)
    # 30 + 0 + 3 − 60 (cap) → clamped to 0
    assert res.score == 0


def test_l2_rating_needs_three_reviews():
    rec = scoring.ArtisanRecord(reviews_count=2, avg_rating=1.0, completed_orders=2)
    assert scoring.l2_score(rec).parts["rating"] == 0


def test_l1_and_l3_formulas():
    assert scoring.l1_score(0.8, 10) == 70
    assert scoring.l1_score(0.9, 100) == 50  # penalty capped at 40
    assert scoring.l3_score(80, 85, 100) == pytest.approx(0.4 * 80 + 0.35 * 85 + 0.25 * 100)


def test_tips_for_missing_video_and_aadhaar():
    tips, status = scoring.artisan_tips(78, 50, 0, has_video=False, aadhaar_verified=False, l1_quality_failed=False,
                                        hard_fail=False, l3_detail={}, cfg=CFG)
    assert "tip.add_video" in tips and "tip.verify_aadhaar" in tips
    assert status["L3"] == "missing"


def test_hard_fail_tip_is_not_accusatory():
    tips, status = scoring.artisan_tips(90, 50, 90, has_video=True, aadhaar_verified=True, l1_quality_failed=False,
                                        hard_fail=True, l3_detail={}, cfg=CFG)
    assert tips == ["tip.under_review"]
