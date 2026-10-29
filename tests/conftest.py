from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.records import load_record

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "cases" / "example"


@pytest.fixture
def board() -> dict[str, Any]:
    return copy.deepcopy(load_record(EXAMPLE / "bakeries-c1.board.yaml"))


@pytest.fixture
def board2() -> dict[str, Any]:
    return copy.deepcopy(load_record(EXAMPLE / "bakeries-c2.board.yaml"))


@pytest.fixture
def manifest() -> dict[str, Any]:
    return copy.deepcopy(load_record(EXAMPLE / "sources.yaml"))
