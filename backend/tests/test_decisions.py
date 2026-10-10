"""Tests for decisions.py — Decision Log validation and recording.

TC22  Empty or whitespace reason → ValueError
      Append-only: multiple decisions, all preserved
      inputs_hash stable for identical inputs
      inputs_hash changes with different relaxed_mask
      Invalid option_id → ValueError
      Missing req_id → ValueError
      Invalid verb → ValueError
      Empty decided_by → ValueError
      Verb stored with option in chosen_option column
"""
from __future__ import annotations

import pytest

from backend.db import Database
from backend.decisions import record_decision


@pytest.fixture()
def db(tmp_path):
    return Database(tmp_path / "test.sqlite")


VALID_OPTIONS = ["mix", "build", "borrow", "relocate", "buy",
                 "mix-1", "mix-2", "mix-3"]

PARSED_JSON = {"level": "senior", "skills": ["react", "nodejs", "kubernetes"]}
OPTIONS_JSON = {"five": [{"id": "mix", "score": 89}], "mixes": []}
MASK = "00000"


def _setup_req(db, req_id="REQ-T01"):
    db.save_requisition(req_id, "Full Stack Developer", "senior",
                        "bengaluru", "onsite", '{"level":"senior"}')


# ── TC22: Empty or whitespace reason ─────────────────────────────────────────


def test_empty_reason_raises(db):
    _setup_req(db)
    with pytest.raises(ValueError, match="[Rr]eason"):
        record_decision(db, "REQ-T01", "mix", "Approve", MASK,
                        "approver", "", VALID_OPTIONS, PARSED_JSON,
                        OPTIONS_JSON)


def test_whitespace_reason_raises(db):
    _setup_req(db)
    with pytest.raises(ValueError, match="[Rr]eason"):
        record_decision(db, "REQ-T01", "mix", "Approve", MASK,
                        "approver", "   \t\n", VALID_OPTIONS, PARSED_JSON,
                        OPTIONS_JSON)


# ── decided_by must be non-empty ──────────────────────────────────────────────


def test_empty_decided_by_raises(db):
    _setup_req(db)
    with pytest.raises(ValueError, match="[Aa]pprover"):
        record_decision(db, "REQ-T01", "mix", "Approve", MASK,
                        "", "good reason", VALID_OPTIONS, PARSED_JSON,
                        OPTIONS_JSON)


def test_whitespace_decided_by_raises(db):
    _setup_req(db)
    with pytest.raises(ValueError, match="[Aa]pprover"):
        record_decision(db, "REQ-T01", "mix", "Approve", MASK,
                        "   \t", "good reason", VALID_OPTIONS, PARSED_JSON,
                        OPTIONS_JSON)


# ── req_id must exist ────────────────────────────────────────────────────────


def test_missing_req_raises(db):
    with pytest.raises(ValueError, match="not found"):
        record_decision(db, "REQ-MISSING", "mix", "Approve", MASK,
                        "approver", "good reason", VALID_OPTIONS,
                        PARSED_JSON, OPTIONS_JSON)


# ── option_id must be valid ──────────────────────────────────────────────────


def test_invalid_option_raises(db):
    _setup_req(db)
    with pytest.raises(ValueError, match="[Ii]nvalid"):
        record_decision(db, "REQ-T01", "nonexistent", "Approve", MASK,
                        "approver", "good reason", VALID_OPTIONS,
                        PARSED_JSON, OPTIONS_JSON)


# ── verb must be valid ───────────────────────────────────────────────────────


def test_invalid_verb_raises(db):
    _setup_req(db)
    with pytest.raises(ValueError, match="[Ii]nvalid verb"):
        record_decision(db, "REQ-T01", "mix", "Destroy", MASK,
                        "approver", "good reason", VALID_OPTIONS,
                        PARSED_JSON, OPTIONS_JSON)


def test_all_valid_verbs_accepted(db):
    _setup_req(db)
    for verb in ("Approve", "Modify", "Reject"):
        result = record_decision(db, "REQ-T01", "mix", verb, MASK,
                                 "approver", f"reason for {verb}",
                                 VALID_OPTIONS, PARSED_JSON, OPTIONS_JSON)
        assert result["verb"] == verb


# ── Happy path ───────────────────────────────────────────────────────────────


def test_decision_recorded(db):
    _setup_req(db)
    result = record_decision(db, "REQ-T01", "mix", "Approve", MASK,
                             "Manager A", "Best balance of speed and cost",
                             VALID_OPTIONS, PARSED_JSON, OPTIONS_JSON)
    assert result["status"] == "recorded"
    assert result["req_id"] == "REQ-T01"
    assert result["option_id"] == "mix"
    assert result["verb"] == "Approve"
    assert result["inputs_hash"]

    rows = db.get_decisions("REQ-T01")
    assert len(rows) == 1
    assert rows[0]["chosen_option"] == "Approve mix"
    assert rows[0]["decided_by"] == "Manager A"
    assert rows[0]["reason"] == "Best balance of speed and cost"


# ── Verb stored with option ──────────────────────────────────────────────────


def test_verb_stored_with_option(db):
    _setup_req(db, "REQ-T06")
    record_decision(db, "REQ-T06", "build", "Reject", MASK,
                    "reviewer", "Too risky", VALID_OPTIONS, PARSED_JSON,
                    OPTIONS_JSON)
    rows = db.get_decisions("REQ-T06")
    assert rows[0]["chosen_option"] == "Reject build"


# ── Append-only ──────────────────────────────────────────────────────────────


def test_append_only(db):
    _setup_req(db, "REQ-T02")
    record_decision(db, "REQ-T02", "mix", "Approve", MASK,
                    "A", "reason1", VALID_OPTIONS, PARSED_JSON, OPTIONS_JSON)
    record_decision(db, "REQ-T02", "build", "Modify", MASK,
                    "B", "reason2", VALID_OPTIONS, PARSED_JSON, OPTIONS_JSON)
    rows = db.get_decisions("REQ-T02")
    assert len(rows) == 2
    assert rows[0]["chosen_option"] == "Approve mix"
    assert rows[1]["chosen_option"] == "Modify build"


# ── inputs_hash stability ────────────────────────────────────────────────────


def test_inputs_hash_stable(db):
    _setup_req(db, "REQ-T03")
    r1 = record_decision(db, "REQ-T03", "mix", "Approve", MASK,
                          "A", "reason1", VALID_OPTIONS, PARSED_JSON,
                          OPTIONS_JSON)
    r2 = record_decision(db, "REQ-T03", "mix", "Approve", MASK,
                          "B", "reason2", VALID_OPTIONS, PARSED_JSON,
                          OPTIONS_JSON)
    assert r1["inputs_hash"] == r2["inputs_hash"]


def test_inputs_hash_changes_with_different_parsed(db):
    _setup_req(db, "REQ-T04")
    r1 = record_decision(db, "REQ-T04", "mix", "Approve", MASK,
                          "A", "reason", VALID_OPTIONS, PARSED_JSON,
                          OPTIONS_JSON)
    different_parsed = {"level": "mid", "skills": ["react"]}
    r2 = record_decision(db, "REQ-T04", "mix", "Approve", MASK,
                          "A", "reason", VALID_OPTIONS, different_parsed,
                          OPTIONS_JSON)
    assert r1["inputs_hash"] != r2["inputs_hash"]


def test_inputs_hash_changes_with_different_mask(db):
    """Same requisition, different relaxed_mask → different hash."""
    _setup_req(db, "REQ-T07")
    r1 = record_decision(db, "REQ-T07", "mix", "Approve", "00000",
                          "A", "reason", VALID_OPTIONS, PARSED_JSON,
                          OPTIONS_JSON)
    r2 = record_decision(db, "REQ-T07", "mix", "Approve", "10100",
                          "A", "reason", VALID_OPTIONS, PARSED_JSON,
                          OPTIONS_JSON)
    assert r1["inputs_hash"] != r2["inputs_hash"]


def test_inputs_hash_changes_with_different_options(db):
    """Same parsed + mask, different option table → different hash."""
    _setup_req(db, "REQ-T08")
    r1 = record_decision(db, "REQ-T08", "mix", "Approve", MASK,
                          "A", "reason", VALID_OPTIONS, PARSED_JSON,
                          OPTIONS_JSON)
    different_opts = {"five": [{"id": "buy", "score": 42}], "mixes": []}
    r2 = record_decision(db, "REQ-T08", "mix", "Approve", MASK,
                          "A", "reason", VALID_OPTIONS, PARSED_JSON,
                          different_opts)
    assert r1["inputs_hash"] != r2["inputs_hash"]


# ── Reason is trimmed ────────────────────────────────────────────────────────


def test_reason_trimmed(db):
    _setup_req(db, "REQ-T05")
    record_decision(db, "REQ-T05", "mix", "Approve", MASK,
                    "A", "  trimmed reason  ", VALID_OPTIONS, PARSED_JSON,
                    OPTIONS_JSON)
    rows = db.get_decisions("REQ-T05")
    assert rows[0]["reason"] == "trimmed reason"
