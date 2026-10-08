"""Tests for reference data, taxonomy files, and automation tasks."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "backend" / "cache"
TAXONOMY_DIR = PROJECT_ROOT / "backend" / "data" / "taxonomy"


def _read_csv(name: str) -> list[dict]:
    path = TAXONOMY_DIR / name
    assert path.exists(), f"{name} not found at {path}"
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ── reference.json ─────────────────────────────────────────────────────

class TestReferenceJson:
    @pytest.fixture(autouse=True)
    def load(self):
        path = CACHE_DIR / "reference.json"
        assert path.exists(), "reference.json not found — run fetch_reference.py first"
        self.ref = json.loads(path.read_text(encoding="utf-8"))

    def test_esco_essential_count(self):
        assert len(self.ref["esco_essential"]) >= 20

    def test_esco_essential_has_titles(self):
        for item in self.ref["esco_essential"]:
            assert "title" in item
            assert "uri" in item

    def test_onet_tasks_both_codes(self):
        assert "15-1254.00" in self.ref["onet_tasks"]
        assert "15-1252.00" in self.ref["onet_tasks"]
        for code in ("15-1254.00", "15-1252.00"):
            assert len(self.ref["onet_tasks"][code]) > 0

    def test_onet_tech_both_codes(self):
        assert "15-1254.00" in self.ref["onet_tech"]
        assert "15-1252.00" in self.ref["onet_tech"]
        for code in ("15-1254.00", "15-1252.00"):
            assert len(self.ref["onet_tech"][code]) > 0

    def test_onet_titles_both_codes(self):
        assert "15-1254.00" in self.ref["onet_titles"]
        assert "15-1252.00" in self.ref["onet_titles"]

    def test_has_fetched_on(self):
        assert "fetched_on" in self.ref

    def test_has_onet_version(self):
        assert "onet_version" in self.ref

    def test_has_esco_uris(self):
        assert self.ref["esco_software_developer_uri"] == (
            "http://data.europa.eu/esco/occupation/"
            "f2b15a0e-e65a-438a-affb-29b9d50b77d1"
        )


# ── skills.csv ─────────────────────────────────────────────────────────

class TestSkillsCsv:
    @pytest.fixture(autouse=True)
    def load(self):
        self.rows = _read_csv("skills.csv")

    def test_count_28_to_32(self):
        assert 28 <= len(self.rows) <= 32, f"Got {len(self.rows)} skills"

    def test_unique_ids(self):
        ids = [r["id"] for r in self.rows]
        assert len(ids) == len(set(ids)), "Duplicate skill IDs"

    def test_required_skills_present(self):
        ids = {r["id"] for r in self.rows}
        required = {
            "react", "nodejs", "kubernetes", "aws", "graphql",
            "terraform", "docker", "typescript", "javascript",
            "nextjs", "express",
        }
        missing = required - ids
        assert not missing, f"Missing required skills: {missing}"


# ── skill_alias.csv ────────────────────────────────────────────────────

class TestSkillAliasCsv:
    @pytest.fixture(autouse=True)
    def load(self):
        self.rows = _read_csv("skill_alias.csv")
        self.skill_ids = {r["id"] for r in _read_csv("skills.csv")}

    def test_all_point_to_known_skills(self):
        for row in self.rows:
            assert row["skill_id"] in self.skill_ids, (
                f"Alias '{row['alias']}' → unknown skill '{row['skill_id']}'"
            )

    def test_key_aliases(self):
        alias_map = {r["alias"].lower(): r["skill_id"] for r in self.rows}
        assert alias_map.get("k8s") == "kubernetes"
        assert alias_map.get("nodejs") == "nodejs"
        assert alias_map.get("reactjs") == "react"


# ── skill_edges.csv ────────────────────────────────────────────────────

class TestSkillEdgesCsv:
    @pytest.fixture(autouse=True)
    def load(self):
        self.rows = _read_csv("skill_edges.csv")
        self.skill_ids = {r["id"] for r in _read_csv("skills.csv")}

    def test_all_skills_known(self):
        for row in self.rows:
            assert row["skill_a"] in self.skill_ids, (
                f"Edge skill_a '{row['skill_a']}' unknown"
            )
            assert row["skill_b"] in self.skill_ids, (
                f"Edge skill_b '{row['skill_b']}' unknown"
            )

    def test_valid_types(self):
        valid = {"child", "adjacent", "requires"}
        for row in self.rows:
            assert row["type"] in valid, f"Invalid edge type: {row['type']}"

    def test_key_edges(self):
        edges = {(r["skill_a"], r["skill_b"], r["type"]) for r in self.rows}
        assert ("nextjs", "react", "child") in edges
        assert ("docker", "kubernetes", "adjacent") in edges
        assert ("express", "nodejs", "requires") in edges


# ── title_alias.csv ────────────────────────────────────────────────────

class TestTitleAliasCsv:
    @pytest.fixture(autouse=True)
    def load(self):
        self.rows = _read_csv("title_alias.csv")

    def test_all_four_source_systems(self):
        systems = {r["source_system"] for r in self.rows}
        assert systems >= {"hris", "ats", "vms", "jobboard"}, (
            f"Missing source systems: {{'hris','ats','vms','jobboard'}} - {systems}"
        )

    def test_twelve_seed_titles(self):
        titles = {r["raw_title"] for r in self.rows}
        required = {
            "SDE-2 (Full Stack)",
            "MERN Stack Developer",
            "Full-Stack Engineer – Contract",
            "Web Developer",
            "Sr. Full Stack Developer",
            "Full Stack Developer III",
            "Lead Full Stack Engineer",
            "SDE-1",
            "React + Node Developer",
            "MEAN Stack Developer",
            "Full Stack Web Developer",
            "SDE-3 (Full Stack)",
        }
        missing = required - titles
        assert not missing, f"Missing seed titles: {missing}"

    def test_valid_methods(self):
        valid = {"esco_alt", "onet", "manual", "fuzzy"}
        for row in self.rows:
            assert row["method"] in valid, f"Invalid method: {row['method']}"


# ── automation_tasks.json ──────────────────────────────────────────────

class TestAutomationTasks:
    @pytest.fixture(autouse=True)
    def load(self):
        path = CACHE_DIR / "automation_tasks.json"
        if not path.exists():
            pytest.skip("automation_tasks.json not found — run score_automation.py first")
        self.tasks = json.loads(path.read_text(encoding="utf-8"))

    def test_has_tasks(self):
        assert len(self.tasks) > 0

    def test_time_shares_sum_to_one(self):
        by_code: dict[str, float] = {}
        for t in self.tasks:
            by_code[t["onet_code"]] = by_code.get(t["onet_code"], 0) + t["time_share"]
        for code, total in by_code.items():
            assert abs(total - 1.0) < 0.01, (
                f"Time shares for {code} sum to {total}, expected ~1.0"
            )

    def test_required_fields(self):
        for t in self.tasks:
            assert "task_id" in t
            assert "onet_code" in t
            assert "task" in t
            assert "time_share" in t
            assert "potential" in t
            assert "rationale" in t
            assert "reviewed" in t
