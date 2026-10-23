"""Sample dataset catalog (data/sample/catalog.json, written by scripts/generate_sample_data.py)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .config import ROOT_DIR

SAMPLE_DIR = ROOT_DIR / "data" / "sample"


@dataclass(frozen=True)
class SampleDataset:
    id: str
    file: str
    title: str
    domain: str
    currency: str
    number_style: str
    description: str
    questions: list[str] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return SAMPLE_DIR / self.file


@lru_cache(maxsize=1)
def load_catalog() -> tuple[SampleDataset, ...]:
    path = SAMPLE_DIR / "catalog.json"
    if not path.exists():
        return ()
    return tuple(SampleDataset(**item) for item in json.loads(path.read_text(encoding="utf-8")))


def get_sample(sample_id: str) -> SampleDataset | None:
    return next((s for s in load_catalog() if s.id == sample_id), None)
