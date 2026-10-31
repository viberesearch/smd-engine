from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine import nextstep
from smd_engine.nextstep import (
    ORDER,
    RULES,
    Facts,
    advise,
    first_procedure,
    render_next,
    split_target,
)
from smd_engine.pack import asset_root, procedure_ids
from smd_engine.records import load_record
from smd_engine.scaffold import scaffold
from smd_engine.validate import Finding
from smd_engine.validate.context import HINT_PROCEDURES

ROOT = Path(__file__).resolve().parents[1]


def procedures(record: dict[str, Any]) -> list[str]:
    return [a.procedure for a in advise(record)[0]]


def scaffolded(folder: Path, profile: str) -> dict[str, Any]:
    paths = scaffold(folder, profile, "en", today="2026-10-31")
    return load_record(next(p for p in paths if p.name.endswith(".board.yaml")))


def test_every_rule_names_a_procedure_that_exists() -> None:
    known = procedure_ids(asset_root())
    assert {r.procedure for r in RULES} <= set(known)
    # the one order holds every procedure a rule or a hint can point to, once
    assert len(set(ORDER)) == len(ORDER) and set(ORDER) <= set(known)
    pointed = {split_target(t)[0] for t in HINT_PROCEDURES.values()} - {""}
    assert pointed | {r.procedure for r in RULES} <= set(ORDER)
    assert first_procedure("program-three-boards") == "small-situation"
    assert first_procedure("management-four-boards") == "positional-construction"


def test_fresh_record_starts_with_the_solo_session_order(tmp_path: Path) -> None:
    record = scaffolded(tmp_path, "program-three-boards")
    # a first cycle with no theses: the step-2 procedure comes first, then the
    # thinking steps in the order of solo-session section 3
    assert procedures(record) == [
        "ingest-transcript",
        "small-situation",
        "visionary-tract",
    ]
    text = render_next(record, "x.board.yaml")
    assert "Next: ingest-transcript §0" in text and "smd pack ingest" in text
    assert "Also:\n  small-situation §2:" in text
    record["theses"] = []
    assert procedures(record)[0] == "ingest-transcript"
    record["cycle"] = 2
    assert procedures(record) == [
        "small-situation",
        "visionary-tract",
        "positional-construction",
    ]


def test_hints_and_rules_are_ordered_by_the_solo_session_order(
    board: dict[str, Any], board2: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(nextstep, "MAX_ALSO", 20)
    # bakeries-c1: the hints of the facts, the functions and the gap, in the
    # order of the steps; qualification-pass has a K, so no rule adds it
    found = procedures(board)
    assert found[:3] == ["ingest-transcript", "theses-to-board", "small-situation"]
    assert found.index("functional-plan") < found.index("problematization")
    assert found == sorted(found, key=ORDER.index)
    # each procedure once, with the sections of all its hints
    plan = next(a for a in advise(board)[0] if a.procedure == "functional-plan")
    assert plan.sections == ("3", "4") and plan.label == "functional-plan §3, §4"
    # bakeries-c2: one hypothesis in testing, a gap, the open K
    assert procedures(board2)[:3] == [
        "field-result",
        "problematization",
        "reflexive-protocol",
    ]
    assert procedures(board2)[-1] == "reflexive-protocol"
    # a new cycle that names no reflexive position goes first (gate 0)
    revised = copy.deepcopy(board2)
    del revised["reflected_from"]
    assert procedures(revised)[0] == "reflexive-protocol"
    assert "reflected_from" in advise(revised)[0][0].reason
    assert advise(revised)[0][0].sections[0] == "2"


def test_unplaced_theses_count_only_where_no_hint_covers_them(
    board2: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(nextstep, "MAX_ALSO", 20)
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
    found = advise(revised)[0]
    placing = next(a for a in found if a.procedure == "theses-to-board")
    # the hint information-without-cell covers it, and gives the reason
    assert placing.reason.startswith("theses: information not laid") and (
        placing.sections == ("2",)
    )
    names = procedures(revised)
    assert names == sorted(names, key=ORDER.index) and "theses-to-board" in names
    # a hint of theses-to-board names what to lay out: the rule stays quiet
    facts = Facts(revised, "program-three-boards")
    rule = next(r for r in RULES if r.procedure == "theses-to-board")
    assert rule.condition(facts) and "feed no element" in rule.reason(facts)
    facts.hints.append(Finding("hint", "T9", "x", "procedures/theses-to-board.md §2"))
    assert not rule.condition(facts)
    # a hint at section 3 (E3, object content with no link) does not say so
    facts.hints[:] = [Finding("hint", "f-old", "x", "procedures/theses-to-board.md §3")]
    assert rule.condition(facts)


def test_the_closing_waits_for_every_hint_before_it() -> None:
    record = {"cycle": 2, "qualifications": [{"id": "K1", "status": "open"}]}
    facts = Facts(record, "program-three-boards")
    assert not facts.steps_pending
    for target in (
        "stakeholder-ontology.md §5",
        "field-result.md §3",
        "qualification-pass.md §3.3",
    ):
        facts.hints[:] = [Finding("hint", "x", "m", f"procedures/{target}")]
        assert facts.steps_pending, target
    facts.hints[:] = [Finding("hint", "x", "m", "procedures/reflexive-protocol.md §6")]
    assert not facts.steps_pending


def test_a_hint_on_a_document_is_a_note_not_a_procedure(board2: dict[str, Any]) -> None:
    dense = copy.deepcopy(board2)
    dense["elements"] += [
        {"id": f"x{i}", "board": "oo", "kind": "function", "label": f"f{i}"}
        for i in range(20)
    ]
    advice, facts = advise(dense)
    assert all(a.procedure for a in advice)
    text = render_next(dense, "x.board.yaml")
    assert "Note (advice, no procedure):" in text
    assert "(docs/checks.md)" in text and "more than 15" in text
    assert "Note" not in render_next(board2, "x.board.yaml")
    assert split_target("docs/checks.md") == ("", "")
    assert split_target("procedures/field-result.md §0.2") == ("field-result", "0.2")


def test_a_procedure_of_another_profile_is_not_proposed(tmp_path: Path) -> None:
    record = scaffolded(tmp_path, "classic-two-boards")
    assert procedures(record)[:2] == ["ingest-transcript", "positional-construction"]
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
    assert "Next: ingest-transcript §0" in out and "theses-to-board §3" in out
    bad = tmp_path / "bad.board.yaml"
    bad.write_text("record: board_set\nschema_version: '0.3'\nid: x\n")
    assert main(["next", str(bad)]) == 1
