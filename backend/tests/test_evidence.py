"""Tests for engine/evidence.py — skill evidence scoring and conflict detection."""
import pandas as pd
import pytest
from datetime import date

from backend.data.seed import main as seed_main
from backend.engine.evidence import normalize_evidence, resolve_person, data_quality
from backend.store import DataStore

TODAY = date(2026, 10, 8)


@pytest.fixture(scope="module", autouse=True)
def generate():
    seed_main()


@pytest.fixture(scope="module")
def store():
    return DataStore()


# ── normalize_evidence unit tests ─────────────────────────────────────


def test_normalize_assessment():
    assert normalize_evidence({"source": "assessment", "value": "35", "detail": ""}) == 35


def test_normalize_assessment_high():
    assert normalize_evidence({"source": "assessment", "value": "80", "detail": ""}) == 80


def test_normalize_cert_associate():
    assert normalize_evidence(
        {"source": "certification", "value": "", "detail": "Terraform Associate 2025"}
    ) == 65


def test_normalize_cert_professional():
    assert normalize_evidence(
        {"source": "certification", "value": "", "detail": "AWS Professional 2026"}
    ) == 80


def test_normalize_cert_specialty():
    assert normalize_evidence(
        {"source": "certification", "value": "", "detail": "Security Specialty 2026"}
    ) == 85


def test_normalize_project_short():
    assert normalize_evidence({"source": "project", "value": "2", "detail": ""}) == 40


def test_normalize_project_3_to_6():
    assert normalize_evidence({"source": "project", "value": "5", "detail": ""}) == 55


def test_normalize_project_6_to_12():
    assert normalize_evidence({"source": "project", "value": "9", "detail": ""}) == 65


def test_normalize_project_long():
    assert normalize_evidence({"source": "project", "value": "30", "detail": ""}) == 75


def test_normalize_project_tech_lead():
    assert normalize_evidence(
        {"source": "project", "value": "14", "detail": "Platform-Core, tech lead"}
    ) == 85


def test_normalize_self_beginner():
    assert normalize_evidence({"source": "self", "value": "beginner", "detail": ""}) == 30


def test_normalize_self_intermediate():
    assert normalize_evidence({"source": "self", "value": "intermediate", "detail": ""}) == 55


def test_normalize_self_advanced():
    assert normalize_evidence({"source": "self", "value": "advanced", "detail": ""}) == 75


def test_normalize_self_expert():
    assert normalize_evidence({"source": "self", "value": "expert", "detail": ""}) == 90


# ── TC23: Rahul AWS ───────────────────────────────────────────────────


def test_rahul_aws(store):
    ev = store.evidence.skill_evidence(person_id="E-072")
    scores = resolve_person("E-072", ev, today=TODAY)
    aws = next(s for s in scores if s["skill"] == "aws")
    assert aws["value"] == 35
    assert aws["source"] == "assessment"
    assert aws["observed_on"] == "2026-03-12"
    assert aws["conflict"] is False
    assert "intermediate" in aws["tooltip"].lower()
    assert "ignored" in aws["tooltip"].lower()


# ── TC24: Self-only intermediate → 39 ────────────────────────────────


def test_self_only_intermediate_39(store):
    ev = store.evidence.skill_evidence(person_id="E-045")
    scores = resolve_person("E-045", ev, today=TODAY)
    gql = next(s for s in scores if s["skill"] == "graphql")
    assert gql["value"] == 39
    assert gql["source"] == "self"
    assert "0.7" in gql["tooltip"] or "× 0.7" in gql["tooltip"]


# ── TC25: Priya Kubernetes conflict ───────────────────────────────────


def test_priya_kubernetes_conflict(store):
    ev = store.evidence.skill_evidence(person_id="E-045")
    scores = resolve_person("E-045", ev, today=TODAY)
    k8s = next(s for s in scores if s["skill"] == "kubernetes")
    assert k8s["value"] == 40
    assert k8s["source"] == "assessment"
    assert k8s["conflict"] is True
    assert "50 points" in k8s["tooltip"]


# ── Karthik Terraform → certification used ────────────────────────────


def test_karthik_terraform_certification(store):
    ev = store.evidence.skill_evidence(person_id="E-031")
    scores = resolve_person("E-031", ev, today=TODAY)
    tf = next(s for s in scores if s["skill"] == "terraform")
    assert tf["source"] == "certification"
    assert tf["value"] == 65
    assert tf["conflict"] is False


# ── TC26: Stale assessment + recent certification → cert used ─────────


def test_stale_assessment_cert_wins():
    ev_df = pd.DataFrame([
        {"person_id": "T-01", "skill_id": "aws", "source": "assessment",
         "value": "80", "observed_on": "2024-01-01", "detail": ""},
        {"person_id": "T-01", "skill_id": "aws", "source": "certification",
         "value": "", "observed_on": "2026-06-01", "detail": "AWS Professional 2026"},
    ])
    scores = resolve_person("T-01", ev_df, today=TODAY)
    aws = next(s for s in scores if s["skill"] == "aws")
    assert aws["source"] == "certification"
    assert aws["value"] == 80
    assert aws["stale"] is False
    ignored_reasons = [i["reason"].lower() for i in aws["ignored"]]
    assert any("stale" in r for r in ignored_reasons)


# ── TC27: Two assessments → most recent used ──────────────────────────


def test_two_assessments_most_recent():
    ev_df = pd.DataFrame([
        {"person_id": "T-02", "skill_id": "react", "source": "assessment",
         "value": "60", "observed_on": "2025-06-01", "detail": ""},
        {"person_id": "T-02", "skill_id": "react", "source": "assessment",
         "value": "75", "observed_on": "2026-03-01", "detail": ""},
    ])
    scores = resolve_person("T-02", ev_df, today=TODAY)
    react = next(s for s in scores if s["skill"] == "react")
    assert react["value"] == 75
    assert react["observed_on"] == "2026-03-01"


# ── TC28: Conflict boundary 29 → no, 30 → yes ────────────────────────


def test_conflict_boundary_29_no_conflict():
    ev_df = pd.DataFrame([
        {"person_id": "T-03", "skill_id": "aws", "source": "assessment",
         "value": "61", "observed_on": "2026-06-01", "detail": ""},
        {"person_id": "T-03", "skill_id": "aws", "source": "self",
         "value": "expert", "observed_on": "2026-06-01", "detail": ""},
    ])
    scores = resolve_person("T-03", ev_df, today=TODAY)
    aws = next(s for s in scores if s["skill"] == "aws")
    assert aws["conflict"] is False


def test_conflict_boundary_30_conflict():
    ev_df = pd.DataFrame([
        {"person_id": "T-04", "skill_id": "aws", "source": "assessment",
         "value": "60", "observed_on": "2026-06-01", "detail": ""},
        {"person_id": "T-04", "skill_id": "aws", "source": "self",
         "value": "expert", "observed_on": "2026-06-01", "detail": ""},
    ])
    scores = resolve_person("T-04", ev_df, today=TODAY)
    aws = next(s for s in scores if s["skill"] == "aws")
    assert aws["conflict"] is True


# ── data_quality ──────────────────────────────────────────────────────


def test_data_quality_counts(store):
    ev = store.evidence.skill_evidence()
    all_scores = []
    for pid in ["E-031", "E-045", "E-072", "C-17"]:
        person_ev = ev[ev.person_id == pid]
        all_scores.extend(resolve_person(pid, person_ev, today=TODAY))
    dq = data_quality(all_scores)
    assert dq["conflicts"] >= 2
    assert dq["stale"] >= 1
    assert dq["self_report_only"] >= 3
    assert "conflict" in dq["line"].lower()
    assert "stale" in dq["line"].lower()
    assert "self-report" in dq["line"].lower()
