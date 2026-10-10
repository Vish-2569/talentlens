"""VMS adapter — contractors, contractor skills, suppliers."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class VMS:

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._contractors = pd.read_csv(data_dir / "contractors.csv")
        self._contractors["bill_rate_lpa"] = (
            self._contractors["bill_rate_lpa"].astype(float))

        self._ctr_skills = pd.read_csv(data_dir / "contractor_skills.csv")
        self._ctr_skills_map: dict[str, set[str]] = (
            self._ctr_skills.groupby("contractor_id")["skill_id"]
            .apply(set).to_dict()
        )

        self._suppliers = pd.read_csv(data_dir / "suppliers.csv")
        self._suppliers["fill_rate"] = self._suppliers["fill_rate"].astype(float)
        self._suppliers["median_days_to_submit"] = (
            self._suppliers["median_days_to_submit"].astype(int))
        self._suppliers["avg_bill_rate_lpa"] = (
            self._suppliers["avg_bill_rate_lpa"].astype(float))

    def contractors(self) -> pd.DataFrame:
        return self._contractors.copy()

    def contractor_skills(self) -> dict[str, set[str]]:
        return {k: set(v) for k, v in self._ctr_skills_map.items()}

    def suppliers(self) -> pd.DataFrame:
        return self._suppliers.copy()
