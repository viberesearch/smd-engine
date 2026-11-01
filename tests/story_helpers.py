"""Boards for the story tests: the invented Spectra Coffee case, and a small
board written to a temporary folder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smd_engine.records import dump_record, load_record
from smd_engine.story.model import Boards, load_boards

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "spectra_coffee"
BOARD = CASE / "spectra-coffee-c1.board.yaml"
STORIES = ("owner", "buyer", "bank", "successor-premortem")


def case_boards() -> Boards:
    return load_boards([BOARD])


def case_story(name: str) -> dict[str, Any]:
    return load_record(CASE / f"{name}.story.yaml")


def mini(
    tmp_path: Path,
    relations: list[dict[str, Any]] | None = None,
    extra: list[dict[str, Any]] | None = None,
) -> Boards:
    """p1 -> fn1 -> fn2 -> nb1 (a normality boundary) -> coop1 (a cooperation).
    `relations` replaces the default chain; `extra` adds elements."""
    chain = [
        {"from": "p1", "to": "fn1", "kind": "flow", "carries": "money"},
        {"from": "fn1", "to": "fn2", "kind": "flow", "carries": "product"},
        {"from": "fn2", "to": "nb1", "kind": "uses"},
        {"from": "coop1", "to": "nb1", "kind": "uses"},
    ]
    record = {
        "record": "board_set",
        "schema_version": "0.3",
        "id": "mini",
        "title": "mini",
        "date": "2026-11-01",
        "cycle": 1,
        "status": "draft",
        "elements": [
            {"id": "p1", "board": "od", "kind": "position", "label": "p"},
            {"id": "fn1", "board": "oo", "kind": "function", "label": "f1"},
            {"id": "fn2", "board": "oo", "kind": "function", "label": "f2"},
            {"id": "coop1", "board": "oo", "kind": "cooperation", "label": "c 3"},
            {
                "id": "nb1",
                "board": "s",
                "half": "small",
                "kind": "normality_boundary",
                "label": "n",
                "seen_from": "p1",
            },
            *(extra or []),
        ],
        "relations": chain if relations is None else relations,
        "state": {"version": "1.0"},
    }
    path = tmp_path / "mini.board.yaml"
    path.write_text(dump_record(record), encoding="utf-8")
    return load_boards([path])
