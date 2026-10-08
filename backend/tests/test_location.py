"""Tests for engine/location.py — multi-location comparison scoring."""
import pytest

from backend.data.seed import main as seed_main
from backend.engine.location import compare_locations
from backend.store import DataStore


@pytest.fixture(scope="module", autouse=True)
def generate():
    seed_main()


@pytest.fixture(scope="module")
def store():
    return DataStore()


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


# ── Correct ordering ────────────────────────────────────────────────


def test_scores_order(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    locs = [r["location"] for r in rows]
    assert locs == ["remote_india", "hyderabad", "pune", "bengaluru"]


# ── Individual score targets (±0.02 tolerance) ──────────────────────


def test_remote_india_086(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    ri = next(r for r in rows if r["location"] == "remote_india")
    assert abs(ri["score"] - 0.86) <= 0.02


def test_hyderabad_052(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    hyd = next(r for r in rows if r["location"] == "hyderabad")
    assert abs(hyd["score"] - 0.52) <= 0.02


def test_pune_049(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    pune = next(r for r in rows if r["location"] == "pune")
    assert abs(pune["score"] - 0.49) <= 0.02


def test_bengaluru_018(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    blr = next(r for r in rows if r["location"] == "bengaluru")
    assert abs(blr["score"] - 0.18) <= 0.02


# ── Market data passed through ──────────────────────────────────────


def test_market_data_in_rows(store):
    stats = _senior_stats(store)
    rows = compare_locations(LOCATIONS, SUPPLIES, stats)
    blr = next(r for r in rows if r["location"] == "bengaluru")
    assert blr["ttf_p50"] == 62
    assert blr["ttf_p80"] == 81
    assert blr["pay_p50_lpa"] == 32.0


# ── Custom weights change scores ────────────────────────────────────


def test_custom_weights_change_scores(store):
    stats = _senior_stats(store)
    default = compare_locations(LOCATIONS, SUPPLIES, stats)
    custom = compare_locations(LOCATIONS, SUPPLIES, stats,
                               weights={"supply": 0.10, "speed": 0.10, "cost": 0.70, "remote": 0.10})
    d_blr = next(r for r in default if r["location"] == "bengaluru")
    c_blr = next(r for r in custom if r["location"] == "bengaluru")
    assert d_blr["score"] != c_blr["score"]
