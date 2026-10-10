"""HRIS adapter — employees, skills, projects, assignments, exits."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def _to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False})


class HRIS:

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._employees = pd.read_csv(data_dir / "employees.csv")
        self._employees["open_to_move"] = _to_bool(self._employees["open_to_move"])
        self._employees["is_active"] = _to_bool(self._employees["is_active"])
        self._employees["years_exp"] = self._employees["years_exp"].astype(float)
        self._employees["rating"] = self._employees["rating"].astype(int)

        self._emp_skills = pd.read_csv(data_dir / "employee_skills.csv")

        self._projects = pd.read_csv(data_dir / "projects.csv")
        self._projects["is_critical"] = _to_bool(self._projects["is_critical"])

        self._assignments = pd.read_csv(data_dir / "project_assignments.csv")

        self._exits = pd.read_csv(data_dir / "exits.csv")
        self._exits["tenure_months"] = self._exits["tenure_months"].astype(int)

    def employees(self) -> pd.DataFrame:
        return self._employees.copy()

    def employee_skills(self) -> dict[str, set[str]]:
        sk: dict[str, set[str]] = {}
        for _, r in self._emp_skills.iterrows():
            sk.setdefault(r["employee_id"], set()).add(r["skill_id"])
        return sk

    def person(self, person_id: str) -> dict:
        row = self._employees[self._employees.employee_id == person_id]
        if row.empty:
            raise KeyError(f"Employee {person_id} not found")
        return row.iloc[0].to_dict()

    def projects(self) -> pd.DataFrame:
        return self._projects.copy()

    def project_assignments(self) -> dict[str, set[str]]:
        asgn: dict[str, set[str]] = {}
        for _, r in self._assignments.iterrows():
            asgn.setdefault(r["employee_id"], set()).add(r["project_id"])
        return asgn

    def exits(self) -> pd.DataFrame:
        return self._exits.copy()
