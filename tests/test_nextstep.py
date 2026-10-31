from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine.nextstep import RULES, advise, first_procedure, render_next
from smd_engine.pack import asset_root, procedure_ids
from smd_engine.records import load_record
from smd_engine.scaffold import scaffold

ROOT = Path(__file__).resolve().parents[1]


def procedures(record: dict[str, Any]) -> list[str]:
    return [a.procedure for a in advise(record)[0]]


def scaffolded(folder: Path, profile: str) -> dict[str, Any]:
    paths = scaffold(folder, profile, "en", today="2026-10-31")
    return load_record(next(p for p in paths if p.name.endswith(".board.yaml")))


def test_every_rule_names_a_procedure_that_exists() -> None:
    known = procedure_ids(asset_root())
    assert {r.procedure for r in RULES} <= set(known)
    assert first_procedure("program-three-boards") == "small-situation"
    assert first_procedure("management-four-boards") == "positional-construction"


def test_fresh_record_starts_with_the_solo_session_order(tmp_path: Path) -> None:
    record = scaffolded(tmp_path, "program-three-boards")
    assert procedures(record) == [
        "small-situation",
        "visionary-tract",
        "positional-construction",
    ]
    text = render_next(record, "x.board.yaml")
    assert "Next: small-situation" in text and "smd pack small-situation" in text
    assert "Also:\n  visionary-tract:" in text


def test_rules_are_read_in_order(board: dict[str, Any], board2: dict[str, Any]) -> None:
    # bakeries-c1: functions with no performer come before the rules after them
    assert procedures(board)[0] == "functional-plan"
    # bakeries-c2: one hypothesis in testing, and the steps show no hint left
    assert procedures(board2) == ["field-result", "reflexive-protocol"]
    # a new cycle that names no reflexive position goes first
    revised = copy.deepcopy(board2)
    del revised["reflected_from"]
    assert procedures(revised)[0] == "reflexive-protocol"
    assert "reflected_from" in advise(revised)[0][0].reason
    # an unplaced thesis (no feeds, no about) outranks the steps
    revised = copy.deepcopy(board2)
    revised["theses"].append(
        {
            "id": "T9",
            "claim": "x",
            "voice": "group",
            "status": "voiced",
            "belt": "mk",
            "kind": "statement",
            "cites": ["s3"],
        }
    )
    assert procedures(revised)[0] == "theses-to-board"
    assert len(procedures(board)) <= 3  # one choice and at most two alternatives


def test_a_procedure_of_another_profile_is_not_proposed(tmp_path: Path) -> None:
    record = scaffolded(tmp_path, "classic-two-boards")
    assert procedures(record)[0] == "positional-construction"
    # a classic record with places and a function but no K: qualification-pass is
    # written for the default profile, so no rule fires and the text says so
    record["elements"] += [
        {"id": "pl", "board": "od", "kind": "place_for_others", "label": "bank"},
        {"id": "fn", "board": "oo", "kind": "function", "label": "dough"},
    ]
    record["theses"] = [
        {
            "id": "T1",
            "claim": "x",
            "voice": "group",
            "status": "voiced",
            "belt": "mk",
            "kind": "statement",
            "feeds": ["fn"],
            "cites": ["s1"],
        }
    ]
    assert procedures(record) == []
    assert "No rule fires" in render_next(record, "x.board.yaml")


def test_cli_next_prints_and_refuses_an_invalid_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = ROOT / "cases/example/bakeries-c1.board.yaml"
    assert main(["next", str(path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("bakeries-c1: cycle 1, profile program-three-boards")
    assert "Next: functional-plan" in out
    bad = tmp_path / "bad.board.yaml"
    bad.write_text("record: board_set\nschema_version: '0.3'\nid: x\n")
    assert main(["next", str(bad)]) == 1
