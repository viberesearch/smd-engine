"""Graph signatures and procedure self-checks moved into the validator
(method review 31.10.2026, gates Ф В and У В): validate/graph.py,
validate/tract.py, the ontology hints, board-dense and the procedure each
hint points to."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine import profile as profile_module
from smd_engine.cli import main
from smd_engine.profile import ProfileError, profiles_dir
from smd_engine.records import load_record
from smd_engine.validate import HINTS, validate_record
from smd_engine.validate import context
from smd_engine.validate.context import HINT_PROCEDURES

ROOT = Path(__file__).resolve().parents[1]
ORU = ROOT / "cases" / "example_ru" / "pekarni-oru-c1.board.yaml"


def found(record: dict[str, Any], level: str, ref: str = "") -> list[str]:
    return [
        f.message
        for f in validate_record(record)
        if f.level == level and f.ref.startswith(ref)
    ]


def el(record: dict[str, Any], eid: str) -> dict[str, Any]:
    return next(e for e in record["elements"] if e["id"] == eid)


def rel(record: dict[str, Any], a: str, b: str, kind: str = "flow") -> None:
    record.setdefault("relations", []).append({"from": a, "to": b, "kind": kind})


def test_belongs_and_subordinates_cycles_are_errors(board: dict[str, Any]) -> None:
    rel(board, "s-big-signal", "s-big", "belongs")
    rel(board, "s-big", "s-big-signal", "belongs")
    assert found(board, "error") == [
        "'belongs' relations form a cycle: s-big, s-big-signal"
    ]
    oru = copy.deepcopy(load_record(ORU))
    sub = next(r for r in oru["relations"] if r["kind"] == "subordinates")
    rel(oru, sub["to"], sub["from"], "subordinates")
    assert found(oru, "error") == [
        "'subordinates' relations form a cycle: "
        + ", ".join(sorted((sub["from"], sub["to"])))
    ]


def test_move_cycle_is_an_error_and_flow_cycle_is_not(board: dict[str, Any]) -> None:
    rel(board, "fn-dough", "fn-logistics")
    rel(board, "fn-logistics", "fn-dough")
    assert found(board, "error") == []
    el(board, "f-new")["move"] = {
        "op": "adjoin",
        "from": ["m-coop"],
        "via": "time",
        "status": "candidate",
    }
    assert found(board, "error") == ["move sources form a cycle: f-new, m-coop"]


def test_function_flows(board: dict[str, Any]) -> None:
    rel(board, "place-bank", "fn-dough")
    rel(board, "fn-dough", "p-owner")
    rel(board, "fn-quality", "gap-payer", "refers")
    assert found(board, "hint", "fn-") == [
        "input from nobody; no payer; no receiver: a `flow` from the payer, from "
        "what it takes in, to the receiver, or a gap with `of` for the empty place",
        "input from nobody: a `flow` from the payer, from what it takes in, to the "
        "receiver, or a gap with `of` for the empty place",
    ]


def test_unlinked_functions_and_idle_positions(board: dict[str, Any]) -> None:
    rel(board, "fn-dough", "fn-logistics")
    el(board, "fn-dough")["performed_by"] = "p-organiser"
    assert found(board, "hint", "f-new")[-1] == (
        "1 of 3 functions are linked by no `flow` to another function of the "
        "plan: fn-quality"
    )
    assert found(board, "hint", "od")[-1].endswith("function missing? p-owner")
    board["reflected_from"] = "p-owner"
    assert not any("function missing" in h for h in found(board, "hint", "od"))


def test_positions_unlinked(board: dict[str, Any]) -> None:
    board["relations"] = []
    assert found(board, "hint", "od")[0].endswith(
        "plan of activity? (E2): p-owner, p-organiser"
    )
    rel(board, "p-owner", "place-mills")
    rel(board, "p-organiser", "place-bank")
    assert not any("(E2)" in h for h in found(board, "hint", "od"))


def test_object_isolated(board: dict[str, Any]) -> None:
    assert found(board, "hint", "oo") == [
        "object content linked to no position or situation by a relation or "
        "transition: in isolation from them? (E3): f-old"
    ]
    rel(board, "p-owner", "f-old", "represents")
    assert found(board, "hint", "oo") == []


def test_ontology_cooperation_links_its_positions(board2: dict[str, Any]) -> None:
    assert not any("(E3)" in h for h in found(board2, "hint", "oo"))
    board2["ontology"][0]["cooperation"] = "ghost"
    board2["elements"].append(dict(el(board2, "coop-plant"), id="ghost"))
    board2["ontology"][0]["valid_for"].append("nobody")
    assert found(board2, "hint", "oo")[-1].endswith("(E3): coop-plant")


def test_isolated_facts(board: dict[str, Any]) -> None:
    assert found(board, "hint", "facts") == [
        "facts with no relation, transition or thesis: background laid out and no "
        "conclusion drawn from it? (E6, E11): s-small-fact"
    ]
    rel(board, "s-small-fact", "s-small", "refers")
    assert found(board, "hint", "facts") == []


def test_jump_to_frame(board: dict[str, Any]) -> None:
    assert found(board, "hint", "p-owner") == []
    for eid in ("s-small", "s-small-fact"):
        el(board, eid)["seen_from"] = "p-organiser"
    assert found(board, "hint", "p-owner") == [
        "shifts to 'p-organiser' and a new frame is drawn, but nothing on the "
        "situation board is seen from it: a jump to the organiser of another "
        "whole without discussing the situation? (E12)"
    ]
    el(board, "p-owner")["stance"] = "reflexive"
    assert found(board, "hint", "p-owner") == []


def test_transition_unanchored(board: dict[str, Any]) -> None:
    board["elements"].append(
        {"id": "gap-x", "board": "oo", "kind": "gap", "label": "x", "of": "function"}
    )
    board["transitions"].append({"n": 4, "from": "gap-payer", "to": "gap-x"})
    assert found(board, "hint", "transition") == [
        "neither end is a position or seen from one: a jump not anchored in a "
        "position? (E14)"
    ]


def test_garland(board: dict[str, Any]) -> None:
    board["elements"].append(
        {"id": "gl-a", "board": "s", "half": "big", "kind": "garland",
         "label": "chains", "seen_from": "p-organiser"}
    )  # fmt: skip
    rel(board, "s-big-signal", "gl-a", "belongs")
    assert found(board, "hint", "gl-a") == [
        "a garland needs two or more events that `belongs` to it; it has 1"
    ]
    board["elements"].append(
        dict(el(board, "s-big-signal"), id="s-sig-2", cites=["s1#t=00:20:00"])
    )
    el(board, "s-big-signal")["cites"] = ["s1#t=00:10:00"]
    rel(board, "s-sig-2", "gl-a", "belongs")
    assert found(board, "hint", "gl-a") == [
        "all its events cite one source ('s1'): one witness"
    ]
    el(board, "s-sig-2")["cites"] = ["s2"]
    assert found(board, "hint", "gl-a") == []


def test_bridge_from_and_move_via(board: dict[str, Any]) -> None:
    board["elements"].append(
        {"id": "bg-a", "board": "s", "half": "big", "kind": "situation",
         "label": "big situation with new quality", "seen_from": "p-organiser",
         "move": {"op": "respecify", "from": ["m-coop"], "via": "x",
                  "status": "candidate"}}
    )  # fmt: skip
    assert found(board, "hint", "bg-a") == [
        "a bridge reads the big situation through the model and the garland; its "
        "move is not from a garland"
    ]
    board["elements"].append(
        {"id": "gl-a", "board": "s", "half": "big", "kind": "garland",
         "label": "chains", "seen_from": "p-organiser"}
    )  # fmt: skip
    el(board, "bg-a")["move"]["from"].append("gl-a")
    assert found(board, "hint", "bg-a") == []
    del el(board, "m-coop")["move"]["via"]
    assert found(board, "hint", "m-coop") == [
        "glue with no `via`: name the shared substructure, the changed links, the "
        "scale or the added axis"
    ]
    el(board, "m-coop")["move"]["status"] = "accepted"
    assert found(board, "hint", "m-coop") == []


def test_valid_for_position_without_subject(board2: dict[str, Any]) -> None:
    board2["ontology"][0]["subjects"].pop()
    findings = [f for f in validate_record(board2) if f.level == "warning"]
    assert [(f.ref, f.message, f.procedure) for f in findings] == [
        (
            "O1",
            "valid_for 'p-organiser' has no subject (subjects)",
            "procedures/positional-construction.md §5",
        )
    ]


def test_ai_cooperation_and_cooperation_flows(board2: dict[str, Any]) -> None:
    assert found(board2, "hint", "O1") == [
        "valid for positions with no `flow` to or from the cooperation "
        "'coop-plant' (what each gives or takes): p-owner, p-organiser"
    ]
    rel(board2, "p-owner", "coop-plant")
    rel(board2, "coop-plant", "p-organiser")
    assert found(board2, "hint", "O1") == []
    el(board2, "coop-plant")["voice"] = "ai"
    assert found(board2, "hint", "coop-plant") == [
        "a cooperation drafted by AI and no K on it asking the human to name or "
        "correct how the activities connect"
    ]
    board2["qualifications"][0]["targets"].append("coop-plant")
    assert found(board2, "hint", "coop-plant") == []


def test_translation_loss(board: dict[str, Any]) -> None:
    board["elements"].append(
        {"id": "c-tr", "board": "oo", "kind": "concept", "label": "translation",
         "seen_from": "p-organiser", "voice": "ai",
         "detail": {"columns": ["term", "tier", "что теряется"],
                    "rows": [["a", "model", "time of purchase"], ["b", "model", "нет"],
                             ["c", "model", " "]]}}
    )  # fmt: skip
    assert found(board, "hint", "c-tr") == [
        "a translation names a loss in every row, or the holder's answer that "
        "there is none, with its address; rows 2, 3"
    ]


def test_board_dense(board: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    assert found(board, "hint", "oo") and not any(
        "elements on" in h for h in found(board, "hint", "oo")
    )
    data = yaml.safe_load(
        (profiles_dir() / "program-three-boards.yaml").read_text(encoding="utf-8")
    )
    data["board_dense"] = 5
    dense = profile_module._parse(copy.deepcopy(data), "program-three-boards")
    monkeypatch.setattr(context, "profile_of", lambda record: dense)
    assert found(board, "hint", "oo")[0] == (
        "6 elements on the object board, more than 5: fold what is settled, or "
        "split a part off to a board of its own; `smd frames --light` and "
        "`--zoom` read it step by step"
    )
    data["board_dense"] = 0
    with pytest.raises(ProfileError, match="board_dense must be"):
        profile_module._parse(data, "program-three-boards")


def test_belts_all_md(board2: dict[str, Any]) -> None:
    for t in board2["theses"]:
        t["belt"] = "md"
    assert (
        "only thought-action (мД), no scheme (М) and no thought-communication "
        "(М-К): mechanical reproduction?"
    ) in found(board2, "hint", "theses")
    board2["theses"][0]["belt"] = "mk"
    assert not any("mechanical" in h for h in found(board2, "hint", "theses"))


def test_every_hint_names_a_procedure(
    board: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    assert set(HINT_PROCEDURES) == set(HINTS)
    heading = re.compile(r"^#{2,3} (\d+[a-z]?(\.\d+)?)[. ]", re.MULTILINE)
    for target in HINT_PROCEDURES.values():
        path, _, section = target.partition(" §")
        assert (ROOT / path).exists(), target
        if section:
            text = (ROOT / path).read_text(encoding="utf-8")
            assert section in {m[0] for m in heading.findall(text)}, target
    hints = [f for f in validate_record(board) if f.level == "hint"]
    assert hints and all(f.procedure for f in hints)
    assert (
        main(
            ["validate", "--hints", str(ROOT / "cases/example/bakeries-c1.board.yaml")]
        )
        == 0
    )
    assert "→ procedures/functional-plan.md §4" in capsys.readouterr().out
