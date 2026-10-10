"""Tests for engine/sourcing.py — sourcing channels (M9).

TC34  Relocate card order: Remote-India, Hyderabad, Pune, Bengaluru
TC35  3 past finalists, no consent=false candidate
      Channel ranking: past_finalists, referral, supplier, job_board
      Campus not applicable for Senior
"""
from __future__ import annotations

from datetime import date

import pytest

from backend.engine.location import compare_locations
from backend.engine.market import matching_supply
from backend.engine.sourcing import analyze_sourcing

TODAY = date(2026, 10, 8)

SENIOR_SKILLS = [
    {"id": "react", "importance": "must"},
    {"id": "nodejs", "importance": "must"},
    {"id": "kubernetes", "importance": "must"},
    {"id": "typescript", "importance": "nice"},
    {"id": "docker", "importance": "nice"},
    {"id": "javascript", "importance": "nice"},
    {"id": "rest_apis", "importance": "nice"},
    {"id": "postgresql", "importance": "nice"},
]


@pytest.fixture(scope="module")
def sourcing_result(store):
    return analyze_sourcing(
        sourcing_df=store.ats.sourcing_history(),
        past_finalists_df=store.ats.past_finalists(),
        suppliers_df=store.vms.suppliers(),
        level="senior",
        today=TODAY,
    )


@pytest.fixture(scope="module")
def relocate_card(store):
    candidates_df = store.ats.candidates()
    candidate_skills = store.ats.candidate_skills()
    market_stats = store.market.market_stats()
    must_ids = [s["id"] for s in SENIOR_SKILLS if s["importance"] == "must"]

    locations = ["bengaluru", "hyderabad", "pune", "remote_india"]
    supplies: dict[str, int] = {}
    for loc in locations:
        s, _ = matching_supply(
            loc, "senior",
            "remote" if loc == "remote_india" else "onsite",
            must_ids, candidates_df, candidate_skills,
        )
        supplies[loc] = s

    loc_stats = market_stats[market_stats["level"] == "senior"]
    return compare_locations(locations, supplies, loc_stats)


# ── TC34: Relocate card order ──────────────────────────────────────────────


def test_relocate_card_order(relocate_card):
    locs = [r["location"] for r in relocate_card]
    assert locs == ["remote_india", "hyderabad", "pune", "bengaluru"]


def test_relocate_card_scores(relocate_card):
    by_loc = {r["location"]: r["score"] for r in relocate_card}
    assert by_loc["remote_india"] == 0.79
    assert by_loc["hyderabad"] == 0.36
    assert by_loc["pune"] == 0.34
    assert by_loc["bengaluru"] == 0.00


def test_relocate_card_supply(relocate_card):
    by_loc = {r["location"]: r["supply"] for r in relocate_card}
    assert by_loc["remote_india"] == 210
    assert by_loc["hyderabad"] == 31
    assert by_loc["pune"] == 26
    assert by_loc["bengaluru"] == 14


def test_relocate_card_ttf(relocate_card):
    blr = next(r for r in relocate_card if r["location"] == "bengaluru")
    assert blr["ttf_p50"] == 62
    assert blr["ttf_p80"] == 81
    remote = next(r for r in relocate_card if r["location"] == "remote_india")
    assert remote["ttf_p50"] == 28
    assert remote["ttf_p80"] == 40


# ── TC35: Past finalists ───────────────────────────────────────────────────


def test_three_past_finalists(sourcing_result):
    assert sourcing_result["past_finalists"]["count"] == 3


def test_two_remote_ready_finalists(sourcing_result):
    assert sourcing_result["past_finalists"]["remote_ready"] == 2


def test_no_consent_false_in_finalists(store):
    pf = store.ats.past_finalists()
    assert (pf["opted_in_pool"] == True).all()  # noqa: E712
    result = analyze_sourcing(
        sourcing_df=store.ats.sourcing_history(),
        past_finalists_df=pf,
        suppliers_df=store.vms.suppliers(),
        level="senior",
        today=TODAY,
    )
    assert result["past_finalists"]["count"] == 3


# ── Channel ranking ────────────────────────────────────────────────────────


def test_channel_ranking_order(sourcing_result):
    ranked = [c for c in sourcing_result["channels"] if c["rank"] is not None]
    ranked.sort(key=lambda c: c["rank"])
    labels = [c["channel"] for c in ranked]
    assert labels == [
        "Past finalists (ATS rediscovery)",
        "Employee referral",
        "Staffing supplier A (via MSP)",
        "Job board",
    ]


def test_referral_fill_rate(sourcing_result):
    ref = next(c for c in sourcing_result["channels"]
               if c["channel"] == "Employee referral")
    assert ref["fill_rate"] == pytest.approx(0.38)
    assert ref["median_days"] == 34


def test_supplier_fill_rate(sourcing_result):
    sup = next(c for c in sourcing_result["channels"]
               if "supplier" in c["channel"].lower())
    assert sup["fill_rate"] == pytest.approx(0.45)
    assert sup["median_days"] == 9


def test_job_board_fill_rate(sourcing_result):
    jb = next(c for c in sourcing_result["channels"]
              if c["channel"] == "Job board")
    assert jb["fill_rate"] == pytest.approx(0.22)
    assert jb["median_days"] == 52


def test_campus_not_applicable_for_senior(sourcing_result):
    campus = next(
        (c for c in sourcing_result["channels"] if c["channel"] == "Campus"),
        None,
    )
    assert campus is not None
    assert campus["rank"] is None
    assert "Not applicable" in campus["evidence"]


# ── Suppliers ──────────────────────────────────────────────────────────────


def test_supplier_a_top(sourcing_result):
    sups = sourcing_result["suppliers"]
    assert sups[0]["supplier_id"] == "SUP-01"
    assert sups[0]["fill_rate"] == pytest.approx(0.45)
    assert sups[0]["median_days_to_submit"] == 9


# ── TC-named aliases (Phase 14A) ──────────────────────────────────────────────

def test_tc34_relocate_card_order(relocate_card):
    test_relocate_card_order(relocate_card)


def test_tc35_three_past_finalists(sourcing_result):
    test_three_past_finalists(sourcing_result)
