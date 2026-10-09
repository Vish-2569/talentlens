"""Tests for engine/redline.py — Requisition Redline.

TC04  5 marks, correct severities (3 red, 2 amber), spans match raw text
TC05  relax Kubernetes only → supply 14 → 47 (supply_delta == 33)
TC06  relax location only  → Remote-India 210, P50 28
TC08  same inputs twice    → identical scenario output (determinism)
      32 scenario keys
      total compute < 1 s per call
      every hover number equals an engine value
"""
from __future__ import annotations

import time
from datetime import date

import pytest

from backend.data.seed import main as seed_main
from backend.engine.parser import regex_parse
from backend.engine.redline import CONSTRAINT_ORDER, analyze_redline
from backend.store import DataStore

TODAY = date(2026, 10, 8)

DEMO_TEXT = (
    "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, "
    "must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days"
)


# ── Stub option scorer ────────────────────────────────────────────────────────

def _stub_scorer(ctx: dict, market_ctx: dict) -> dict:
    """Deterministic stub scorer — logic matches the demo story top-option mapping."""
    loc = ctx.get("location", "bengaluru")
    key = ctx.get("key_skill_id", "kubernetes")
    has_key = key in ctx.get("must_skill_ids", [])

    if loc == "remote_india" and not has_key:
        return {
            "top_option_id": "mix",
            "panel_text": "Borrow C-17 (3 months) + Build E-045: available now, ₹18L in year one.",
            "options": [
                {
                    "option_id": "mix",
                    "name": "Recommended mix",
                    "score": 84.0,
                    "ready_by_p80_days": 0,
                    "year_one_cost_lpa": 18.0,
                    "panel_line": "",
                }
            ],
        }
    if loc == "remote_india":
        p50 = market_ctx.get("ttf_p50", 28)
        pay = market_ctx.get("pay_p50", 29.0)
        return {
            "top_option_id": "relocate",
            "panel_text": f"Relocate: Remote-India, P50 {p50} days, ₹{pay}L.",
            "options": [
                {
                    "option_id": "relocate",
                    "name": "Relocate",
                    "score": 64.0,
                    "ready_by_p80_days": market_ctx.get("ttf_p80", 40),
                    "year_one_cost_lpa": pay,
                    "panel_line": "",
                }
            ],
        }
    p50 = market_ctx.get("ttf_p50", 62)
    pay = market_ctx.get("pay_p50", 32.0)
    return {
        "top_option_id": "buy",
        "panel_text": f"Buy: P50 {p50} days, ₹{pay}L.",
        "options": [
            {
                "option_id": "buy",
                "name": "Buy",
                "score": 41.0,
                "ready_by_p80_days": 81,
                "year_one_cost_lpa": 32.0,
                "panel_line": "",
            }
        ],
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def generate():
    seed_main()


@pytest.fixture(scope="module")
def store():
    return DataStore()


@pytest.fixture(scope="module")
def result(store):
    fields, _ = regex_parse(
        DEMO_TEXT,
        store.reference.skills(),
        store.reference.skill_aliases(),
    )
    return analyze_redline(
        fields,
        DEMO_TEXT,
        store.ats.candidates(),
        store.ats.candidate_skills(),
        store.hris.employees(),
        store.hris.employee_skills(),
        store.vms.contractors(),
        store.vms.contractor_skills(),
        store.reference.skill_edges(),
        store.market.market_stats(),
        {},
        _stub_scorer,
        TODAY,
    )


# ── TC04: five marks, severities, spans ──────────────────────────────────────

def test_tc04_five_marks(result):
    assert len(result["constraints"]) == 5


def test_tc04_severities(result):
    by_kind = {c["kind"]: c["severity"] for c in result["constraints"]}
    assert by_kind["location"] == "red"
    assert by_kind["years"] == "amber"
    assert by_kind["skill"] == "red"
    assert by_kind["budget"] == "amber"
    assert by_kind["deadline"] == "red"


def test_tc04_spans_match_raw_text(result):
    for c in result["constraints"]:
        s, e, phrase = c["span_start"], c["span_end"], c["phrase"]
        assert DEMO_TEXT[s:e] == phrase, (
            f"kind={c['kind']}: DEMO_TEXT[{s}:{e}]={DEMO_TEXT[s:e]!r} != phrase={phrase!r}"
        )


def test_tc04_constraint_order(result):
    assert result["constraint_order"] == CONSTRAINT_ORDER


# ── TC05: relax Kubernetes only → supply 14 → 47 ─────────────────────────────

def test_tc05_relax_kubernetes_supply(result):
    skill_c = next(c for c in result["constraints"] if c["kind"] == "skill")
    assert skill_c["cost"]["supply_delta"] == 33, (
        f"Expected supply_delta 33 (47-14); got {skill_c['cost']['supply_delta']}"
    )


def test_tc05_supply_no_key_is_47(result):
    skill_c = next(c for c in result["constraints"] if c["kind"] == "skill")
    assert skill_c["hover_data"]["supply_no_key"] == 47


def test_tc05_kubernetes_is_key_skill(result):
    skill_c = next(c for c in result["constraints"] if c["kind"] == "skill")
    assert skill_c["id"] == "c-skill-kubernetes"


# ── TC06: relax location only → Remote-India 210, P50 28 ─────────────────────

def test_tc06_remote_supply(result):
    loc_c = next(c for c in result["constraints"] if c["kind"] == "location")
    assert loc_c["hover_data"]["remote_supply"] == 210


def test_tc06_remote_p50(result):
    loc_c = next(c for c in result["constraints"] if c["kind"] == "location")
    assert loc_c["hover_data"]["remote_p50"] == 28


# ── TC08: determinism ─────────────────────────────────────────────────────────

def test_tc08_determinism(store):
    fields, _ = regex_parse(
        DEMO_TEXT, store.reference.skills(), store.reference.skill_aliases()
    )
    kwargs = dict(
        raw_text=DEMO_TEXT,
        candidates_df=store.ats.candidates(),
        candidate_skills=store.ats.candidate_skills(),
        employees_df=store.hris.employees(),
        emp_skills=store.hris.employee_skills(),
        contractors_df=store.vms.contractors(),
        ctr_skills=store.vms.contractor_skills(),
        skill_edges_df=store.reference.skill_edges(),
        market_stats_df=store.market.market_stats(),
        dejareq_result={},
        score_options_fn=_stub_scorer,
        today=TODAY,
    )
    r1 = analyze_redline(fields, **kwargs)
    r2 = analyze_redline(fields, **kwargs)
    assert r1["scenarios"]["00000"] == r2["scenarios"]["00000"]
    assert r1["scenarios"]["11111"] == r2["scenarios"]["11111"]
    assert r1["scenarios"]["10100"] == r2["scenarios"]["10100"]


# ── 32 scenario keys ──────────────────────────────────────────────────────────

def test_32_scenario_keys(result):
    assert len(result["scenarios"]) == 32
    expected = {format(i, "05b") for i in range(32)}
    assert set(result["scenarios"].keys()) == expected


def test_scenario_00000_top_is_buy(result):
    assert result["scenarios"]["00000"]["top_option_id"] == "buy"


def test_scenario_10100_top_is_mix(result):
    # location + skill relaxed → mix (Borrow + Build)
    assert result["scenarios"]["10100"]["top_option_id"] == "mix"


# ── Performance < 1 s per call ────────────────────────────────────────────────

def test_performance(store):
    fields, _ = regex_parse(
        DEMO_TEXT, store.reference.skills(), store.reference.skill_aliases()
    )
    kwargs = dict(
        raw_text=DEMO_TEXT,
        candidates_df=store.ats.candidates(),
        candidate_skills=store.ats.candidate_skills(),
        employees_df=store.hris.employees(),
        emp_skills=store.hris.employee_skills(),
        contractors_df=store.vms.contractors(),
        ctr_skills=store.vms.contractor_skills(),
        skill_edges_df=store.reference.skill_edges(),
        market_stats_df=store.market.market_stats(),
        dejareq_result={},
        score_options_fn=_stub_scorer,
        today=TODAY,
    )
    t0 = time.perf_counter()
    for _ in range(5):
        analyze_redline(fields, **kwargs)
    elapsed = time.perf_counter() - t0
    avg = elapsed / 5
    assert avg < 1.0, f"Average call time {avg:.2f}s >= 1.0s"


# ── Hover numbers equal engine values ────────────────────────────────────────

def test_hover_skill_numbers(result):
    skill_c = next(c for c in result["constraints"] if c["kind"] == "skill")
    d = skill_c["hover_data"]
    assert d["supply_no_key"] == 47
    assert d["supply_base"] == 14
    assert d["pct_removed"] == 70
    assert d["contractor_id"] == "C-17"
    assert d["weeks_remaining"] == 4


def test_hover_location_numbers(result):
    loc_c = next(c for c in result["constraints"] if c["kind"] == "location")
    d = loc_c["hover_data"]
    assert d["supply_base"] == 14
    assert d["remote_supply"] == 210
    assert d["remote_p50"] == 28


def test_hover_budget_numbers(result):
    bud_c = next(c for c in result["constraints"] if c["kind"] == "budget")
    d = bud_c["hover_data"]
    assert d["market_p50"] == pytest.approx(32.0)
    assert d["pct_below"] == pytest.approx(12.5)
    assert d["ttf_mult"] == pytest.approx(1.25, abs=0.05)


def test_hover_deadline_numbers(result):
    dl_c = next(c for c in result["constraints"] if c["kind"] == "deadline")
    d = dl_c["hover_data"]
    assert d["buy_p80"] == 81
    assert d["remote_p80"] == 40


def test_hover_years_numbers(result):
    yr_c = next(c for c in result["constraints"] if c["kind"] == "years")
    d = yr_c["hover_data"]
    assert d["build_count_5plus"] == 1
    assert d["top_emp_id"] == "E-031"
    assert d["build_count_3plus"] == 4
    assert d["extra_at_3plus"] == 3


# ── Assumption ledger ─────────────────────────────────────────────────────────

def test_assumption_ledger_entries(result):
    ledger = result["assumption_ledger"]
    assert len(ledger["entries"]) == 5
    kinds = [e["kind"] for e in ledger["entries"]]
    assert kinds == CONSTRAINT_ORDER


def test_decision_boundaries_present(result):
    boundaries = result["assumption_ledger"]["decision_boundaries"]
    assert len(boundaries) >= 1
    assert all(isinstance(b, str) and len(b) > 0 for b in boundaries)
