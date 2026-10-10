"""Tests for engine/match.py — internal match scoring."""
import pytest
from datetime import date

from backend.engine.evidence import resolve_person
from backend.engine.match import score_employee, score_contractor, band

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

MID_SKILLS = [
    {"id": "react", "importance": "must"},
    {"id": "nodejs", "importance": "must"},
    {"id": "typescript", "importance": "nice"},
    {"id": "javascript", "importance": "nice"},
    {"id": "html_css", "importance": "nice"},
    {"id": "git", "importance": "nice"},
    {"id": "jest", "importance": "nice"},
]


def _resolve(store, pid):
    ev_df = store.evidence.skill_evidence(person_id=pid)
    return resolve_person(pid, ev_df, today=TODAY)


def _emp_skills(store, pid):
    all_sk = store.hris.employee_skills()
    return all_sk.get(pid, set())


def _ctr_skills(store, pid):
    all_sk = store.vms.contractor_skills()
    return all_sk.get(pid, set())


# ── TC12: Karthik = 88, band "redeploy" ─────────────────────────────


def test_karthik_88(store):
    ev = _resolve(store, "E-031")
    sk = _emp_skills(store, "E-031")
    edges = store.reference.skill_edges()
    result = score_employee("E-031", SENIOR_SKILLS, ev, sk, edges,
                            "lead", "senior", today=TODAY)
    assert result["match"] == 88
    assert result["band"] == "redeploy"


# ── TC12: Priya = 82, band "Build" ──────────────────────────────────


def test_priya_82(store):
    ev = _resolve(store, "E-045")
    sk = _emp_skills(store, "E-045")
    edges = store.reference.skill_edges()
    result = score_employee("E-045", SENIOR_SKILLS, ev, sk, edges,
                            "mid", "senior", today=TODAY)
    assert result["match"] == 82
    assert result["band"] == "Build"


# ── TC12: Arjun = 84 ────────────────────────────────────────────────


def test_arjun_84(store):
    ev = _resolve(store, "C-17")
    sk = _ctr_skills(store, "C-17")
    edges = store.reference.skill_edges()
    result = score_contractor("C-17", SENIOR_SKILLS, ev, sk, edges,
                              "senior", "senior",
                              start_date=date(2025, 7, 1), today=TODAY)
    assert result["match"] == 84


# ── TC12: Rahul = 76 for mid ────────────────────────────────────────


def test_rahul_76_for_mid(store):
    ev = _resolve(store, "E-072")
    sk = _emp_skills(store, "E-072")
    edges = store.reference.skill_edges()
    result = score_employee("E-072", MID_SKILLS, ev, sk, edges,
                            "junior", "mid", today=TODAY)
    assert result["match"] == 76
    assert result["band"] == "Build"


# ── Must-have gate caps at 70 ───────────────────────────────────────


def test_must_have_gate_cap_70():
    import pandas as pd
    edges = pd.DataFrame(columns=["skill_a", "skill_b", "type", "weight"])
    ev = [{"skill": "react", "value": 90, "source": "assessment",
           "observed_on": "2026-06-01", "stale": False, "confidence": 1.0}]
    skills = {"react"}
    required = [
        {"id": "react", "importance": "must"},
        {"id": "nodejs", "importance": "must"},
    ]
    result = score_employee("T-99", required, ev, skills, edges,
                            "senior", "senior", today=TODAY)
    assert result["match"] <= 70


# ── Evidence IDs returned ────────────────────────────────────────────


def test_evidence_ids_returned(store):
    ev = _resolve(store, "E-031")
    sk = _emp_skills(store, "E-031")
    edges = store.reference.skill_edges()
    result = score_employee("E-031", SENIOR_SKILLS, ev, sk, edges,
                            "lead", "senior", today=TODAY)
    assert len(result["evidence_ids"]) > 0


# ── Band boundaries ─────────────────────────────────────────────────


def test_band_boundaries():
    assert band(85) == "redeploy"
    assert band(84) == "Build"
    assert band(70) == "Build"
    assert band(69) == "long-term pipeline"
    assert band(50) == "long-term pipeline"
    assert band(49) == "hidden"
