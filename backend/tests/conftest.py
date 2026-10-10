"""Shared fixtures — session-scoped seed generation into a temp directory."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.data.seed import main as seed_main
from backend.store import DataStore


@pytest.fixture(scope="session")
def seed_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    d = tmp_path_factory.mktemp("seed")
    seed_main(output_dir=d)
    return d


@pytest.fixture(scope="session")
def store(seed_dir: Path) -> DataStore:
    return DataStore(data_dir=seed_dir)
