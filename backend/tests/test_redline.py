"""Tests for engine/redline.py — Requisition Redline.

TC04  5 marks, correct severities (3 red, 2 amber), spans match raw text
TC05  relax Kubernetes only → supply 14 → 47 (supply_delta == 33)
TC06  relax location only  → Remote-India 210, P50 28
TC08  same inputs twice    → identical scenario output (determinism)
      32 scenario keys
      total compute < 2 s per call (real M8 scorer)
      every hover number equals an engine value
      mask 00000 panel text contains "Buy" and "P50 62 days"
      location + Kubernetes relaxed → Borrow + Build mix, ₹18L
      decision boundaries non-empty
"""
from __future__ import annotations

import time
from datetime import date

import pytest

from backend.engine.automate import estimate_automation
from backend.engine.borrow import analyze_contractor
from backend.engine.build import build_plan
from backend.engine.dejareq import dejareq
from backend.engine.evidence import resolve_person
from backend.engine.location import compare_locations
from backend.engine.market import matching_supply, market_card
from backend.engine.match import score_employee, score_contractor
from backend.engine.options import make_scenario_scorer
from backend.engine.parser import regex_parse
from backend.engine.redline import CONSTRAINT_ORDER, analyze_redline
from backend.engine.ripple import analyze_ripple

TODAY = date(2026, 10, 8)

DEMO_TEXT = (
    "Senior Full Stack Developer, Bengaluru, on-site, 5+ years, "
    "must know React, Node.js and Kubernetes, budget ₹28L, need in 30 days"
)

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


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def real_scorer(store):
    employees_df = store.hris.employees()
    emp_skills = store.hris.employee_skills()
    evidence_df = store.evidence.skill_evidence()
    skill_edges = store.reference.skill_edges()
    market_stats = store.market.market_stats()
    projects_df = store.hris.projects()
    proj_assign = store.hris.project_assignments()
    candidates_df = store.ats.candidates()
    candidate_skills = store.ats.candidate_skills()
    contractors_df = store.vms.contractors()
    ctr_skills = store.vms.contractor_skills()

    match_results: dict[str, dict] = {}
    build_plans_d: dict[str, dict] = {}
    evidence_results: dict[str, list[dict]] = {}

    mask = (employees_df["open_to_move"] == True) & (employees_df["is_active"] == True)  # noqa: E712
    for _, row in employees_df[mask].iterrows():
        pid = str(row["employee_id"])
        ev = resolve_person(pid, evidence_df, today=TODAY)
        sk = emp_skills.get(pid, set())
        m = score_employee(
            pid, SENIOR_SKILLS, ev, sk, skill_edges,
            str(row["level"]), "senior", today=TODAY,
        )
        if m["match"] >= 70:
            match_results[pid] = m
            build_plans_d[pid] = build_plan(
                pid, ev, sk, SENIOR_SKILLS, skill_edges,
                str(row["level"]), "senior",
            )
            evidence_results[pid] = ev

    borrow_analyses: list[dict] = []
    for _, row in contractors_df.iterrows():
        cid = str(row["contractor_id"])
        ev = resolve_person(cid, evidence_df, today=TODAY)
        sk = ctr_skills.get(cid, set())
        cm = score_contractor(
            cid, SENIOR_SKILLS, ev, sk, skill_edges,
            str(row["level"]), "senior",
            start_date=(row["start_date"] if isinstance(row["start_date"], date)
                        else date.fromisoformat(str(row["start_date"]))),
            today=TODAY,
        )
        if cm["match"] >= 70:
            sd = row["start_date"] if isinstance(row["start_date"], date) else date.fromisoformat(str(row["start_date"]))
            ed = row["end_date"] if isinstance(row["end_date"], date) else date.fromisoformat(str(row["end_date"]))
            ba = analyze_contractor(
                cid, float(row["bill_rate_lpa"]), sd, ed,
                cm["match"], proj_assign, projects_df, today=TODAY,
            )
            borrow_analyses.append(ba)
            evidence_results[cid] = ev

    supply, _ = matching_supply(
        "bengaluru", "senior", "onsite",
        [s["id"] for s in SENIOR_SKILLS if s["importance"] == "must"],
        candidates_df, candidate_skills,
    )
    mstat = store.market.stat("bengaluru", "senior")
    mcard = market_card("bengaluru", "senior", supply, mstat)

    locations = ["bengaluru", "hyderabad", "pune", "remote_india"]
    supplies: dict[str, int] = {}
    for loc in locations:
        s, _ = matching_supply(
            loc, "senior",
            "remote" if loc == "remote_india" else "onsite",
            [sk["id"] for sk in SENIOR_SKILLS if sk["importance"] == "must"],
            candidates_df, candidate_skills,
        )
        supplies[loc] = s

    loc_stats = market_stats[market_stats["level"] == "senior"]
    loc_results = compare_locations(locations, supplies, loc_stats)
    automation_result = estimate_automation(store.reference.automation_tasks())

    ripple_result = analyze_ripple(
        required_skills=SENIOR_SKILLS, required_level="senior",
        required_team="Payments", required_location="bengaluru",
        required_work_mode="onsite", employees_df=employees_df,
        emp_skills=emp_skills, evidence_df=evidence_df,
        skill_edges_df=skill_edges, market_stats_df=market_stats,
        projects_df=projects_df, project_assignments=proj_assign,
        candidates_df=candidates_df, candidate_skills=candidate_skills,
        today=TODAY,
    )

    reqs = store.ats.requisitions()
    exits = store.hris.exits()
    dejareq_result = dejareq(
        parsed_req={"role": "Full Stack Developer", "level": "senior",
                     "location": "bengaluru", "work_mode": "onsite",
                     "team": "Payments",
                     "skill_ids": [s["id"] for s in SENIOR_SKILLS]},
        past_reqs=reqs, employees=employees_df, emp_skills=emp_skills,
        contractors=contractors_df, ctr_skills=ctr_skills,
        exits=exits, today=TODAY,
    )

    return make_scenario_scorer(
        match_results=match_results,
        build_plans=build_plans_d,
        borrow_analyses=borrow_analyses,
        location_results=loc_results,
        automation_result=automation_result,
        ripple_result=ripple_result,
        dejareq_result=dejareq_result,
        evidence_results=evidence_results,
        base_location="bengaluru",
        base_must_skill_ids=[s["id"] for s in SENIOR_SKILLS if s["importance"] == "must"],
        deadline_days=30,
        duration_months=12,
    )


@pytest.fixture(scope="module")
def result(store, real_scorer):
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
        real_scorer,
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

def test_tc08_determinism(store, real_scorer):
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
        score_options_fn=real_scorer,
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


def test_scenario_00000_panel_text(result):
    panel = result["scenarios"]["00000"]["panel_text"]
    assert "Buy" in panel or "buy" in panel
    assert "62" in panel
    assert "32" in panel


def test_scenario_10100_top_is_mix(result):
    assert result["scenarios"]["10100"]["top_option_id"] == "mix"


def test_scenario_10100_panel_has_18L(result):
    panel = result["scenarios"]["10100"]["panel_text"]
    assert "18" in panel


# ── Performance < 2 s per call (real scorer) ─────────────────────────────────

def test_performance(store, real_scorer):
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
        score_options_fn=real_scorer,
        today=TODAY,
    )
    t0 = time.perf_counter()
    for _ in range(3):
        analyze_redline(fields, **kwargs)
    elapsed = time.perf_counter() - t0
    avg = elapsed / 3
    assert avg < 2.0, f"Average call time {avg:.2f}s >= 2.0s"


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
