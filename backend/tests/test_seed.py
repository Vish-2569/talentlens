"""Tests for seed data generation — verifies demo story numbers from CLAUDE.md §13."""
import csv
import hashlib
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module", autouse=True)
def generate_seed_data():
    from backend.data.seed import main
    main()


def _read(name: str) -> list[dict]:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── Employees ─────────────────────────────────────────────────────────


def test_key_employees_exist():
    rows = _read("employees.csv")
    ids = {r["employee_id"] for r in rows}
    assert {"E-031", "E-045", "E-072", "E-010"} <= ids


def test_karthik():
    e = next(r for r in _read("employees.csv") if r["employee_id"] == "E-031")
    assert e["display_name"] == "Karthik"
    assert e["level"] == "lead"
    assert e["team"] == "Platform"
    assert e["open_to_move"] == "true"


def test_priya():
    e = next(r for r in _read("employees.csv") if r["employee_id"] == "E-045")
    assert e["display_name"] == "Priya"
    assert e["level"] == "mid"
    assert e["team"] == "Checkout"
    assert float(e["years_exp"]) >= 4.0
    assert e["open_to_move"] == "true"


def test_rahul():
    e = next(r for r in _read("employees.csv") if r["employee_id"] == "E-072")
    assert e["display_name"] == "Rahul"
    assert e["level"] == "junior"
    assert e["team"] == "Checkout"
    assert e["open_to_move"] == "true"


def test_karthik_has_terraform():
    skills = {r["skill_id"] for r in _read("employee_skills.csv")
              if r["employee_id"] == "E-031"}
    assert "terraform" in skills
    assert "kubernetes" in skills
    assert "react" in skills
    assert "nodejs" in skills


def test_priya_no_kubernetes():
    skills = {r["skill_id"] for r in _read("employee_skills.csv")
              if r["employee_id"] == "E-045"}
    assert "react" in skills
    assert "nodejs" in skills
    assert "kubernetes" not in skills


def test_rahul_skills():
    skills = {r["skill_id"] for r in _read("employee_skills.csv")
              if r["employee_id"] == "E-072"}
    assert {"react", "nodejs", "javascript"} <= skills


def test_no_other_platform_has_terraform():
    """Karthik is sole Terraform holder on Platform (bus factor = 1)."""
    emps = _read("employees.csv")
    platform_ids = {e["employee_id"] for e in emps if e["team"] == "Platform"}
    skills = _read("employee_skills.csv")
    tf_holders = {s["employee_id"] for s in skills
                  if s["skill_id"] == "terraform" and s["employee_id"] in platform_ids}
    assert tf_holders == {"E-031"}


def test_years_relaxation_widens_build():
    """Relaxing 5+ → 3+ years widens internal Build pool from 1 to 4."""
    emps = _read("employees.csv")
    skills_rows = _read("employee_skills.csv")
    skill_map = {}
    for s in skills_rows:
        skill_map.setdefault(s["employee_id"], set()).add(s["skill_id"])

    active_open = [
        e for e in emps
        if e["is_active"] == "true" and e["open_to_move"] == "true"
    ]
    has_rn = [
        e for e in active_open
        if skill_map.get(e["employee_id"], set()) >= {"react", "nodejs"}
    ]
    at_5 = [e for e in has_rn if float(e["years_exp"]) >= 5]
    at_3 = [e for e in has_rn if float(e["years_exp"]) >= 3]
    assert len(at_5) == 1, f"Expected 1, got {len(at_5)}: {[e['employee_id'] for e in at_5]}"
    assert len(at_3) == 4, f"Expected 4, got {len(at_3)}: {[e['employee_id'] for e in at_3]}"


# ── Contractors ───────────────────────────────────────────────────────


def test_arjun():
    c = next(r for r in _read("contractors.csv") if r["contractor_id"] == "C-17")
    assert c["display_name"] == "Arjun"
    assert c["level"] == "senior"
    assert float(c["bill_rate_lpa"]) == 24.0


def test_arjun_skills():
    skills = {r["skill_id"] for r in _read("contractor_skills.csv")
              if r["contractor_id"] == "C-17"}
    assert {"react", "nodejs", "kubernetes"} <= skills


# ── Requisitions (Deja Req) ───────────────────────────────────────────


def test_four_past_requisitions():
    reqs = [r for r in _read("requisitions.csv")
            if r["role"] == "Full Stack Developer" and r["level"] == "senior"]
    assert len(reqs) == 4


def test_req_decisions():
    by_id = {r["req_id"]: r for r in _read("requisitions.csv")}
    assert by_id["REQ-001"]["decision"] == "buy"
    assert by_id["REQ-002"]["decision"] == "buy"
    assert by_id["REQ-003"]["decision"] == "borrow"
    assert by_id["REQ-004"]["decision"] == "build"


def test_buy_ttf():
    by_id = {r["req_id"]: r for r in _read("requisitions.csv")}
    assert int(by_id["REQ-001"]["time_to_fill_days"]) == 68
    assert int(by_id["REQ-002"]["time_to_fill_days"]) == 74


def test_buy_costs():
    by_id = {r["req_id"]: r for r in _read("requisitions.csv")}
    assert float(by_id["REQ-001"]["first_year_cost_lpa"]) == 31.0
    assert float(by_id["REQ-002"]["first_year_cost_lpa"]) == 33.0
    assert float(by_id["REQ-003"]["first_year_cost_lpa"]) == 24.0
    assert float(by_id["REQ-004"]["first_year_cost_lpa"]) == 4.0


# ── Exits ─────────────────────────────────────────────────────────────


def test_avg_external_tenure():
    """Average tenure of external hires: 8 months (9 and 7)."""
    exits = _read("exits.csv")
    buy_exits = [r for r in exits if r["req_origin"] in ("REQ-001", "REQ-002")]
    tenures = sorted(int(r["tenure_months"]) for r in buy_exits)
    assert tenures == [7, 9]
    assert sum(tenures) / len(tenures) == 8.0


# ── Candidate Supply ──────────────────────────────────────────────────


def _supply(location, work_mode, level, must_skills, min_years=5):
    """Count candidates matching all filters."""
    cands = _read("candidates.csv")
    skills = _read("candidate_skills.csv")
    pool = {
        c["candidate_id"] for c in cands
        if c["level"] == level
        and c["location"] == location
        and c["work_mode"] == work_mode
        and float(c["years_exp"]) >= min_years
    }
    sk_map = {}
    for s in skills:
        sk_map.setdefault(s["candidate_id"], set()).add(s["skill_id"])
    return {cid for cid in pool if sk_map.get(cid, set()) >= set(must_skills)}


def test_bengaluru_senior_all_constraints():
    """14 Bengaluru on-site Senior with React+Node.js+Kubernetes."""
    assert len(_supply("bengaluru", "onsite", "senior",
                        ["react", "nodejs", "kubernetes"])) == 14


def test_bengaluru_senior_without_kubernetes():
    """47 without Kubernetes constraint (Kubernetes removes 70%)."""
    assert len(_supply("bengaluru", "onsite", "senior",
                        ["react", "nodejs"])) == 47


def test_remote_india_senior_supply():
    assert len(_supply("remote_india", "remote", "senior",
                        ["react", "nodejs", "kubernetes"])) == 210


def test_hyderabad_senior_supply():
    assert len(_supply("hyderabad", "onsite", "senior",
                        ["react", "nodejs", "kubernetes"])) == 31


def test_pune_senior_supply():
    assert len(_supply("pune", "onsite", "senior",
                        ["react", "nodejs", "kubernetes"])) == 26


# ── Market Stats ──────────────────────────────────────────────────────


def _mstat(location, level):
    return next(r for r in _read("market_stats.csv")
                if r["location"] == location and r["level"] == level)


def test_market_bengaluru_senior():
    m = _mstat("bengaluru", "senior")
    assert int(m["ttf_p50"]) == 62
    assert int(m["ttf_p80"]) == 81
    assert float(m["sal_p50"]) == 32.0
    assert float(m["sal_p25"]) == 24.0
    assert float(m["sal_p75"]) == 40.0


def test_market_remote_senior():
    m = _mstat("remote_india", "senior")
    assert int(m["ttf_p50"]) == 28
    assert int(m["ttf_p80"]) == 40
    assert float(m["sal_p50"]) == 29.0


def test_market_hyderabad_senior():
    m = _mstat("hyderabad", "senior")
    assert int(m["ttf_p50"]) == 44
    assert int(m["ttf_p80"]) == 58
    assert float(m["sal_p50"]) == 30.0


def test_market_pune_senior():
    m = _mstat("pune", "senior")
    assert int(m["ttf_p50"]) == 47
    assert int(m["ttf_p80"]) == 62
    assert float(m["sal_p50"]) == 26.0


def test_market_bengaluru_junior():
    m = _mstat("bengaluru", "junior")
    assert int(m["ttf_p50"]) == 21
    assert float(m["sal_p50"]) == 7.0


def test_market_bengaluru_lead():
    m = _mstat("bengaluru", "lead")
    assert int(m["ttf_p50"]) == 76


# ── Evidence ──────────────────────────────────────────────────────────


def _evidence_for(person_id, skill_id):
    return [r for r in _read("evidence.csv")
            if r["person_id"] == person_id and r["skill_id"] == skill_id]


def test_rahul_aws_evidence():
    rows = _evidence_for("E-072", "aws")
    sources = {r["source"] for r in rows}
    assert {"assessment", "self"} <= sources
    a = next(r for r in rows if r["source"] == "assessment")
    assert int(a["value"]) == 35
    assert a["observed_on"] == "2026-03-12"


def test_priya_kubernetes_evidence():
    rows = _evidence_for("E-045", "kubernetes")
    sources = {r["source"] for r in rows}
    assert {"assessment", "self"} <= sources
    a = next(r for r in rows if r["source"] == "assessment")
    assert int(a["value"]) == 40
    assert a["observed_on"] == "2026-08-18"
    s = next(r for r in rows if r["source"] == "self")
    assert s["value"] == "expert"


def test_karthik_terraform_evidence():
    rows = _evidence_for("E-031", "terraform")
    sources = {r["source"] for r in rows}
    assert "certification" in sources
    assert "project" in sources
    proj = next(r for r in rows if r["source"] == "project")
    assert int(proj["value"]) == 30


def test_graphql_self_report_only():
    """At least one person has GraphQL with self-report as the only source."""
    ev = _read("evidence.csv")
    gql = [r for r in ev if r["skill_id"] == "graphql"]
    people = {r["person_id"] for r in gql}
    for pid in people:
        person_gql = [r for r in gql if r["person_id"] == pid]
        if {r["source"] for r in person_gql} == {"self"}:
            return
    pytest.fail("No person has GraphQL with self-report only")


# ── Past Finalists ────────────────────────────────────────────────────


def test_three_past_finalists():
    rows = _read("past_finalists.csv")
    assert len(rows) == 3


def test_two_remote_ready_finalists():
    rows = _read("past_finalists.csv")
    remote_ready = [r for r in rows if r["open_to_remote"] == "true"]
    assert len(remote_ready) == 2


# ── Sourcing ──────────────────────────────────────────────────────────


def test_sourcing_referral():
    rows = _read("sourcing_history.csv")
    ref = next(r for r in rows if r["channel"] == "referral")
    assert float(ref["fill_rate"]) == 0.38
    assert int(ref["median_days"]) == 34


def test_sourcing_supplier():
    rows = _read("sourcing_history.csv")
    sup = next(r for r in rows if r["channel"] == "supplier")
    assert float(sup["fill_rate"]) == 0.45
    assert int(sup["median_days"]) == 9


def test_sourcing_job_board():
    rows = _read("sourcing_history.csv")
    jb = next(r for r in rows if r["channel"] == "job_board")
    assert float(jb["fill_rate"]) == 0.22
    assert int(jb["median_days"]) == 52


# ── Suppliers ─────────────────────────────────────────────────────────


def test_supplier_a():
    rows = _read("suppliers.csv")
    s = next(r for r in rows if r["supplier_id"] == "SUP-01")
    assert float(s["fill_rate"]) == 0.45
    assert int(s["median_days_to_submit"]) == 9


# ── Projects ──────────────────────────────────────────────────────────


def test_platform_core_critical():
    projects = _read("projects.csv")
    pc = next(r for r in projects if r["name"] == "Platform-Core")
    assert pc["is_critical"] == "true"


def test_karthik_on_platform_core():
    assignments = _read("project_assignments.csv")
    ka = [r for r in assignments if r["employee_id"] == "E-031"]
    assert any(r["project_id"] == "PROJ-01" for r in ka)


# ── Determinism ───────────────────────────────────────────────────────


def test_deterministic():
    """Running seed twice produces identical CSV output."""
    from backend.data.seed import main

    def _hashes():
        h = {}
        for f in sorted(DATA_DIR.glob("*.csv")):
            h[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
        return h

    main()
    h1 = _hashes()
    main()
    h2 = _hashes()
    assert h1 == h2
    assert len(h1) >= 15, f"Expected ≥15 CSVs, got {len(h1)}"
