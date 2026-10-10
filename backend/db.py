
"""SQLite persistence — parameterized queries only. Decision is append-only.

LLM cache lives separately in cache/llm_cache.sqlite (Phase 8).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "talentlens.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS Requisition (
    req_id       TEXT PRIMARY KEY,
    role         TEXT NOT NULL,
    level        TEXT NOT NULL,
    location     TEXT NOT NULL,
    work_mode    TEXT NOT NULL,
    raw_json     TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ReqConstraint (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id   TEXT NOT NULL REFERENCES Requisition(req_id),
    kind     TEXT NOT NULL,
    value    TEXT NOT NULL,
    source   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ReqSkill (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id     TEXT NOT NULL REFERENCES Requisition(req_id),
    skill_id   TEXT NOT NULL,
    importance TEXT NOT NULL,
    confidence REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS Scenario (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id       TEXT NOT NULL REFERENCES Requisition(req_id),
    relaxed_mask TEXT NOT NULL,
    outputs_json TEXT NOT NULL,
    UNIQUE(req_id, relaxed_mask)
);

CREATE TABLE IF NOT EXISTS Decision (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id        TEXT NOT NULL REFERENCES Requisition(req_id),
    chosen_option TEXT NOT NULL,
    decided_by    TEXT NOT NULL,
    reason        TEXT NOT NULL,
    decided_at    TEXT NOT NULL,
    inputs_hash   TEXT NOT NULL
);
"""


class Database:

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ── Requisition ──────────────────────────────────────────────────

    def save_requisition(self, req_id: str, role: str, level: str,
                         location: str, work_mode: str,
                         raw_json: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO Requisition "
            "(req_id, role, level, location, work_mode, raw_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (req_id, role, level, location, work_mode, raw_json),
        )
        self.conn.commit()

    def get_requisition(self, req_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM Requisition WHERE req_id = ?", (req_id,)
        ).fetchone()
        return dict(row) if row else None

    # ── ReqConstraint ────────────────────────────────────────────────

    def save_constraints(self, req_id: str,
                         constraints: list[dict]) -> None:
        self.conn.execute(
            "DELETE FROM ReqConstraint WHERE req_id = ?", (req_id,))
        self.conn.executemany(
            "INSERT INTO ReqConstraint (req_id, kind, value, source) "
            "VALUES (?, ?, ?, ?)",
            [(req_id, c["kind"], c["value"], c["source"])
             for c in constraints],
        )
        self.conn.commit()

    def get_constraints(self, req_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM ReqConstraint WHERE req_id = ? ORDER BY id",
            (req_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── ReqSkill ─────────────────────────────────────────────────────

    def save_skills(self, req_id: str, skills: list[dict]) -> None:
        self.conn.execute(
            "DELETE FROM ReqSkill WHERE req_id = ?", (req_id,))
        self.conn.executemany(
            "INSERT INTO ReqSkill (req_id, skill_id, importance, confidence) "
            "VALUES (?, ?, ?, ?)",
            [(req_id, s["skill_id"], s["importance"], s["confidence"])
             for s in skills],
        )
        self.conn.commit()

    def get_skills(self, req_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM ReqSkill WHERE req_id = ? ORDER BY id",
            (req_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Scenario ─────────────────────────────────────────────────────

    def save_scenario(self, req_id: str, relaxed_mask: str,
                      outputs_json: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO Scenario (req_id, relaxed_mask, outputs_json) "
            "VALUES (?, ?, ?)",
            (req_id, relaxed_mask, outputs_json),
        )
        self.conn.commit()

    def save_scenarios_batch(self, rows: list[tuple[str, str, str]]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO Scenario (req_id, relaxed_mask, outputs_json) "
            "VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()

    def get_scenarios(self, req_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM Scenario WHERE req_id = ? ORDER BY id",
            (req_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Decision (append-only: no update or delete) ──────────────────

    def append_decision(self, req_id: str, chosen_option: str,
                        decided_by: str, reason: str,
                        inputs_hash: str) -> None:
        self.conn.execute(
            "INSERT INTO Decision "
            "(req_id, chosen_option, decided_by, reason, decided_at, inputs_hash) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (req_id, chosen_option, decided_by, reason,
             datetime.now(timezone.utc).isoformat(), inputs_hash),
        )
        self.conn.commit()

    def get_decisions(self, req_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM Decision WHERE req_id = ? ORDER BY id",
            (req_id,),
        ).fetchall()
        return [dict(r) for r in rows]
