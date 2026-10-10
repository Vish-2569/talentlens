"""Tests for engine/dejareq.py — Deja Req past-requisition analysis."""
import pytest
import pandas as pd
from datetime import date

from backend.engine.dejareq import dejareq

TODAY = date(2026, 10, 8)

# Demo skills match the Section 13 story: React, Node.js, Kubernetes (3 skills).
# Standard Jaccard compares against PastRequisition.skills column, not person skills.
DEMO_PARSED_REQ = {
    "role": "Full Stack Developer",
    "level": "senior",
    "team": "Payments",
    "location": "bengaluru",
    "work_mode": "onsite",
    "skill_ids": ["react", "nodejs", "kubernetes"],
}

JUNIOR_PARSED_REQ = {
    "role": "Full Stack Developer",
    "level": "junior",
    "team": "Payments",
    "location": "bengaluru",
    "work_mode": "onsite",
    "skill_ids": ["react", "nodejs", "javascript", "html_css", "git"],
}


def _run(store, parsed_req):
    return dejareq(
        parsed_req=parsed_req,
        past_reqs=store.ats.requisitions(),
        employees=store.hris.employees(),
        emp_skills=store.hris.employee_skills(),
        contractors=store.vms.contractors(),
        ctr_skills=store.vms.contractor_skills(),
        exits=store.hris.exits(),
        today=TODAY,
    )


# ── TC01: Demo requisition → banner, 4 timeline rows ───────────────


def test_demo_banner_4_times(store):
    result = _run(store, DEMO_PARSED_REQ)
    assert "4 times in the last 2 years" in result["banner"]


def test_demo_4_timeline_rows(store):
    result = _run(store, DEMO_PARSED_REQ)
    assert len(result["timeline"]) == 4


def test_demo_timeline_newest_first(store):
    result = _run(store, DEMO_PARSED_REQ)
    dates = [t["opened_date"] for t in result["timeline"]]
    assert dates == ["2026-06-01", "2026-03-01", "2025-10-01", "2024-11-05"]


def test_demo_timeline_evidence_ids(store):
    result = _run(store, DEMO_PARSED_REQ)
    for row in result["timeline"]:
        assert len(row["evidence_ids"]) > 0


# ── TC02: Junior requisition → no banner ────────────────────────────


def test_junior_no_banner(store):
    result = _run(store, JUNIOR_PARSED_REQ)
    assert "banner" not in result
    assert result["match_count"] == 0


# ── TC03: Churn, knowledge loss, cost story ─────────────────────────


def test_avg_external_tenure_8_months(store):
    result = _run(store, DEMO_PARSED_REQ)
    assert result["averages"]["buy"]["avg_tenure_months"] == 8


def test_churn_detected(store):
    result = _run(store, DEMO_PARSED_REQ)
    assert result["patterns"]["churn"] is True


def test_buy_risk_plus_020(store):
    result = _run(store, DEMO_PARSED_REQ)
    buy_adj = next(a for a in result["risk_adjustments"]
                   if a["option"] == "buy")
    assert buy_adj["delta"] == 0.20


def test_knowledge_loss_detected(store):
    result = _run(store, DEMO_PARSED_REQ)
    assert result["patterns"]["knowledge_loss"] is True


def test_borrow_risk_plus_010(store):
    result = _run(store, DEMO_PARSED_REQ)
    borrow_adj = next(a for a in result["risk_adjustments"]
                      if a["option"] == "borrow")
    assert borrow_adj["delta"] == 0.10


def test_cost_story_64_vs_4(store):
    result = _run(store, DEMO_PARSED_REQ)
    cs = result["cost_story"]
    assert cs["buy_total_lpa"] == 64.0
    assert cs["build_total_lpa"] == 4.0
    assert cs["difference_lpa"] == 60.0


def test_jun_2026_outcome_still_in_role(store):
    result = _run(store, DEMO_PARSED_REQ)
    jun_row = result["timeline"][0]
    assert jun_row["req_id"] == "REQ-004"
    assert jun_row["outcome"] == "Still in role, rated Exceeds"


def test_insight_text(store):
    result = _run(store, DEMO_PARSED_REQ)
    expected = (
        "Pattern: external hires for this role left in under a year "
        "(average 8 months, 2 of 2). "
        "The one internal move is still in role. "
        "This requisition implies Buy. "
        "Your own history says that hasn't worked."
    )
    assert result["insight"] == expected


def test_what_worked_is_build(store):
    result = _run(store, DEMO_PARSED_REQ)
    assert result["patterns"]["what_worked"] == "build"


# ── TC04: Low-overlap past requisition must NOT match ───────────────


def test_low_overlap_req_no_match(store):
    """A past req sharing only 1 of 3 required skills (Jaccard = 1/3 < 0.5) must not match."""
    low_overlap_reqs = pd.DataFrame([{
        "req_id": "REQ-X01",
        "role": "Full Stack Developer",
        "level": "senior",
        "team": "Payments",
        "location": "bengaluru",
        "work_mode": "onsite",
        "opened_date": "2026-06-01",
        "closed_date": "2026-06-30",
        "decision": "buy",
        "outcome": "still_in_role",
        "person_id": "E-010",
        "time_to_fill_days": 29,
        "first_year_cost_lpa": 31.0,
        "skills": "react",   # only 1 of 3 required skills → Jaccard = 1/3 < 0.5
    }])
    result = dejareq(
        parsed_req=DEMO_PARSED_REQ,
        past_reqs=low_overlap_reqs,
        employees=store.hris.employees(),
        emp_skills=store.hris.employee_skills(),
        contractors=store.vms.contractors(),
        ctr_skills=store.vms.contractor_skills(),
        exits=store.hris.exits(),
        today=TODAY,
    )
    assert result["match_count"] == 0
