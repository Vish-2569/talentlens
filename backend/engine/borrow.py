"""Borrow (contractor) analysis — pure functions, no I/O."""
from __future__ import annotations

from datetime import date

import pandas as pd


def extension_cost(bill_rate_lpa: float, months: int) -> float:
    return round(bill_rate_lpa * months / 12, 2)


def conversion_saving(
    bill_rate_lpa: float,
    salary_lpa: float,
    msp_fee: float = 0.0,
    burden: float = 0.30,
    conversion_fee: float = 2.0,
) -> float:
    contractor_year = bill_rate_lpa + msp_fee
    fte_year = salary_lpa * (1.0 + burden) + conversion_fee
    return round(contractor_year - fte_year, 2)


def conversion_signal(start_date: date, today: date) -> bool:
    tenure_days = (today - start_date).days
    tenure_months = tenure_days / 30.44
    return tenure_months > 12


def compliance_flag(
    contractor_id: str,
    project_assignments: dict[str, set[str]],
    projects_df: pd.DataFrame,
) -> bool:
    critical_pids = set(
        projects_df[projects_df["is_critical"] == True]["project_id"]
    )
    assigned = project_assignments.get(contractor_id, set())
    return bool(assigned & critical_pids)


def availability_text(end_date: date, today: date) -> str:
    days = (end_date - today).days
    weeks = max(1, round(days / 7))
    return f"Contract ends in {weeks} weeks"


def analyze_contractor(
    contractor_id: str,
    bill_rate_lpa: float,
    start_date: date,
    end_date: date,
    fit_score: int,
    project_assignments: dict[str, set[str]],
    projects_df: pd.DataFrame,
    today: date = date(2026, 10, 8),
) -> dict:
    return {
        "person_id": contractor_id,
        "fit": fit_score,
        "extend_cost_12m": extension_cost(bill_rate_lpa, 12),
        "extend_cost_3m": extension_cost(bill_rate_lpa, 3),
        "conversion_signal": conversion_signal(start_date, today),
        "compliance_flag": compliance_flag(contractor_id, project_assignments, projects_df),
        "availability": availability_text(end_date, today),
    }
