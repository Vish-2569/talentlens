"""Tests for engine/borrow.py — contractor extension/conversion analysis."""
import pytest
from datetime import date

from backend.data.seed import main as seed_main
from backend.engine.borrow import (
    extension_cost, conversion_saving, conversion_signal,
    compliance_flag, availability_text, analyze_contractor,
)
from backend.store import DataStore

TODAY = date(2026, 9, 1)


@pytest.fixture(scope="module", autouse=True)
def generate():
    seed_main()


@pytest.fixture(scope="module")
def store():
    return DataStore()


# ── Extension costs ──────────────────────────────────────────────────


def test_extension_12m_24L():
    assert extension_cost(24.0, 12) == 24.0


def test_extension_3m_6L():
    assert extension_cost(24.0, 3) == 6.0


# ── Conversion ───────────────────────────────────────────────────────


def test_conversion_signal_true():
    assert conversion_signal(date(2025, 7, 1), TODAY) is True


def test_conversion_signal_false_short_tenure():
    assert conversion_signal(date(2026, 3, 1), TODAY) is False


# ── Compliance ───────────────────────────────────────────────────────


def test_compliance_flag_false(store):
    projects = store.hris.projects()
    pa = store.hris.project_assignments()
    result = compliance_flag("C-17", pa, projects)
    assert result is False


def test_compliance_flag_true_for_critical_project(store):
    projects = store.hris.projects()
    fake_pa = {"C-17": {"PROJ-01"}}
    result = compliance_flag("C-17", fake_pa, projects)
    assert result is True


# ── Availability ─────────────────────────────────────────────────────


def test_availability_4_weeks():
    text = availability_text(date(2026, 9, 29), TODAY)
    assert "4 weeks" in text


# ── Full analysis ────────────────────────────────────────────────────


def test_analyze_arjun(store):
    projects = store.hris.projects()
    pa = store.hris.project_assignments()
    result = analyze_contractor(
        "C-17", 24.0,
        start_date=date(2025, 7, 1),
        end_date=date(2026, 9, 29),
        fit_score=84,
        project_assignments=pa,
        projects_df=projects,
        today=TODAY,
    )
    assert result["extend_cost_12m"] == 24.0
    assert result["extend_cost_3m"] == 6.0
    assert result["conversion_signal"] is True
    assert result["compliance_flag"] is False
    assert "4 weeks" in result["availability"]
