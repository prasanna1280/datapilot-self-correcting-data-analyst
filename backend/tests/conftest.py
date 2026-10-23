from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from backend.datapilot import config, executors, runner, team
from backend.datapilot.data_loader import read_upload
from database import Database

SAMPLE_CSV = Path(__file__).resolve().parents[2] / "data" / "sample" / "sales_2026.csv"


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    """Point runtime folders + DB at tmp, force the local executor."""
    s = dataclasses.replace(
        config.settings, runtime_dir=tmp_path / "runtime", db_path=tmp_path / "test.db",
        executor_mode="local", max_messages=12,
    )
    for mod in (config, executors, runner, team):
        monkeypatch.setattr(mod, "settings", s)
    return s


@pytest.fixture
def db(isolated_settings):
    return Database(isolated_settings.db_path)


@pytest.fixture
def sales_df():
    return read_upload(SAMPLE_CSV.name, SAMPLE_CSV.read_bytes())
