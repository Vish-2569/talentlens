"""Market adapter — market_stats for Redline/Relocate analysis."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class MarketAdapter:

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._stats = pd.read_csv(data_dir / "market_stats.csv")
        for col in ("demand", "ttf_p50", "ttf_p80"):
            self._stats[col] = self._stats[col].astype(int)
        for col in ("sal_p25", "sal_p50", "sal_p75", "col_index", "remote_share", "reloc_package_lpa"):
            if col in self._stats.columns:
                self._stats[col] = self._stats[col].astype(float)

    def market_stats(self) -> pd.DataFrame:
        return self._stats.copy()

    def stat(self, location: str, level: str) -> dict:
        row = self._stats[
            (self._stats.location == location) & (self._stats.level == level)]
        if row.empty:
            raise KeyError(f"No market stat for {location}/{level}")
        return row.iloc[0].to_dict()
