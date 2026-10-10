"""Tests for engine/location.py — M6 location comparison (Section 7).

Formula: min–max normalised, weights supply=0.35 / speed=0.30 / cost=0.25 / remote=0.10.
Penalty: (reloc_package_lpa / max_reloc_in_set) × PENALTY_WEIGHT=0.05, clipped to [0,1].

Section 13 scores (0.86/0.52/0.49/0.18) are not reachable with this formula given the
fixed supply/TTF story values; recomputed targets are 0.79/0.36/0.34/0.00 (see DECISIONS.md).
"""
import pytest

from backend.engine.location import compare_locations


LOCATIONS = ["remote_india", "hyderabad", "pune", "bengaluru"]
SUPPLIES = {
    "remote_india": 210,
    "hyderabad": 31,
    "pune": 26,
    "bengaluru": 14,
}


def _senior_stats(store):
    stats = store.market.market_stats()
    return stats[stats["level"] == "senior"]


# ── Ordering (must always hold) ──────────────────────────────────────


def test_scores_order(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    locs = [r["location"] for r in rows]
    assert locs == ["remote_india", "hyderabad", "pune", "bengaluru"]


# ── Per-location scores (recomputed targets, §13 / DECISIONS.md) ─────


def test_remote_india_079(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    ri = next(r for r in rows if r["location"] == "remote_india")
    assert abs(ri["score"] - 0.79) <= 0.02


def test_hyderabad_036(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    hyd = next(r for r in rows if r["location"] == "hyderabad")
    assert abs(hyd["score"] - 0.36) <= 0.02


def test_pune_034(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    pune = next(r for r in rows if r["location"] == "pune")
    assert abs(pune["score"] - 0.34) <= 0.02


def test_bengaluru_000(store):
    # Bengaluru is the minimum on all four dimensions so scores 0.00 before penalty,
    # then the ₹2L reloc package drives it negative → clipped to 0.00.
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    blr = next(r for r in rows if r["location"] == "bengaluru")
    assert blr["score"] == 0.0


# ── Market data passed through ───────────────────────────────────────


def test_market_data_in_rows(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    blr = next(r for r in rows if r["location"] == "bengaluru")
    assert blr["ttf_p50"] == 62
    assert blr["ttf_p80"] == 81
    assert blr["pay_p50_lpa"] == 32.0


# ── Custom weights change scores ──────────────────────────────────────


def test_custom_weights_change_scores(store):
    stats = _senior_stats(store)
    default = compare_locations(LOCATIONS, SUPPLIES, stats)
    custom = compare_locations(LOCATIONS, SUPPLIES, stats,
                               weights={"supply": 0.10, "speed": 0.10, "cost": 0.70, "remote": 0.10})
    d_ri = next(r for r in default if r["location"] == "remote_india")
    c_ri = next(r for r in custom if r["location"] == "remote_india")
    assert d_ri["score"] != c_ri["score"]
