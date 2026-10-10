"""Shared fixtures — session-scoped seed generation into a temp directory."""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.data.seed import main as seed_main
from backend.db import DEFAULT_DB_PATH
from backend.store import DataStore


@pytest.fixture(scope="session")
def seed_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    d = tmp_path_factory.mktemp("seed")
    seed_main(output_dir=d)
    return d


@pytest.fixture(scope="session")
def store(seed_dir: Path) -> DataStore:
    return DataStore(data_dir=seed_dir)


@pytest.fixture(scope="session", autouse=True)
def _patch_test_db(tmp_path_factory: pytest.TempPathFactory):
    """Redirect all DB writes to a temp file so tests never touch talentlens.sqlite."""
    import backend.api.main as _main
    _main._db_path = tmp_path_factory.mktemp("testdb") / "test.sqlite"
    yield
    _main._db_path = DEFAULT_DB_PATH
