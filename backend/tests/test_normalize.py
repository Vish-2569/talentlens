"""Tests for engine/normalize.py — title and skill normalization."""
import pytest

from backend.engine.normalize import (
    normalize_title, normalize_skill, skill_relation, title_normalization_panel,
)

ESCO_URI = "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1"


def _title(store, raw, system="ats"):
    return normalize_title(
        raw, system,
        store.reference.title_aliases(),
        store.reference.canonical_roles(),
    )


def _skill(store, token):
    return normalize_skill(
        token,
        store.reference.skills(),
        store.reference.skill_aliases(),
    )


# ── TC31: Title normalization ─────────────────────────────────────────


def test_tc31_sde2_full_stack_mid(store):
    r = _title(store, "SDE-2 (Full Stack)", "hris")
    assert r["role"] == "Full Stack Developer"
    assert r["level"] == "mid"
    assert r["level_label"] == "stated"
    assert r["esco_uri"] == ESCO_URI


def test_mern_stack_developer_inferred(store):
    r = _title(store, "MERN Stack Developer", "ats")
    assert r["role"] == "Full Stack Developer"
    assert r["level_label"] == "inferred"
    assert r["esco_uri"] == ESCO_URI


def test_sr_fullstack_engineer_senior(store):
    r = _title(store, "Sr. Full-Stack Engineer – Contract", "vms")
    assert r["role"] == "Full Stack Developer"
    assert r["level"] == "senior"
    assert r["level_label"] == "stated"
    assert r["esco_uri"] == ESCO_URI


def test_sde1_junior(store):
    r = _title(store, "SDE-1", "hris")
    assert r["role"] == "Full Stack Developer"
    assert r["level"] == "junior"
    assert r["level_label"] == "stated"


def test_lead_full_stack(store):
    r = _title(store, "Lead Full Stack Engineer", "hris")
    assert r["role"] == "Full Stack Developer"
    assert r["level"] == "lead"
    assert r["level_label"] == "stated"


def test_full_stack_dev_iii_senior(store):
    r = _title(store, "Full Stack Developer III", "hris")
    assert r["role"] == "Full Stack Developer"
    assert r["level"] == "senior"
    assert r["level_label"] == "stated"


# ── TC32: Rejection ───────────────────────────────────────────────────


def test_tc32_data_analyst_rejected(store):
    r = _title(store, "Data Analyst", "jobboard")
    assert r["rejected"] is True
    assert "reason" in r


def test_random_nonsense_rejected(store):
    r = _title(store, "Chief Happiness Officer", "ats")
    assert r["rejected"] is True


# ── TC13: Skill normalization ─────────────────────────────────────────


def test_tc13_k8s_to_kubernetes(store):
    assert _skill(store, "k8s")["skill_id"] == "kubernetes"


def test_reactjs_to_react(store):
    assert _skill(store, "ReactJS")["skill_id"] == "react"


def test_node_js_to_nodejs(store):
    assert _skill(store, "node js")["skill_id"] == "nodejs"


def test_exact_skill(store):
    assert _skill(store, "terraform")["skill_id"] == "terraform"


# ── TC14: Unknown skill ───────────────────────────────────────────────


def test_tc14_blorkify_unknown(store):
    r = _skill(store, "Blorkify")
    assert r["unknown"] is True


def test_random_skill_unknown(store):
    r = _skill(store, "Quantum Basket Weaving")
    assert r["unknown"] is True


# ── Skill relation ────────────────────────────────────────────────────


def test_docker_kubernetes_adjacent(store):
    r = skill_relation("docker", "kubernetes", store.reference.skill_edges())
    assert r is not None
    assert r[0] == "adjacent"
    assert r[1] == 0.5


def test_nextjs_react_child(store):
    r = skill_relation("nextjs", "react", store.reference.skill_edges())
    assert r is not None
    assert r[0] == "child"


def test_unrelated_skills_none(store):
    r = skill_relation("react", "kafka", store.reference.skill_edges())
    assert r is None


# ── Title normalization panel ─────────────────────────────────────────


def test_panel_structure(store):
    panel = title_normalization_panel(
        store.reference.title_aliases(),
        store.reference.canonical_roles(),
    )
    assert panel["raw_titles_count"] == 12
    assert panel["role"] == "Full Stack Developer"
    assert set(panel["levels"]) == {"junior", "mid", "senior", "lead"}
    assert len(panel["mappings"]) == 12


def test_panel_all_have_esco_uri(store):
    panel = title_normalization_panel(
        store.reference.title_aliases(),
        store.reference.canonical_roles(),
    )
    for m in panel["mappings"]:
        assert m["esco_uri"] == ESCO_URI


def test_panel_has_all_source_systems(store):
    panel = title_normalization_panel(
        store.reference.title_aliases(),
        store.reference.canonical_roles(),
    )
    systems = {m["source_system"] for m in panel["mappings"]}
    assert systems >= {"hris", "ats", "vms", "jobboard"}
