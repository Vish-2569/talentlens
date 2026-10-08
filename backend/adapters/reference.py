"""ReferenceCache adapter — reads taxonomy CSVs and cache JSON files. Never calls network."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR = Path(__file__).parent.parent / "cache"
TAXONOMY_DIR = DATA_DIR / "taxonomy"


class ReferenceCache:

    def __init__(self, taxonomy_dir: Path = TAXONOMY_DIR,
                 cache_dir: Path = CACHE_DIR) -> None:
        self._skills = pd.read_csv(taxonomy_dir / "skills.csv")
        self._skill_aliases = pd.read_csv(taxonomy_dir / "skill_alias.csv")
        self._skill_edges = pd.read_csv(taxonomy_dir / "skill_edges.csv")
        self._title_aliases = pd.read_csv(taxonomy_dir / "title_alias.csv")

        with open(taxonomy_dir / "canonical_role.json", encoding="utf-8") as f:
            self._canonical_roles: list[dict] = json.load(f)

        with open(cache_dir / "reference.json", encoding="utf-8") as f:
            self._reference: dict = json.load(f)

        with open(cache_dir / "automation_tasks.json", encoding="utf-8") as f:
            self._automation_tasks: list[dict] = json.load(f)

    def skills(self) -> pd.DataFrame:
        return self._skills.copy()

    def skill_aliases(self) -> pd.DataFrame:
        return self._skill_aliases.copy()

    def skill_edges(self) -> pd.DataFrame:
        return self._skill_edges.copy()

    def title_aliases(self) -> pd.DataFrame:
        return self._title_aliases.copy()

    def canonical_roles(self) -> list[dict]:
        return [r.copy() for r in self._canonical_roles]

    def reference(self) -> dict:
        return self._reference.copy()

    def automation_tasks(self) -> list[dict]:
        return [t.copy() for t in self._automation_tasks]
