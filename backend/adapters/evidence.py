"""Evidence adapter — skill evidence records for Skill Evidence Tags."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


class EvidenceAdapter:

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self._evidence = pd.read_csv(data_dir / "evidence.csv")

    def skill_evidence(self, person_id: str | None = None) -> pd.DataFrame:
        if person_id is not None:
            return self._evidence[self._evidence.person_id == person_id].copy()
        return self._evidence.copy()
