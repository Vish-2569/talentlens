"""Tests for engine/ripple.py — ripple-effect backfill chain analysis.

TC09  Priya (E-045) chain = 3 nodes, all green, 41 days faster, ₹20L cheaper, ₹12L total
TC10  Karthik (E-031) chain has a red bus-factor flag (Terraform) and a red dead-end node
TC11  open_to_move=false employees never appear; chain depth never exceeds 3
"""
import pytest
from datetime import date

from backend.engine.match import build_edge_lookup
from backend.engine.ripple import analyze_ripple, borrow_coverage_check

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

# IDs with open_to_move=false (should never appear in any chain).
CLOSED_TO_MOVE = {"E-010", "E-018", "E-020"}


@pytest.fixture(scope="module")
def result(store):
    skill_edges_df = store.reference.skill_edges()
    return analyze_ripple(
        required_skills=SENIOR_SKILLS,
        required_level="senior",
        required_team="Payments",
        required_location="bengaluru",
        required_work_mode="onsite",
        employees_df=store.hris.employees(),
        emp_skills=store.hris.employee_skills(),
        evidence_df=store.evidence.skill_evidence(),
        edge_lookup=build_edge_lookup(skill_edges_df),
        market_stats_df=store.market.market_stats(),
        projects_df=store.hris.projects(),
        project_assignments=store.hris.project_assignments(),
        candidates_df=store.ats.candidates(),
        candidate_skills=store.ats.candidate_skills(),
        today=TODAY,
        skill_edges_df=skill_edges_df,
    )


def _get(result, person_id):
    return next(c for c in result["candidates"] if c["person_id"] == person_id)


# ── TC09: Priya chain — 3 green nodes ───────────────────────────────


def test_priya_in_top2(result):
    ids = [c["person_id"] for c in result["candidates"]]
    assert "E-045" in ids


def test_tc09_priya_chain_3_nodes(result):
    priya = _get(result, "E-045")
    assert len(priya["chain"]) == 3


def test_priya_chain_all_green(result):
    priya = _get(result, "E-045")
    statuses = [node["status"] for node in priya["chain"]]
    assert all(s == "green" for s in statuses), f"Non-green statuses: {statuses}"


def test_priya_41_days_faster(result):
    priya = _get(result, "E-045")
    assert priya["net_days_to_fill"] == 21
    assert priya["baseline_days"] == 62
    assert priya["days_saved"] == 41


def test_priya_net_cost_12L(result):
    priya = _get(result, "E-045")
    assert priya["net_cost_lpa"] == 12.0


def test_priya_20L_cheaper(result):
    priya = _get(result, "E-045")
    assert priya["cost_saved_lpa"] == 20.0


def test_priya_2_promotions(result):
    priya = _get(result, "E-045")
    assert priya["promotions"] == 2


# ── TC10: Karthik chain — bus-factor red flag + red dead-end ────────


def test_karthik_in_top2(result):
    ids = [c["person_id"] for c in result["candidates"]]
    assert "E-031" in ids


def test_tc10_karthik_bus_factor_terraform(result):
    karthik = _get(result, "E-031")
    all_flags = [f for node in karthik["chain"] for f in node.get("bus_factor_flags", [])]
    assert "terraform" in all_flags, f"Expected terraform in bus_factor_flags, got: {all_flags}"


def test_karthik_chain_has_red_node(result):
    karthik = _get(result, "E-031")
    statuses = [node["status"] for node in karthik["chain"]]
    assert "red" in statuses, f"Expected a red node in Karthik's chain, got: {statuses}"


def test_karthik_dead_end_is_lead_platform(result):
    karthik = _get(result, "E-031")
    red_nodes = [n for n in karthik["chain"] if n["status"] == "red"]
    assert len(red_nodes) >= 1
    assert red_nodes[0]["person_id"] is None  # external dead-end


# ── TC11: open_to_move=false never appears; depth cap ───────────────


def test_tc11_closed_employees_not_in_chains(result):
    for cand in result["candidates"]:
        for node in cand["chain"]:
            pid = node.get("person_id")
            if pid is not None:
                assert pid not in CLOSED_TO_MOVE, (
                    f"open_to_move=false employee {pid} appeared in chain"
                )


def test_chain_depth_never_exceeds_3(result):
    for cand in result["candidates"]:
        chain = cand["chain"]
        assert len(chain) <= 4, (
            f"Chain length {len(chain)} exceeds max 3 backfill levels + 1 mover"
        )


def test_open_to_move_false_not_mover(result):
    for cand in result["candidates"]:
        assert cand["person_id"] not in CLOSED_TO_MOVE


# ── Borrow one-liner: Arjun (C-17) not on critical project ──────────


def test_arjun_no_coverage_loss(store):
    pa = store.hris.project_assignments()
    projects = store.hris.projects()
    emp_sk = store.hris.employee_skills()
    ctr_sk = store.vms.contractor_skills()
    result_b = borrow_coverage_check("C-17", pa, projects, emp_sk, ctr_sk)
    assert result_b["loses_coverage"] is False


# ── Evidence IDs in chain nodes ──────────────────────────────────────


def test_mover_nodes_have_evidence_ids(result):
    for cand in result["candidates"]:
        mover_node = cand["chain"][0]
        assert isinstance(mover_node["evidence_ids"], list)
        assert len(mover_node["evidence_ids"]) > 0, (
            f"Mover {cand['person_id']} has no evidence_ids"
        )


# ── Backfill threshold boundary tests ─────────────────────────────


def test_backfill_exactly_70_qualifies(store):
    """A candidate scoring exactly 70 should be accepted as a backfill."""
    from unittest.mock import patch
    from backend.engine.ripple import _trace_chain, _BACKFILL_MIN

    assert _BACKFILL_MIN == 70

    fake_scored = [{"match": 70, "person_id": "E-FAKE", "evidence_ids": ["ev1"],
                    "level": "mid", "team": "Test", "location": "bengaluru",
                    "work_mode": "onsite"}]

    with patch("backend.engine.ripple._score_movers", return_value=fake_scored), \
         patch("backend.engine.ripple._bus_factor_check", return_value=[]), \
         patch("backend.engine.ripple.resolve_person", return_value={}), \
         patch("backend.engine.ripple.build_plan", return_value={
             "readiness_weeks": 0, "build_cost_lpa": 0.0, "gaps": []}):
        skill_edges_df = store.reference.skill_edges()
        chain = _trace_chain(
            level="senior", team="Test",
            location="bengaluru", work_mode="onsite",
            employees_df=store.hris.employees(),
            emp_skills=store.hris.employee_skills(),
            evidence_df=store.evidence.skill_evidence(),
            edge_lookup=build_edge_lookup(skill_edges_df),
            market_stats_df=store.market.market_stats(),
            project_assignments=store.hris.project_assignments(),
            projects_df=store.hris.projects(),
            candidates_df=store.ats.candidates(),
            candidate_skills=store.ats.candidate_skills(),
            today=TODAY,
            skill_edges_df=skill_edges_df,
        )
        assert chain[0]["person_id"] == "E-FAKE"


def test_backfill_69_9_rejected(store):
    """A candidate scoring 69.9 should NOT qualify as a backfill."""
    from unittest.mock import patch
    from backend.engine.ripple import _trace_chain

    fake_scored = [{"match": 69.9, "person_id": "E-FAKE", "evidence_ids": ["ev1"],
                    "level": "mid", "team": "Test", "location": "bengaluru",
                    "work_mode": "onsite"}]

    with patch("backend.engine.ripple._score_movers", return_value=fake_scored):
        skill_edges_df = store.reference.skill_edges()
        chain = _trace_chain(
            level="senior", team="Test",
            location="bengaluru", work_mode="onsite",
            employees_df=store.hris.employees(),
            emp_skills=store.hris.employee_skills(),
            evidence_df=store.evidence.skill_evidence(),
            edge_lookup=build_edge_lookup(skill_edges_df),
            market_stats_df=store.market.market_stats(),
            project_assignments=store.hris.project_assignments(),
            projects_df=store.hris.projects(),
            candidates_df=store.ats.candidates(),
            candidate_skills=store.ats.candidate_skills(),
            today=TODAY,
            skill_edges_df=skill_edges_df,
        )
        assert chain[0]["person_id"] is None, "69.9 should fall through to external hire"
