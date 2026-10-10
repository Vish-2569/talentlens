"""Tests for adapter layer and DataStore — verifies typed loading, immutability, demo story values."""
import pandas as pd
import pytest


# ── HRIS adapter ─────────────────────────────────────────────────────


def test_hris_employees(store):
    df = store.hris.employees()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    k = df[df.employee_id == "E-031"].iloc[0]
    assert k["display_name"] == "Karthik"
    assert k["level"] == "lead"
    assert isinstance(k["years_exp"], float)
    assert k["years_exp"] == 7.2
    assert k["open_to_move"] == True
    assert k["is_active"] == True


def test_hris_employee_skills(store):
    sk = store.hris.employee_skills()
    assert isinstance(sk, dict)
    assert "terraform" in sk["E-031"]
    assert "kubernetes" not in sk["E-045"]
    assert isinstance(sk["E-031"], set)


def test_hris_person(store):
    p = store.hris.person("E-031")
    assert isinstance(p, dict)
    assert p["display_name"] == "Karthik"
    assert p["level"] == "lead"


def test_hris_person_not_found(store):
    with pytest.raises(KeyError):
        store.hris.person("E-999")


def test_hris_projects(store):
    df = store.hris.projects()
    pc = df[df.project_id == "PROJ-01"].iloc[0]
    assert pc["name"] == "Platform-Core"
    assert pc["is_critical"] == True


def test_hris_project_assignments(store):
    asgn = store.hris.project_assignments()
    assert isinstance(asgn, dict)
    assert "PROJ-01" in asgn["E-031"]


def test_hris_exits(store):
    df = store.hris.exits()
    assert len(df) == 2
    e18 = df[df.employee_id == "E-018"].iloc[0]
    assert e18["tenure_months"] == 9


def test_hris_row_count(store):
    assert len(store.hris.employees()) == 80


# ── ATS adapter ──────────────────────────────────────────────────────


def test_ats_candidates(store):
    df = store.ats.candidates()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 100


def test_ats_candidate_skills(store):
    sk = store.ats.candidate_skills()
    assert isinstance(sk, dict)
    first_key = next(iter(sk))
    assert isinstance(sk[first_key], set)


def test_ats_requisitions(store):
    df = store.ats.requisitions()
    r1 = df[df.req_id == "REQ-001"].iloc[0]
    assert r1["decision"] == "buy"
    assert r1["time_to_fill_days"] == 68
    assert r1["first_year_cost_lpa"] == 31.0


def test_ats_past_finalists(store):
    df = store.ats.past_finalists()
    assert len(df) == 3
    remote = df[df.open_to_remote == True]
    assert len(remote) == 2


def test_ats_sourcing_history(store):
    df = store.ats.sourcing_history()
    ref = df[df.channel == "referral"].iloc[0]
    assert ref["fill_rate"] == 0.38
    assert ref["median_days"] == 34


# ── VMS adapter ──────────────────────────────────────────────────────


def test_vms_contractors(store):
    df = store.vms.contractors()
    arjun = df[df.contractor_id == "C-17"].iloc[0]
    assert arjun["display_name"] == "Arjun"
    assert arjun["level"] == "senior"
    assert arjun["bill_rate_lpa"] == 24.0


def test_vms_contractor_skills(store):
    sk = store.vms.contractor_skills()
    assert "kubernetes" in sk["C-17"]
    assert isinstance(sk["C-17"], set)


def test_vms_suppliers(store):
    df = store.vms.suppliers()
    a = df[df.supplier_id == "SUP-01"].iloc[0]
    assert a["fill_rate"] == 0.45
    assert a["median_days_to_submit"] == 9


# ── Evidence adapter ─────────────────────────────────────────────────


def test_evidence_all(store):
    df = store.evidence.skill_evidence()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    rahul_aws = df[(df.person_id == "E-072") & (df.skill_id == "aws")
                   & (df.source == "assessment")]
    assert len(rahul_aws) == 1
    assert rahul_aws.iloc[0]["value"] == "35"
    assert rahul_aws.iloc[0]["observed_on"] == "2026-03-12"


def test_evidence_by_person(store):
    df = store.evidence.skill_evidence(person_id="E-031")
    assert isinstance(df, pd.DataFrame)
    assert (df.person_id == "E-031").all()
    tf = df[df.skill_id == "terraform"]
    assert len(tf) >= 2


# ── Market adapter ───────────────────────────────────────────────────


def test_market_stats_count(store):
    df = store.market.market_stats()
    assert len(df) == 16


def test_market_stat_lookup(store):
    m = store.market.stat("bengaluru", "senior")
    assert m["ttf_p50"] == 62
    assert m["ttf_p80"] == 81
    assert m["sal_p50"] == 32.0


def test_market_stat_remote(store):
    m = store.market.stat("remote_india", "senior")
    assert m["ttf_p50"] == 28
    assert m["sal_p50"] == 29.0


# ── ReferenceCache ───────────────────────────────────────────────────


def test_ref_skills(store):
    df = store.reference.skills()
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 28
    assert "react" in df.id.values


def test_ref_skill_aliases(store):
    df = store.reference.skill_aliases()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 40


def test_ref_skill_edges(store):
    df = store.reference.skill_edges()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 30


def test_ref_title_aliases(store):
    df = store.reference.title_aliases()
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 12


def test_ref_canonical_roles(store):
    roles = store.reference.canonical_roles()
    assert isinstance(roles, list)
    assert roles[0]["id"] == "full_stack_developer"


def test_ref_reference_json(store):
    ref = store.reference.reference()
    assert isinstance(ref, dict)
    assert "esco_essential" in ref


def test_ref_automation_tasks(store):
    tasks = store.reference.automation_tasks()
    assert isinstance(tasks, list)
    assert len(tasks) > 0
    assert "potential" in tasks[0]


# ── DataStore immutability ───────────────────────────────────────────


def test_mutating_returned_frame_does_not_change_store(store):
    df1 = store.hris.employees()
    original_len = len(df1)
    df1.drop(df1.index, inplace=True)
    df2 = store.hris.employees()
    assert len(df2) == original_len


def test_mutating_skills_dict_does_not_change_store(store):
    sk1 = store.hris.employee_skills()
    sk1["E-031"].add("FAKE_SKILL")
    sk2 = store.hris.employee_skills()
    assert "FAKE_SKILL" not in sk2["E-031"]


# ── display_names ────────────────────────────────────────────────────


def test_display_names(store):
    names = store.display_names(["E-031", "E-045", "C-17"])
    assert names["E-031"] == "Karthik"
    assert names["E-045"] == "Priya"
    assert names["C-17"] == "Arjun"


def test_display_names_unknown_id(store):
    names = store.display_names(["E-999", "E-031"])
    assert "E-999" not in names
    assert names["E-031"] == "Karthik"
