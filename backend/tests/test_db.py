"""Tests for db.py — SQLite tables, parameterized queries, append-only Decision."""
import sqlite3
from pathlib import Path

import pytest

from backend.db import Database


@pytest.fixture()
def db(tmp_path):
    return Database(tmp_path / "test.sqlite")


# ── Table creation ───────────────────────────────────────────────────


def test_tables_created(db):
    tables = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {t[0] for t in tables}
    assert {"Requisition", "ReqConstraint", "ReqSkill",
            "Scenario", "Decision"} <= names


# ── Requisition CRUD ─────────────────────────────────────────────────


def test_save_and_load_requisition(db):
    db.save_requisition("REQ-T01", "Full Stack Developer", "senior",
                        "bengaluru", "onsite", '{"raw":"text"}')
    row = db.get_requisition("REQ-T01")
    assert row is not None
    assert row["role"] == "Full Stack Developer"
    assert row["level"] == "senior"


def test_get_missing_requisition(db):
    assert db.get_requisition("REQ-NOPE") is None


# ── ReqConstraint ────────────────────────────────────────────────────


def test_save_and_load_constraints(db):
    db.save_requisition("REQ-T02", "FSD", "senior", "bengaluru", "onsite", "{}")
    db.save_constraints("REQ-T02", [
        {"kind": "location", "value": "bengaluru", "source": "stated"},
        {"kind": "skill", "value": "kubernetes", "source": "inferred"},
    ])
    rows = db.get_constraints("REQ-T02")
    assert len(rows) == 2
    assert rows[0]["kind"] == "location"


# ── ReqSkill ─────────────────────────────────────────────────────────


def test_save_and_load_skills(db):
    db.save_requisition("REQ-T03", "FSD", "senior", "bengaluru", "onsite", "{}")
    db.save_skills("REQ-T03", [
        {"skill_id": "react", "importance": "must", "confidence": 0.95},
        {"skill_id": "kubernetes", "importance": "must", "confidence": 0.8},
    ])
    rows = db.get_skills("REQ-T03")
    assert len(rows) == 2
    assert rows[0]["skill_id"] == "react"


# ── Scenario ─────────────────────────────────────────────────────────


def test_save_and_load_scenario(db):
    db.save_requisition("REQ-T04", "FSD", "senior", "bengaluru", "onsite", "{}")
    db.save_scenario("REQ-T04", "00000", '{"supply":14}')
    db.save_scenario("REQ-T04", "10000", '{"supply":210}')
    rows = db.get_scenarios("REQ-T04")
    assert len(rows) == 2
    assert rows[0]["relaxed_mask"] == "00000"


# ── Decision (append-only) ───────────────────────────────────────────


def test_append_decision(db):
    db.save_requisition("REQ-T05", "FSD", "senior", "bengaluru", "onsite", "{}")
    db.append_decision("REQ-T05", "mix", "manager@co.in",
                       "Best balance of speed and cost", "abc123")
    rows = db.get_decisions("REQ-T05")
    assert len(rows) == 1
    assert rows[0]["chosen_option"] == "mix"
    assert rows[0]["decided_by"] == "manager@co.in"
    assert rows[0]["reason"] == "Best balance of speed and cost"
    assert rows[0]["inputs_hash"] == "abc123"
    assert rows[0]["decided_at"] is not None


def test_decision_append_multiple(db):
    db.save_requisition("REQ-T06", "FSD", "senior", "bengaluru", "onsite", "{}")
    db.append_decision("REQ-T06", "buy", "a@co.in", "Quick hire", "h1")
    db.append_decision("REQ-T06", "mix", "b@co.in", "Changed mind", "h2")
    rows = db.get_decisions("REQ-T06")
    assert len(rows) == 2


def test_no_update_decision(db):
    assert not hasattr(db, "update_decision")


def test_no_delete_decision(db):
    assert not hasattr(db, "delete_decision")


# ── SQL injection safety ─────────────────────────────────────────────


def test_sql_injection_in_reason(db):
    """A malicious string stored as a reason round-trips as plain text."""
    db.save_requisition("REQ-T07", "FSD", "senior", "bengaluru", "onsite", "{}")
    evil = "x'); DROP TABLE Decision;--"
    db.append_decision("REQ-T07", "buy", "attacker", evil, "h1")
    rows = db.get_decisions("REQ-T07")
    assert len(rows) == 1
    assert rows[0]["reason"] == evil
    # Decision table still exists
    count = db.conn.execute("SELECT COUNT(*) FROM Decision").fetchone()[0]
    assert count >= 1


def test_sql_injection_in_requisition(db):
    evil_role = "'; DROP TABLE Requisition;--"
    db.save_requisition("REQ-T08", evil_role, "senior", "bengaluru", "onsite", "{}")
    row = db.get_requisition("REQ-T08")
    assert row["role"] == evil_role
    count = db.conn.execute("SELECT COUNT(*) FROM Requisition").fetchone()[0]
    assert count >= 1
