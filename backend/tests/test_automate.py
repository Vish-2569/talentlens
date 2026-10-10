"""Tests for engine/automate.py — automation potential estimation."""
import pytest

from backend.engine.automate import estimate_automation


# ── 25-35% range with production tasks ──────────────────────────────


def test_hours_saved_25_to_35(store):
    tasks = store.reference.automation_tasks()
    result = estimate_automation(tasks)
    assert 25.0 <= result["hours_saved_pct"] <= 35.0, (
        f"Expected 25-35%, got {result['hours_saved_pct']:.2f}%"
    )


# ── Range is ±30% of central estimate ───────────────────────────────


def test_range_plus_minus_30pct(store):
    tasks = store.reference.automation_tasks()
    result = estimate_automation(tasks)
    pct = result["hours_saved_pct"]
    assert abs(result["range_low"] - pct * 0.70) < 0.01
    assert abs(result["range_high"] - pct * 1.30) < 0.01


# ── headcount=1 → not a replacement ─────────────────────────────────


def test_headcount_1_not_replacement(store):
    tasks = store.reference.automation_tasks()
    result = estimate_automation(tasks, headcount=1)
    assert result["replacement"] is False


def test_headcount_gt1_replacement():
    tasks = [{"task_id": "1", "time_share": 0.5, "potential": 0.5}]
    result = estimate_automation(tasks, headcount=2)
    assert result["replacement"] is True


# ── Returns task breakdown ───────────────────────────────────────────


def test_returns_task_breakdown(store):
    tasks = store.reference.automation_tasks()
    result = estimate_automation(tasks)
    assert len(result["task_breakdown"]) == len(tasks)
    assert all("task_id" in t for t in result["task_breakdown"])


# ── Returns evidence IDs ─────────────────────────────────────────────


def test_returns_evidence_ids(store):
    tasks = store.reference.automation_tasks()
    result = estimate_automation(tasks)
    assert len(result["evidence_ids"]) > 0
