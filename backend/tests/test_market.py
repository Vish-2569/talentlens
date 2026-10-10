"""Tests for engine/market.py — supply counting, TTF adjustment."""
import pytest

from backend.engine.market import matching_supply, ttf_adjusted, market_card


MUST_SKILLS = ["react", "nodejs", "kubernetes"]


# ── Supply counts (Section 13) ──────────────────────────────────────


def test_bengaluru_senior_supply_14(store):
    cands = store.ats.candidates()
    cand_sk = store.ats.candidate_skills()
    count, _ = matching_supply("bengaluru", "senior", "onsite",
                               MUST_SKILLS, cands, cand_sk)
    assert count == 14


def test_without_kubernetes_47(store):
    cands = store.ats.candidates()
    cand_sk = store.ats.candidate_skills()
    count, _ = matching_supply("bengaluru", "senior", "onsite",
                               ["react", "nodejs"], cands, cand_sk)
    assert count == 47


def test_remote_india_210(store):
    cands = store.ats.candidates()
    cand_sk = store.ats.candidate_skills()
    count, _ = matching_supply("remote_india", "senior", "remote",
                               MUST_SKILLS, cands, cand_sk)
    assert count == 210


def test_hyderabad_31(store):
    cands = store.ats.candidates()
    cand_sk = store.ats.candidate_skills()
    count, _ = matching_supply("hyderabad", "senior", "onsite",
                               MUST_SKILLS, cands, cand_sk)
    assert count == 31


def test_pune_26(store):
    cands = store.ats.candidates()
    cand_sk = store.ats.candidate_skills()
    count, _ = matching_supply("pune", "senior", "onsite",
                               MUST_SKILLS, cands, cand_sk)
    assert count == 26


# ── TTF budget factor ───────────────────────────────────────────────


def test_ttf_budget_factor_125():
    result = ttf_adjusted(
        ttf_base=62.0,
        supply=14,
        supply_ref=14,
        budget_lpa=28.0,
        sal_p50=32.0,
    )
    assert abs(result / 62.0 - 1.25) < 0.01


# ── Market card returns correct structure ────────────────────────────


def test_market_card_values(store):
    stat = store.market.stat("bengaluru", "senior")
    card = market_card("bengaluru", "senior", 14, stat)
    assert card["supply"] == 14
    assert card["ttf_p50"] == 62
    assert card["ttf_p80"] == 81
    assert card["sal_p50"] == 32.0


# ── Returns candidate IDs ───────────────────────────────────────────


def test_returns_candidate_ids(store):
    cands = store.ats.candidates()
    cand_sk = store.ats.candidate_skills()
    count, ids = matching_supply("bengaluru", "senior", "onsite",
                                 MUST_SKILLS, cands, cand_sk)
    assert len(ids) == count
    assert all(isinstance(i, str) for i in ids)
