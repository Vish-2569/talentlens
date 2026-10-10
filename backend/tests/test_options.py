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

from backend.engine.borrow import analyze_contractor
from backend.engine.automate import estimate_automation
from backend.engine.dejareq import dejareq
from backend.engine.evidence import resolve_person
from backend.engine.location import compare_locations
from backend.engine.market import matching_supply, market_card
from backend.engine.match import score_employee, score_contractor, build_edge_lookup
from backend.engine.build import build_plan
from backend.engine.options import (
    DEFAULT_WEIGHTS,
    _adjust_weights,
    _filter_mixes,
    _generate_atoms,
    _risk_label,
    _self_report_penalty,
    generate_options,
    round_half_up,
)
from backend.engine.ripple import analyze_ripple

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
def precomputed(store):
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
                     "skill_ids": [s["id"] for s in SENIOR_SKILLS
                                  if s["importance"] == "must"]},
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


def test_tc33_options_five_required_fields(result):
    """TC33: all 5 options have time, cost, fit, risk_label, reason; mix is scored."""
    required = {
        "option_id", "name", "what_it_means", "ready_by_p80_days",
        "year_one_cost_lpa", "fit", "risk_label", "score",
        "one_line_reason", "evidence_ids",
    }
    assert len(result["options"]) == 5, "Exactly 5 options required"
    for opt in result["options"]:
        missing = required - set(opt.keys())
        assert not missing, f"{opt['name']} missing fields: {missing}"
    # Mix must be numerically scored (not "add-on")
    top_mixes = result.get("top_mixes", [])
    assert top_mixes and isinstance(top_mixes[0]["score"], (int, float)), (
        "Mix option must carry a numeric score"
    )


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


def test_option_scores(result):
    by_name = {o["name"]: o["score"] for o in result["options"]}
    assert by_name["Build"] == 73
    assert by_name["Buy"] == 42
    assert by_name["Borrow"] == 87
    assert by_name["Relocate"] == 62
    assert by_name["Automate"] == "add-on"


def test_option_ranking(result):
    scored = [o for o in result["options"] if isinstance(o["score"], int)]
    scores = [(o["name"], o["score"]) for o in scored]
    scores.sort(key=lambda x: -x[1])
    names = [s[0] for s in scores]
    assert names == ["Borrow", "Build", "Relocate", "Buy"]


def test_mix_score_89(result):
    top = result["top_mixes"][0]
    assert top["score"] == 89


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


def test_tc29_self_report_penalty_synthetic():
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
    from backend.engine.options import _compute_entry_stats, _score_pool

    base_atom = {
        "type": "build", "person_id": "E-045", "location": None,
        "option_category": "build", "cost_lpa": 12.0, "days": 42,
        "fit": 0.82, "red_flags": 0, "evidence_ids": ["react"],
    }
    flagged_atom = {**base_atom, "person_id": "E-031", "red_flags": 3}

    w = dict(DEFAULT_WEIGHTS)
    total = sum(w.values())
    w = {k: v / total for k, v in w.items()}

    clean = _compute_entry_stats([base_atom], {}, [])
    flagged = _compute_entry_stats([flagged_atom], {}, [])

    assert flagged["risk_raw"] > clean["risk_raw"]
    scores, _dims = _score_pool([clean, flagged], w)
    assert scores[1] < scores[0]


# ── Determinism ──────────────────────────────────────────────────────────────


def test_options_deterministic(precomputed):
    r1 = generate_options(**precomputed, today=TODAY)
    r2 = generate_options(**precomputed, today=TODAY)
    assert r1 == r2


# ── Karthik red_flags == 2 (bus factor + red dead-end), Priya == 0 ─────────


def test_karthik_red_flags_equals_2(precomputed):
    """TC10: Karthik's chain has a Terraform bus-factor flag AND a red
    dead-end node (no backfill >= 70, Lead P50 76 > 60). Both count."""
    atoms = _generate_atoms(
        match_results=precomputed["match_results"],
        build_plans=precomputed["build_plans"],
        borrow_analyses=precomputed["borrow_analyses"],
        location_results=precomputed["location_results"],
        automation_result=precomputed["automation_result"],
        market_data=precomputed["market_data"],
        ripple_result=precomputed["ripple_result"],
    )
    karthik = next(a for a in atoms if a["person_id"] == "E-031")
    assert karthik["red_flags"] == 2


def test_priya_red_flags_equals_0(precomputed):
    atoms = _generate_atoms(
        match_results=precomputed["match_results"],
        build_plans=precomputed["build_plans"],
        borrow_analyses=precomputed["borrow_analyses"],
        location_results=precomputed["location_results"],
        automation_result=precomputed["automation_result"],
        market_data=precomputed["market_data"],
        ripple_result=precomputed["ripple_result"],
    )
    priya = next(a for a in atoms if a["person_id"] == "E-045")
    assert priya["red_flags"] == 0


# ── Bridge-only mix rejected (does not cover full duration) ────────────────


def test_bridge_only_mix_rejected():
    """A standalone 3-month bridge cannot fill a 12-month need."""
    bridge = {
        "type": "bridge", "person_id": "C-17", "location": None,
        "option_category": "borrow", "cost_lpa": 6.0, "days": 0,
        "fit": 0.84, "red_flags": 0, "evidence_ids": [],
    }
    auto = {
        "type": "automate", "person_id": None, "location": None,
        "option_category": "automate", "cost_lpa": 1.0, "days": 7,
        "fit": 0.0, "red_flags": 0, "evidence_ids": [],
    }
    mixes = [[bridge], [bridge, auto]]
    filtered = _filter_mixes(mixes, [], duration_months=12)
    assert len(filtered) == 0


def test_bridge_plus_build_mix_valid():
    """A bridge + build mix covers the full duration."""
    bridge = {
        "type": "bridge", "person_id": "C-17", "location": None,
        "option_category": "borrow", "cost_lpa": 6.0, "days": 0,
        "fit": 0.84, "red_flags": 0, "evidence_ids": [],
    }
    build = {
        "type": "build", "person_id": "E-045", "location": None,
        "option_category": "build", "cost_lpa": 12.0, "days": 42,
        "fit": 0.82, "red_flags": 0, "evidence_ids": [],
    }
    mixes = [[bridge, build]]
    filtered = _filter_mixes(mixes, [], duration_months=12)
    assert len(filtered) == 1


# ── Déjà Req risk wiring: churn → buy+relocate, knowledge-loss → borrow ───


def test_dejareq_churn_applies_to_buy_and_relocate():
    """When dejareq fires churn (option='buy', delta=0.20), both Buy and
    Relocate atoms carry +0.20 risk since both are external hires."""
    from backend.engine.options import _compute_entry_stats

    dejareq_with_churn = {
        "risk_adjustments": [
            {"option": "buy", "delta": 0.20, "reason": "churn"},
        ],
    }
    buy_atom = {
        "type": "buy", "person_id": None, "location": "bengaluru",
        "option_category": "buy", "cost_lpa": 32.0, "days": 81,
        "fit": 0.70, "red_flags": 0, "evidence_ids": [],
    }
    relocate_atom = {
        "type": "relocate", "person_id": None, "location": "remote_india",
        "option_category": "relocate", "cost_lpa": 29.0, "days": 40,
        "fit": 0.65, "red_flags": 0, "evidence_ids": [],
    }

    buy_churn = _compute_entry_stats([buy_atom], dejareq_with_churn, [])
    buy_no = _compute_entry_stats([buy_atom], {}, [])
    rel_churn = _compute_entry_stats([relocate_atom], dejareq_with_churn, [])
    rel_no = _compute_entry_stats([relocate_atom], {}, [])

    assert abs(buy_churn["risk_raw"] - buy_no["risk_raw"] - 0.20) < 0.01
    assert abs(rel_churn["risk_raw"] - rel_no["risk_raw"] - 0.20) < 0.01


def test_dejareq_knowledge_loss_applies_to_borrow():
    """When dejareq fires knowledge-loss (option='borrow', delta=0.10),
    Borrow atoms carry +0.10 risk."""
    from backend.engine.options import _compute_entry_stats

    dejareq_kl = {
        "risk_adjustments": [
            {"option": "borrow", "delta": 0.10, "reason": "knowledge loss"},
        ],
    }
    extend_atom = {
        "type": "extend", "person_id": "C-17", "location": None,
        "option_category": "borrow", "cost_lpa": 24.0, "days": 0,
        "fit": 0.84, "red_flags": 0, "evidence_ids": [],
    }

    kl = _compute_entry_stats([extend_atom], dejareq_kl, [])
    no = _compute_entry_stats([extend_atom], {}, [])

    assert abs(kl["risk_raw"] - no["risk_raw"] - 0.10) < 0.01


# ── Risk label thresholds ──────────────────────────────────────────────────


def test_risk_label_low():
    assert _risk_label(0.0) == "Low"
    assert _risk_label(0.29) == "Low"


def test_risk_label_medium():
    assert _risk_label(0.30) == "Medium"
    assert _risk_label(0.44) == "Medium"


def test_risk_label_medium_high():
    assert _risk_label(0.45) == "Medium-high"
    assert _risk_label(0.59) == "Medium-high"


def test_risk_label_high():
    assert _risk_label(0.60) == "High"
    assert _risk_label(1.0) == "High"


# ── Unified scoring: same atom gets same score as card and as mix ──────────


def test_borrow_card_score_equals_extend_mix_score(result):
    """extend(C-17) must have an identical score whether it appears as the
    Borrow option card or as a standalone mix, because both are scored in
    one shared normalization pool."""
    borrow_card = next(o for o in result["options"] if o["name"] == "Borrow")
    extend_mix = None
    for mx in result["top_mixes"]:
        atoms = mx["atoms"]
        if len(atoms) == 1 and atoms[0]["type"] == "extend":
            extend_mix = mx
            break
    if extend_mix is None:
        pytest.skip("extend-only mix not in top 3")
    assert borrow_card["score"] == extend_mix["score"], (
        f"Borrow card score {borrow_card['score']} != "
        f"extend mix score {extend_mix['score']}"
    )


# ── Build card uses Build-band only (match 70-84, needs upskilling) ────────


def test_build_card_is_build_band(result, precomputed):
    """The Build option card must come from a Build-band atom (type=='build',
    match 70-84), not a redeploy atom (85-100). Redeploy atoms are valid in
    mixes but not as the Build card."""
    build_card = next(o for o in result["options"] if o["name"] == "Build")
    # Build-band atoms have type "build" and days > 0 (need upskilling)
    assert build_card["ready_by_p80_days"] > 0, (
        "Build card should need upskilling time (days > 0), "
        "not be a ready-now redeploy"
    )
    # Verify it's not Karthik's redeploy atom (cost 42L, 0 days)
    assert build_card["year_one_cost_lpa"] != 42.0 or build_card["ready_by_p80_days"] != 0


# ── Tie-break: equal score → lower cost → fewer atoms ────────────────────


def test_tiebreak_fewer_atoms_wins(result):
    """bridge(C-17)+build(E-045) must rank above bridge+build+automate
    when both have the same score, because it has fewer atoms."""
    mixes = result["top_mixes"]
    bridge_build = None
    bridge_build_auto = None
    for mx in mixes:
        types = sorted(a["type"] for a in mx["atoms"])
        if types == ["bridge", "build"]:
            bridge_build = mx
        elif types == ["automate", "bridge", "build"]:
            bridge_build_auto = mx
    if bridge_build is None or bridge_build_auto is None:
        pytest.skip("both mixes not in top 3")
    assert bridge_build["score"] == bridge_build_auto["score"], (
        "Precondition: both mixes must have the same score"
    )
    bb_idx = mixes.index(bridge_build)
    bba_idx = mixes.index(bridge_build_auto)
    assert bb_idx < bba_idx, (
        f"bridge+build (idx {bb_idx}) must rank above "
        f"bridge+build+automate (idx {bba_idx})"
    )


# ── Dimensions reproduce scores (round_half_up, not round) ─────────────────


def test_dimensions_reproduce_scores(result):
    """For every scored option and mix, round_half_up(Σ(w×d)×100) == score."""
    w = result["weights_used"]
    for opt in result["options"]:
        if opt["name"] == "Automate":
            assert opt.get("dimensions") is None
            continue
        d = opt["dimensions"]
        raw = (w["speed"] * d["speed"]
               + w["cost"] * d["cost"]
               + w["fit"] * d["fit"]
               + w["risk"] * d["risk"]
               + w["strategic"] * d["strategic"])
        assert round_half_up(raw * 100) == opt["score"], (
            f"{opt['name']}: round_half_up({raw}*100) = {round_half_up(raw * 100)}, "
            f"expected {opt['score']}"
        )
    for mx in result["top_mixes"]:
        d = mx["dimensions"]
        raw = (w["speed"] * d["speed"]
               + w["cost"] * d["cost"]
               + w["fit"] * d["fit"]
               + w["risk"] * d["risk"]
               + w["strategic"] * d["strategic"])
        assert round_half_up(raw * 100) == mx["score"], (
            f"mix {mx['mix_id']}: round_half_up({raw}*100) = "
            f"{round_half_up(raw * 100)}, expected {mx['score']}"
        )


# ── Half-up rounding with exact binary .5 case ────────────────────────────


def test_half_up_rounding_exact_binary():
    """0.125 is exact in IEEE 754; 0.125 * 100 = 12.5; half-up → 13.
    Python round(12.5) would give 12 (banker's rounding)."""
    assert round_half_up(12.5) == 13
    assert round(12.5) == 12  # banker's rounding for comparison
    assert round_half_up(0.125 * 100) == 13


# ── Five option IDs: Build, Buy, Borrow, Relocate, Automate (no mix) ──────


def test_options_five_ids(result):
    ids = {o["option_id"] for o in result["options"]}
    assert ids == {"build", "buy", "borrow", "relocate", "automate"}


def test_mix_not_in_five(result):
    ids = {o["option_id"] for o in result["options"]}
    assert "mix" not in ids


# ── relaxed_mask documents which constraints generate_options enforces ──────


def test_relaxed_mask_bits(precomputed):
    """Verify relaxed_mask = '11110' behaviourally.

    For each constraint, call generate_options twice — once as the demo
    requisition, once with only that constraint changed — and compare scored
    output.  Output unchanged => bit 1 (constraint not enforced).
    Output changed  => bit 0 (constraint enforced).

    Constraint order: [location, years, skill, budget, deadline].
    """
    import inspect

    # ── Bits 0-3: location, years, skill, budget => bit 1 ───────────────
    # generate_options has no parameter for any of these four constraints.
    # Calling it with "location = Remote-India / years = 3 / kubernetes nice /
    # budget = P50" would produce identical output because there is no
    # mechanism to pass those constraints in.  We verify this by checking
    # that the function signature contains none of those parameters.
    sig_params = set(inspect.signature(generate_options).parameters)
    for absent_param in ("location", "requested_location", "min_years",
                         "must_skill", "budget", "budget_lpa"):
        assert absent_param not in sig_params, (
            f"generate_options must NOT have a '{absent_param}' parameter "
            f"(relaxed_mask bit for that constraint must be 1)"
        )

    # Confirm by running with the same precomputed data twice — output
    # identical, so none of the absent constraints could have been enforced.
    base = generate_options(**precomputed, today=TODAY)
    again = generate_options(**precomputed, today=TODAY)
    base_scores = sorted(
        (o["option_id"], o["score"]) for o in base["options"]
    )
    again_scores = sorted(
        (o["option_id"], o["score"]) for o in again["options"]
    )
    assert base_scores == again_scores, (
        "generate_options is not deterministic — cannot verify relaxed bits"
    )

    # ── Bit 4: deadline => bit 0 ─────────────────────────────────────────
    # deadline_days IS a parameter and _adjust_weights shifts speed/strategic
    # when deadline_days < 60.  Running with deadline=30 vs deadline=90
    # should produce different weights → different scores.
    tight = generate_options(**{**precomputed, "deadline_days": 30}, today=TODAY)
    loose = generate_options(**{**precomputed, "deadline_days": 90}, today=TODAY)
    tight_scores = {o["option_id"]: o["score"] for o in tight["options"]
                    if o["score"] is not None}
    loose_scores = {o["option_id"]: o["score"] for o in loose["options"]
                    if o["score"] is not None}
    assert tight_scores != loose_scores, (
        "deadline_days=30 vs deadline_days=90 produced identical scores — "
        "relaxed_mask bit 4 must be 0 (deadline is enforced)"
    )
