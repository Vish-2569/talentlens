"""ATS adapter — candidates, skills, requisitions, finalists, sourcing."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def _to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().map({"true": True, "false": False})


class ATS:

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._candidates = pd.read_csv(data_dir / "candidates.csv")
        self._candidates["years_exp"] = self._candidates["years_exp"].astype(float)

        self._cand_skills = pd.read_csv(data_dir / "candidate_skills.csv")

        self._requisitions = pd.read_csv(data_dir / "requisitions.csv")
        self._requisitions["time_to_fill_days"] = (
            self._requisitions["time_to_fill_days"].astype(int))
        self._requisitions["first_year_cost_lpa"] = (
            self._requisitions["first_year_cost_lpa"].astype(float))

        self._finalists = pd.read_csv(data_dir / "past_finalists.csv")
        self._finalists["open_to_remote"] = _to_bool(self._finalists["open_to_remote"])
        self._finalists["opted_in_pool"] = _to_bool(self._finalists["opted_in_pool"])

        self._sourcing = pd.read_csv(data_dir / "sourcing_history.csv")
        self._sourcing["fill_rate"] = pd.to_numeric(
            self._sourcing["fill_rate"], errors="coerce")
        self._sourcing["median_days"] = pd.to_numeric(
            self._sourcing["median_days"], errors="coerce").astype("Int64")

    def candidates(self) -> pd.DataFrame:
        return self._candidates.copy()

    def candidate_skills(self) -> dict[str, set[str]]:
        sk: dict[str, set[str]] = {}
        for _, r in self._cand_skills.iterrows():
            sk.setdefault(r["candidate_id"], set()).add(r["skill_id"])
        return sk

    def requisitions(self) -> pd.DataFrame:
        return self._requisitions.copy()

    def past_finalists(self) -> pd.DataFrame:
        return self._finalists.copy()

    def sourcing_history(self) -> pd.DataFrame:
        return self._sourcing.copy()
