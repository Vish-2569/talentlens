"""DataStore — single immutable object holding all adapters, built once at startup.

Engine modules receive data from DataStore only; they never import adapters or open files.
Names are joined onto pseudonymous IDs only at the API response layer via display_names().
"""
from __future__ import annotations

from pathlib import Path

from backend.adapters.hris import HRIS
from backend.adapters.ats import ATS
from backend.adapters.vms import VMS
from backend.adapters.evidence import EvidenceAdapter
from backend.adapters.market import MarketAdapter
from backend.adapters.reference import ReferenceCache
from backend.engine.match import build_edge_lookup

DATA_DIR = Path(__file__).parent / "data"
CACHE_DIR = Path(__file__).parent / "cache"
TAXONOMY_DIR = DATA_DIR / "taxonomy"


class DataStore:

    def __init__(self, data_dir: Path = DATA_DIR,
                 cache_dir: Path = CACHE_DIR,
                 taxonomy_dir: Path = TAXONOMY_DIR) -> None:
        self.hris = HRIS(data_dir)
        self.ats = ATS(data_dir)
        self.vms = VMS(data_dir)
        self.evidence = EvidenceAdapter(data_dir)
        self.market = MarketAdapter(data_dir)
        self.reference = ReferenceCache(taxonomy_dir, cache_dir)

        self.edge_lookup = build_edge_lookup(self.reference.skill_edges())

        self._name_map: dict[str, str] = {}
        for _, r in self.hris._employees.iterrows():
            self._name_map[r["employee_id"]] = r["display_name"]
        for _, r in self.vms._contractors.iterrows():
            self._name_map[r["contractor_id"]] = r["display_name"]

    def display_names(self, ids: list[str]) -> dict[str, str]:
        """Map pseudonymous IDs to display names. API layer only."""
        return {pid: self._name_map[pid]
                for pid in ids if pid in self._name_map}
