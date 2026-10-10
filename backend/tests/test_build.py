"""Tests for engine/build.py — upskill gap analysis and build chain costing."""
import pytest
from datetime import date

from backend.engine.evidence import resolve_person
from backend.engine.build import build_plan, build_chain_cost

TODAY = date(2026, 10, 8)

SENIOR_SKILLS = [
    {"id": "react", "importance": "must"},
    {"id": "nodejs", "importance": "must"},
    {"id": "kubernetes", "importance": "must"},
]


def _resolve(store, pid):
    ev_df = store.evidence.skill_evidence(person_id=pid)
    return resolve_person(pid, ev_df, today=TODAY)


def _emp_skills(store, pid):
    return store.hris.employee_skills().get(pid, set())


# ── Priya: 6 weeks readiness, 0.5L cost ─────────────────────────────


def test_priya_readiness_6_weeks(store):
    ev = _resolve(store, "E-045")
    sk = _emp_skills(store, "E-045")
    edges = store.reference.skill_edges()
    result = build_plan("E-045", ev, sk, SENIOR_SKILLS, edges, "mid", "senior")
    assert result["readiness_weeks"] == 6


def test_priya_build_cost_05(store):
    ev = _resolve(store, "E-045")
    sk = _emp_skills(store, "E-045")
    edges = store.reference.skill_edges()
    result = build_plan("E-045", ev, sk, SENIOR_SKILLS, edges, "mid", "senior")
    assert result["build_cost_lpa"] == 0.5


# ── Rahul: 12 weeks readiness ───────────────────────────────────────


def test_rahul_readiness_12_weeks(store):
    ev = _resolve(store, "E-072")
    sk = _emp_skills(store, "E-072")
    edges = store.reference.skill_edges()
    mid_skills = [
        {"id": "react", "importance": "must"},
        {"id": "nodejs", "importance": "must"},
        {"id": "kubernetes", "importance": "must"},
    ]
    result = build_plan("E-072", ev, sk, mid_skills, edges, "junior", "mid")
    assert result["readiness_weeks"] == 12


def test_rahul_build_cost(store):
    ev = _resolve(store, "E-072")
    sk = _emp_skills(store, "E-072")
    edges = store.reference.skill_edges()
    mid_skills = [
        {"id": "react", "importance": "must"},
        {"id": "nodejs", "importance": "must"},
        {"id": "kubernetes", "importance": "must"},
    ]
    result = build_plan("E-072", ev, sk, mid_skills, edges, "junior", "mid")
    assert result["build_cost_lpa"] == 0.5


# ── Build chain total = 12L ──────────────────────────────────────────


def test_build_chain_12L():
    result = build_chain_cost(
        junior_salary_lpa=7.0,
        raises_lpa=4.5,
        upskill_cost_lpa=0.5,
    )
    assert result["total_cost_lpa"] == 12.0
    assert result["breakdown"]["junior_hire"] == 7.0
    assert result["breakdown"]["raises"] == 4.5
    assert result["breakdown"]["upskill"] == 0.5


# ── Evidence IDs returned ────────────────────────────────────────────


def test_build_returns_evidence_ids(store):
    ev = _resolve(store, "E-045")
    sk = _emp_skills(store, "E-045")
    edges = store.reference.skill_edges()
    result = build_plan("E-045", ev, sk, SENIOR_SKILLS, edges, "mid", "senior")
    assert len(result["evidence_ids"]) > 0
