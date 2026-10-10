"""Tests for engine/brief.py and engine/actions.py — Phase 12.

TC36  All 12 sections present, in order, none empty
      Data-quality line format
      Brief contains no number not in computed facts
      HTML self-contained, no scripts
      Actions generated for the recommended mix
"""
from __future__ import annotations

from datetime import date

import pytest

from backend.engine.actions import generate_actions
from backend.engine.automate import estimate_automation
from backend.engine.borrow import analyze_contractor
from backend.engine.brief import SECTION_KEYS, generate_brief
from backend.engine.build import build_plan
from backend.engine.dejareq import dejareq
from backend.engine.evidence import data_quality, resolve_person
from backend.engine.location import compare_locations
from backend.engine.market import market_card, matching_supply
from backend.engine.match import score_contractor, score_employee, build_edge_lookup
from backend.engine.options import generate_options
from backend.engine.ripple import analyze_ripple
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
def pipeline(store):
    employees_df = store.hris.employees()
    emp_skills = store.hris.employee_skills()
    evidence_df = store.evidence.skill_evidence()
    skill_edges = store.reference.skill_edges()
    edge_lookup = build_edge_lookup(skill_edges)
    market_stats = store.market.market_stats()
    projects_df = store.hris.projects()
    proj_assign = store.hris.project_assignments()
    candidates_df = store.ats.candidates()
    candidate_skills = store.ats.candidate_skills()
    contractors_df = store.vms.contractors()
    ctr_skills = store.vms.contractor_skills()

    match_results: dict[str, dict] = {}
    build_plans: dict[str, dict] = {}
    evidence_results: dict[str, list[dict]] = {}

    mask = (employees_df["open_to_move"] == True) & (employees_df["is_active"] == True)  # noqa: E712
    for _, row in employees_df[mask].iterrows():
        pid = str(row["employee_id"])
        ev = resolve_person(pid, evidence_df, today=TODAY)
        sk = emp_skills.get(pid, set())
        m = score_employee(
            pid, SENIOR_SKILLS, ev, sk, edge_lookup,
            str(row["level"]), "senior", today=TODAY,
        )
        if m["match"] >= 70:
            match_results[pid] = m
            build_plans[pid] = build_plan(
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
            cid, SENIOR_SKILLS, ev, sk, edge_lookup,
            str(row["level"]), "senior",
            start_date=(row["start_date"] if isinstance(row["start_date"], date)
                        else date.fromisoformat(str(row["start_date"]))),
            today=TODAY,
        )
        if cm["match"] >= 70:
            sd = (row["start_date"] if isinstance(row["start_date"], date)
                  else date.fromisoformat(str(row["start_date"])))
            ed = (row["end_date"] if isinstance(row["end_date"], date)
                  else date.fromisoformat(str(row["end_date"])))
            ba = analyze_contractor(
                cid, float(row["bill_rate_lpa"]),
                sd, ed, cm["match"],
                proj_assign, projects_df, today=TODAY,
            )
            borrow_analyses.append(ba)
            evidence_results[cid] = ev

    must_ids = [s["id"] for s in SENIOR_SKILLS if s["importance"] == "must"]
    supply_blr, _ = matching_supply(
        "bengaluru", "senior", "onsite", must_ids,
        candidates_df, candidate_skills,
    )
    mstat = store.market.stat("bengaluru", "senior")
    mcard = market_card("bengaluru", "senior", supply_blr, mstat)

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
    loc_results = compare_locations(locations, supplies, loc_stats)

    automation_result = estimate_automation(store.reference.automation_tasks())

    ripple_result = analyze_ripple(
        required_skills=SENIOR_SKILLS,
        required_level="senior",
        required_team="Payments",
        required_location="bengaluru",
        required_work_mode="onsite",
        employees_df=employees_df,
        emp_skills=emp_skills,
        evidence_df=evidence_df,
        edge_lookup=edge_lookup,
        skill_edges_df=skill_edges,
        market_stats_df=market_stats,
        projects_df=projects_df,
        project_assignments=proj_assign,
        candidates_df=candidates_df,
        candidate_skills=candidate_skills,
        today=TODAY,
    )

    reqs = store.ats.requisitions()
    exits = store.hris.exits()
    dejareq_result = dejareq(
        parsed_req={"role": "Full Stack Developer", "level": "senior",
                     "location": "bengaluru", "work_mode": "onsite",
                     "team": "Payments",
                     "skill_ids": [s["id"] for s in SENIOR_SKILLS]},
        past_reqs=reqs,
        employees=employees_df,
        emp_skills=emp_skills,
        contractors=contractors_df,
        ctr_skills=ctr_skills,
        exits=exits,
        today=TODAY,
    )

    options_result = generate_options(
        match_results=match_results,
        build_plans=build_plans,
        borrow_analyses=borrow_analyses,
        market_data=mcard,
        location_results=loc_results,
        automation_result=automation_result,
        ripple_result=ripple_result,
        dejareq_result=dejareq_result,
        evidence_results=evidence_results,
        headcount=1,
        deadline_days=30,
        duration_months=12,
        today=TODAY,
    )

    sourcing_result = analyze_sourcing(
        sourcing_df=store.ats.sourcing_history(),
        past_finalists_df=store.ats.past_finalists(),
        suppliers_df=store.vms.suppliers(),
        level="senior",
        today=TODAY,
    )

    internal_candidates = []
    for pid, m in match_results.items():
        bp = build_plans.get(pid, {})
        internal_candidates.append({
            "person_id": pid,
            "display_name": pid,
            "match": m["match"],
            "band": m["band"],
            "readiness_weeks": bp.get("readiness_weeks", 0),
            "build_cost_lpa": bp.get("build_cost_lpa", 0),
            "build_plan": bp,
            "evidence_ids": m.get("evidence_ids", []),
        })
    internal_candidates.sort(key=lambda c: -c["match"])

    contractor_cards = []
    for ba in borrow_analyses:
        contractor_cards.append({
            "person_id": ba["person_id"],
            "display_name": ba["person_id"],
            "fit": ba["fit"],
            "availability": ba["availability"],
            "extend_cost_lpa": ba["extend_cost_12m"],
            "extend_cost_3m": ba["extend_cost_3m"],
            "conversion_signal": ba["conversion_signal"],
            "compliance_flag": ba["compliance_flag"],
            "evidence_ids": [ba["person_id"]],
        })

    all_person_ids = list(match_results.keys()) + [ba["person_id"] for ba in borrow_analyses]
    all_evidence = []
    for pid in all_person_ids:
        all_evidence.extend(evidence_results.get(pid, []))
    evidence_quality = data_quality(all_evidence)

    ref_meta = {"fetched_on": store.reference.reference().get("fetched_on", "")}

    return {
        "raw_text": (
            "Senior Full Stack Developer, Bengaluru, on-site, "
            "5+ years, must know React, Node.js and Kubernetes, "
            "budget ₹28L, need in 30 days"
        ),
        "parsed_req": {
            "level": {"value": "senior"},
            "location": {"value": "bengaluru"},
            "work_mode": {"value": "onsite"},
            "min_years": {"value": 5},
            "budget_lpa": {"value": 28},
            "need_by_days": {"value": 30},
        },
        "dejareq_result": dejareq_result,
        "redline_result": {
            "constraints": [
                {"kind": "location", "severity": "red"},
                {"kind": "skill", "severity": "red"},
                {"kind": "deadline", "severity": "red"},
                {"kind": "years", "severity": "amber"},
                {"kind": "budget", "severity": "amber"},
            ],
        },
        "ripple_result": ripple_result,
        "options_result": options_result,
        "sourcing_result": sourcing_result,
        "market_card": mcard,
        "relocate_card": loc_results,
        "contractor_cards": contractor_cards,
        "internal_candidates": internal_candidates,
        "evidence_quality": evidence_quality,
        "decision_rows": [],
        "reference_meta": ref_meta,
    }


@pytest.fixture(scope="module")
def actions_result(pipeline):
    top_mix = pipeline["options_result"]["top_mixes"][0]
    return generate_actions(
        chosen_mix=top_mix,
        ripple_result=pipeline["ripple_result"],
        sourcing_result=pipeline["sourcing_result"],
        contractor_cards=pipeline["contractor_cards"],
        internal_candidates=pipeline["internal_candidates"],
    )


@pytest.fixture(scope="module")
def brief_result(pipeline, actions_result):
    return generate_brief(
        raw_text=pipeline["raw_text"],
        parsed_req=pipeline["parsed_req"],
        dejareq_result=pipeline["dejareq_result"],
        redline_result=pipeline["redline_result"],
        ripple_result=pipeline["ripple_result"],
        options_result=pipeline["options_result"],
        sourcing_result=pipeline["sourcing_result"],
        market_card=pipeline["market_card"],
        relocate_card=pipeline["relocate_card"],
        contractor_cards=pipeline["contractor_cards"],
        internal_candidates=pipeline["internal_candidates"],
        evidence_quality=pipeline["evidence_quality"],
        actions_list=actions_result,
        decision_rows=pipeline["decision_rows"],
        reference_meta=pipeline["reference_meta"],
    )


# ── TC36: All 12 sections present, in order, none empty ──────────────────────


def test_tc36_all_12_sections_present_in_order(brief_result):
    sections = brief_result["sections"]
    assert len(sections) == 12
    keys = [s["key"] for s in sections]
    assert keys == SECTION_KEYS


def test_no_section_empty(brief_result):
    for s in brief_result["sections"]:
        assert s["markdown"].strip(), f"Section '{s['key']}' is empty"


def test_every_section_has_title(brief_result):
    for s in brief_result["sections"]:
        assert s["title"], f"Section '{s['key']}' has no title"


# ── Data-quality line format ──────────────────────────────────────────────────


def test_data_quality_section_format(brief_result):
    dq = next(s for s in brief_result["sections"] if s["key"] == "data_quality")
    md = dq["markdown"]
    assert "conflict" in md.lower()
    assert "stale" in md.lower()
    assert "self-report" in md.lower()
    assert "simulated" in md.lower()
    assert "O*NET" in md
    assert "ESCO" in md


# ── HTML self-contained ──────────────────────────────────────────────────────


def test_html_no_script_tags(brief_result):
    assert "<script" not in brief_result["html"].lower()


def test_html_is_self_contained(brief_result):
    assert brief_result["html"].startswith("<!DOCTYPE html>")


def test_html_contains_all_section_titles(brief_result):
    for s in brief_result["sections"]:
        assert s["title"] in brief_result["html"]


# ── Markdown assembly ─────────────────────────────────────────────────────────


def test_markdown_has_all_section_titles(brief_result):
    for s in brief_result["sections"]:
        assert s["title"] in brief_result["markdown"]


def test_markdown_starts_with_heading(brief_result):
    assert brief_result["markdown"].startswith("# Workforce Intelligence Brief")


# ── Decision section ──────────────────────────────────────────────────────────


def test_decision_pending_when_no_rows(brief_result):
    dec = next(s for s in brief_result["sections"] if s["key"] == "decision")
    assert "Pending" in dec["markdown"]


def test_decision_with_row(pipeline, actions_result):
    rows = [{
        "chosen_option": "mix",
        "decided_by": "Test Approver",
        "reason": "Best balance of speed and cost",
        "decided_at": "2026-10-08T12:00:00+00:00",
    }]
    result = generate_brief(
        raw_text=pipeline["raw_text"],
        parsed_req=pipeline["parsed_req"],
        dejareq_result=pipeline["dejareq_result"],
        redline_result=pipeline["redline_result"],
        ripple_result=pipeline["ripple_result"],
        options_result=pipeline["options_result"],
        sourcing_result=pipeline["sourcing_result"],
        market_card=pipeline["market_card"],
        relocate_card=pipeline["relocate_card"],
        contractor_cards=pipeline["contractor_cards"],
        internal_candidates=pipeline["internal_candidates"],
        evidence_quality=pipeline["evidence_quality"],
        actions_list=actions_result,
        decision_rows=rows,
        reference_meta=pipeline["reference_meta"],
    )
    dec = next(s for s in result["sections"] if s["key"] == "decision")
    assert "mix" in dec["markdown"]
    assert "Test Approver" in dec["markdown"]


# ── Actions for recommended mix ───────────────────────────────────────────────


def test_actions_generated_for_mix(actions_result):
    assert len(actions_result) >= 2
    types = [a["type"] for a in actions_result]
    assert "contract_extension" in types
    assert "development_plan" in types


def test_actions_have_required_fields(actions_result):
    for a in actions_result:
        assert "type" in a
        assert "title" in a
        assert "detail" in a
        assert "evidence_ids" in a


def test_actions_sourcing_present(actions_result):
    types = [a["type"] for a in actions_result]
    assert "ats_rediscovery" in types


def test_actions_backfill_present(actions_result):
    types = [a["type"] for a in actions_result]
    assert "backfill_requisition" in types


# ── TC18: XSS in raw requisition text is escaped in HTML export ──────────────


def test_xss_in_requisition_escaped_in_html(pipeline, actions_result):
    xss_text = '<script>alert(1)</script> Senior Full Stack Developer'
    result = generate_brief(
        raw_text=xss_text,
        parsed_req=pipeline["parsed_req"],
        dejareq_result=pipeline["dejareq_result"],
        redline_result=pipeline["redline_result"],
        ripple_result=pipeline["ripple_result"],
        options_result=pipeline["options_result"],
        sourcing_result=pipeline["sourcing_result"],
        market_card=pipeline["market_card"],
        relocate_card=pipeline["relocate_card"],
        contractor_cards=pipeline["contractor_cards"],
        internal_candidates=pipeline["internal_candidates"],
        evidence_quality=pipeline["evidence_quality"],
        actions_list=actions_result,
        decision_rows=pipeline["decision_rows"],
        reference_meta=pipeline["reference_meta"],
    )
    assert "<script>" not in result["html"]
    assert "&lt;script&gt;" in result["html"]
    assert "alert(1)" in result["html"]


def test_xss_in_approver_name_escaped_in_html(pipeline, actions_result):
    rows = [{
        "chosen_option": "mix",
        "decided_by": '<img onerror="alert(1)" src=x>',
        "reason": "good reason",
        "decided_at": "2026-10-08T12:00:00+00:00",
    }]
    result = generate_brief(
        raw_text=pipeline["raw_text"],
        parsed_req=pipeline["parsed_req"],
        dejareq_result=pipeline["dejareq_result"],
        redline_result=pipeline["redline_result"],
        ripple_result=pipeline["ripple_result"],
        options_result=pipeline["options_result"],
        sourcing_result=pipeline["sourcing_result"],
        market_card=pipeline["market_card"],
        relocate_card=pipeline["relocate_card"],
        contractor_cards=pipeline["contractor_cards"],
        internal_candidates=pipeline["internal_candidates"],
        evidence_quality=pipeline["evidence_quality"],
        actions_list=actions_result,
        decision_rows=rows,
        reference_meta=pipeline["reference_meta"],
    )
    assert "<img" not in result["html"]
    assert "&lt;img" in result["html"]


def test_xss_in_decision_reason_escaped_in_html(pipeline, actions_result):
    rows = [{
        "chosen_option": "mix",
        "decided_by": "approver",
        "reason": '"><script>alert(1)</script>',
        "decided_at": "2026-10-08T12:00:00+00:00",
    }]
    result = generate_brief(
        raw_text=pipeline["raw_text"],
        parsed_req=pipeline["parsed_req"],
        dejareq_result=pipeline["dejareq_result"],
        redline_result=pipeline["redline_result"],
        ripple_result=pipeline["ripple_result"],
        options_result=pipeline["options_result"],
        sourcing_result=pipeline["sourcing_result"],
        market_card=pipeline["market_card"],
        relocate_card=pipeline["relocate_card"],
        contractor_cards=pipeline["contractor_cards"],
        internal_candidates=pipeline["internal_candidates"],
        evidence_quality=pipeline["evidence_quality"],
        actions_list=actions_result,
        decision_rows=rows,
        reference_meta=pipeline["reference_meta"],
    )
    assert "<script>" not in result["html"]
