"""Tests for engine/options.py — option generation and scoring.

test_options_five_present            Five options with required fields
test_mix_duplicate_person_rejected   Mix using one person twice is dropped
test_weights_sum_to_one              Weights sum to 1.0 after shifting
TC29                                 Self-report-only must-have adds +0.05 risk
test_options_deterministic           Same input twice → identical output
test_ripple_red_flags_in_risk        Karthik's red flags raise atom risk above Priya's
"""
from __future__ import annotations

from datetime import date

import pytest

from backend.data.seed import main as seed_main
from backend.engine.borrow import analyze_contractor
from backend.engine.automate import estimate_automation
from backend.engine.dejareq import dejareq
from backend.engine.evidence import resolve_person
from backend.engine.location import compare_locations
from backend.engine.market import matching_supply, market_card
from backend.engine.match import score_employee, score_contractor
from backend.engine.build import build_plan
from backend.engine.options import (
    DEFAULT_WEIGHTS,
    _adjust_weights,
    _filter_mixes,
    _generate_atoms,
    _self_report_penalty,
    generate_options,
)
from backend.engine.ripple import analyze_ripple
from backend.store import DataStore

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


@pytest.fixture(scope="module", autouse=True)
def generate():
    seed_main()


@pytest.fixture(scope="module")
def store():
    return DataStore()


@pytest.fixture(scope="module")
def precomputed(store):
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
    build_plans: dict[str, dict] = {}
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
            cid, SENIOR_SKILLS, ev, sk, skill_edges,
            str(row["level"]), "senior",
            start_date=row["start_date"] if hasattr(row["start_date"], "date") else date.fromisoformat(str(row["start_date"])),
            today=TODAY,
        )
        if cm["match"] >= 70:
            sd = row["start_date"] if isinstance(row["start_date"], date) else date.fromisoformat(str(row["start_date"]))
            ed = row["end_date"] if isinstance(row["end_date"], date) else date.fromisoformat(str(row["end_date"]))
            ba = analyze_contractor(
                cid,
                float(row["bill_rate_lpa"]),
                sd, ed,
                cm["match"],
                proj_assign, projects_df,
                today=TODAY,
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
        required_skills=SENIOR_SKILLS,
        required_level="senior",
        required_team="Payments",
        required_location="bengaluru",
        required_work_mode="onsite",
        employees_df=employees_df,
        emp_skills=emp_skills,
        evidence_df=evidence_df,
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
                     "location": "bengaluru", "work_mode": "onsite"},
        past_reqs=reqs,
        employees=employees_df,
        emp_skills=emp_skills,
        contractors=contractors_df,
        ctr_skills=ctr_skills,
        exits=exits,
        today=TODAY,
    )

    return {
        "match_results": match_results,
        "build_plans": build_plans,
        "borrow_analyses": borrow_analyses,
        "market_data": mcard,
        "location_results": loc_results,
        "automation_result": automation_result,
        "ripple_result": ripple_result,
        "dejareq_result": dejareq_result,
        "evidence_results": evidence_results,
        "headcount": 1,
        "deadline_days": 30,
        "duration_months": 12,
    }


@pytest.fixture(scope="module")
def result(precomputed):
    return generate_options(**precomputed, today=TODAY)


# ── Five options present with required fields ────────────────────────────────


def test_options_five_present(result):
    assert len(result["options"]) == 5


def test_options_five_names(result):
    names = {o["name"] for o in result["options"]}
    assert names == {"Build", "Buy", "Borrow", "Relocate", "Automate"}


def test_options_required_fields(result):
    required = {
        "option_id", "name", "what_it_means", "ready_by_p80_days",
        "year_one_cost_lpa", "fit", "risk_label", "score",
        "one_line_reason", "evidence_ids",
    }
    for opt in result["options"]:
        missing = required - set(opt.keys())
        assert not missing, f"{opt['name']} missing fields: {missing}"


def test_options_time_is_int(result):
    for opt in result["options"]:
        assert isinstance(opt["ready_by_p80_days"], int), opt["name"]


def test_options_cost_is_numeric(result):
    for opt in result["options"]:
        assert isinstance(opt["year_one_cost_lpa"], (int, float)), opt["name"]


def test_options_fit_is_numeric(result):
    for opt in result["options"]:
        assert isinstance(opt["fit"], (int, float)), opt["name"]


def test_options_risk_label_valid(result):
    valid = {"Low", "Medium", "Medium-high", "High"}
    for opt in result["options"]:
        assert opt["risk_label"] in valid, f"{opt['name']}: {opt['risk_label']}"


def test_options_reason_nonempty(result):
    for opt in result["options"]:
        assert len(opt["one_line_reason"]) > 0, opt["name"]


def test_options_evidence_ids_are_list_of_str(result):
    for opt in result["options"]:
        assert isinstance(opt["evidence_ids"], list), opt["name"]
        for eid in opt["evidence_ids"]:
            assert isinstance(eid, str), f"{opt['name']}: {eid}"


def test_options_automate_score_is_addon(result):
    auto = next(o for o in result["options"] if o["name"] == "Automate")
    assert auto["score"] == "add-on"


def test_options_scored_are_int(result):
    for opt in result["options"]:
        if opt["name"] != "Automate":
            assert isinstance(opt["score"], int), f"{opt['name']}: {opt['score']}"


def test_options_top_mixes_capped_at_3(result):
    assert len(result["top_mixes"]) <= 3


def test_options_weights_used_present(result):
    w = result["weights_used"]
    assert set(w.keys()) == {"speed", "cost", "fit", "risk", "strategic"}


def test_options_assumption_ledger_present(result):
    ledger = result["assumption_ledger"]
    assert "self_report_risks" in ledger
    assert "dejareq_adjustments" in ledger
    assert "weight_shifts" in ledger


# ── Mix with duplicate person is rejected ────────────────────────────────────


def test_mix_duplicate_person_rejected():
    mixes = [
        [
            {"type": "redeploy", "person_id": "E-045", "location": None,
             "option_category": "build", "cost_lpa": 5.0, "days": 42,
             "fit": 0.82, "red_flags": 0, "evidence_ids": []},
            {"type": "build", "person_id": "E-045", "location": None,
             "option_category": "build", "cost_lpa": 3.0, "days": 42,
             "fit": 0.82, "red_flags": 0, "evidence_ids": []},
        ],
        [
            {"type": "redeploy", "person_id": "E-045", "location": None,
             "option_category": "build", "cost_lpa": 5.0, "days": 42,
             "fit": 0.82, "red_flags": 0, "evidence_ids": []},
            {"type": "extend", "person_id": "C-17", "location": None,
             "option_category": "borrow", "cost_lpa": 24.0, "days": 14,
             "fit": 0.84, "red_flags": 0, "evidence_ids": []},
        ],
    ]
    filtered = _filter_mixes(mixes, [])
    assert len(filtered) == 1
    pids = {a["person_id"] for a in filtered[0]}
    assert "E-045" in pids and "C-17" in pids


# ── Weights sum to 1.0 after shifting ────────────────────────────────────────


def test_weights_sum_to_one_default():
    w = _adjust_weights(dict(DEFAULT_WEIGHTS), deadline_days=90, duration_months=12)
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weights_sum_to_one_tight_deadline():
    w = _adjust_weights(dict(DEFAULT_WEIGHTS), deadline_days=30, duration_months=12)
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weights_sum_to_one_short_duration():
    w = _adjust_weights(dict(DEFAULT_WEIGHTS), deadline_days=90, duration_months=6)
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weights_sum_to_one_both():
    w = _adjust_weights(dict(DEFAULT_WEIGHTS), deadline_days=45, duration_months=5)
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weights_tight_deadline_boosts_speed():
    w_normal = _adjust_weights(dict(DEFAULT_WEIGHTS), deadline_days=90, duration_months=12)
    w_tight = _adjust_weights(dict(DEFAULT_WEIGHTS), deadline_days=30, duration_months=12)
    assert w_tight["speed"] > w_normal["speed"]


# ── TC29: Self-report-only must-have adds +0.05 risk ────────────────────────


def test_self_report_penalty_synthetic():
    evidence = {
        "E-999": [
            {"skill": "graphql", "source": "self", "ignored": [],
             "value": 39, "observed_on": "2025-02-15",
             "confidence": 0.35, "stale": False, "conflict": False},
        ],
    }
    penalty, entries = _self_report_penalty(["E-999"], evidence)
    assert penalty == 0.05
    assert len(entries) == 1
    assert entries[0]["person_id"] == "E-999"
    assert entries[0]["skill"] == "graphql"
    assert entries[0]["risk_delta"] == 0.05


def test_self_report_penalty_multiple():
    evidence = {
        "E-100": [
            {"skill": "graphql", "source": "self", "ignored": [],
             "value": 39, "observed_on": "2025-02-15",
             "confidence": 0.35, "stale": False, "conflict": False},
            {"skill": "vue", "source": "self", "ignored": [],
             "value": 42, "observed_on": "2025-03-10",
             "confidence": 0.35, "stale": False, "conflict": False},
        ],
    }
    penalty, entries = _self_report_penalty(["E-100"], evidence)
    assert penalty == 0.10
    assert len(entries) == 2


def test_self_report_penalty_not_triggered_with_other_sources():
    evidence = {
        "E-200": [
            {"skill": "react", "source": "assessment", "ignored": [
                {"source": "self", "value": 60, "reason": "lower trust"}
            ], "value": 75, "observed_on": "2026-01-10",
             "confidence": 0.9, "stale": False, "conflict": False},
        ],
    }
    penalty, entries = _self_report_penalty(["E-200"], evidence)
    assert penalty == 0.0
    assert len(entries) == 0


def test_self_report_in_ledger(result):
    ledger = result["assumption_ledger"]["self_report_risks"]
    for entry in ledger:
        assert entry["risk_delta"] == 0.05
        assert "person_id" in entry
        assert "skill" in entry


# ── Ripple red flags in risk (bus factor, red dead-end nodes) ────────────────


def test_ripple_red_flags_on_atoms(precomputed):
    """Karthik (E-031) has red flags from ripple; Priya (E-045) has none.
    The atom for Karthik must carry higher red_flags than Priya's."""
    atoms = _generate_atoms(
        match_results=precomputed["match_results"],
        build_plans=precomputed["build_plans"],
        borrow_analyses=precomputed["borrow_analyses"],
        location_results=precomputed["location_results"],
        automation_result=precomputed["automation_result"],
        market_data=precomputed["market_data"],
        ripple_result=precomputed["ripple_result"],
    )
    build_atoms = {a["person_id"]: a for a in atoms
                   if a["type"] in ("build", "redeploy") and a["person_id"]}

    karthik = build_atoms.get("E-031")
    priya = build_atoms.get("E-045")

    assert karthik is not None, "Karthik should produce an atom"
    assert priya is not None, "Priya should produce an atom"
    assert karthik["red_flags"] > 0, "Karthik must have ripple red flags"
    assert karthik["red_flags"] > priya["red_flags"], (
        f"Karthik red_flags ({karthik['red_flags']}) must exceed "
        f"Priya's ({priya['red_flags']})"
    )


def test_ripple_red_flags_increase_mix_risk():
    """A mix containing a high-red-flag atom scores higher risk_raw
    than an identical mix with zero red flags."""
    from backend.engine.options import _score_mixes

    base_atom = {
        "type": "build", "person_id": "E-045", "location": None,
        "option_category": "build", "cost_lpa": 12.0, "days": 42,
        "fit": 0.82, "red_flags": 0, "evidence_ids": ["react"],
    }
    flagged_atom = {**base_atom, "person_id": "E-031", "red_flags": 3}

    w = dict(DEFAULT_WEIGHTS)
    total = sum(w.values())
    w = {k: v / total for k, v in w.items()}

    scored_clean = _score_mixes([[base_atom]], w, {}, [])
    scored_flagged = _score_mixes([[flagged_atom]], w, {}, [])

    assert scored_flagged[0]["risk"] > scored_clean[0]["risk"]
    assert scored_flagged[0]["score"] < scored_clean[0]["score"]


# ── Determinism ──────────────────────────────────────────────────────────────


def test_options_deterministic(precomputed):
    r1 = generate_options(**precomputed, today=TODAY)
    r2 = generate_options(**precomputed, today=TODAY)
    assert r1 == r2
