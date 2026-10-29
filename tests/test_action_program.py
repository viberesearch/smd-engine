"""Gates Ш8-Ш12: the fields and hints from G.P.'s «Программа действий»
(GP-Guide11), read against т. 5 (GP-T5)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from smd_engine.records import load_record
from smd_engine.validate import validate_record

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"


def found(record: dict[str, Any], level: str, previous: Any = None) -> list[str]:
    return [
        f"{f.ref}: {f.message}"
        for f in validate_record(record, None, previous)
        if f.level == level
    ]


def el(record: dict[str, Any], eid: str) -> dict[str, Any]:
    return next(e for e in record["elements"] if e["id"] == eid)


def add_goal(record: dict[str, Any], **fields: Any) -> dict[str, Any]:
    g = {"id": "g-1", "board": "od", "kind": "goal", "label": "a shared plant"}
    g.update(seen_from="p-organiser", **fields)
    record["elements"].append(g)
    return g


def test_new_fields_are_only_for_their_kinds(board: dict[str, Any]) -> None:
    el(board, "p-owner").update(stance="inside", acts_as="organiser")
    add_goal(board, goal_source="own")
    el(board, "m-coop").update(nature="both", modality="ought")
    assert found(board, "error") == []
    el(board, "f-new").update(stance="external", acts_as="manager")
    el(board, "p-owner").update(goal_source="own")
    el(board, "s-small-fact")["nature"] = "natural"
    assert found(board, "error") == [
        "p-owner: 'goal_source' is only for goals",
        "f-new: 'acts_as' is only for positions",
        "f-new: 'stance' is only for positions: position",
        "s-small-fact: 'nature' is only for the object board",
    ]


def test_goal_links_are_checked(board2: dict[str, Any]) -> None:
    add_goal(board2, arises_from=["gap-risk", "T1", "ghost", "f-new", "T2"])
    board2["elements"][-1].update(goal_source="assigned", assigned_by="f-new")
    assert found(board2, "error") == [
        "g-1: arises_from 'ghost' is not an element or thesis",
        "g-1: arises_from 'f-new': a gap, a fact, or a difficulty, problem or "
        "factual thesis",
        "g-1: arises_from 'T2': a gap, a fact, or a difficulty, problem or "
        "factual thesis",
        "g-1: assigned_by must be a position or a place for others",
    ]


def test_factual_thesis_and_the_stance_flag(board2: dict[str, Any]) -> None:
    board2["theses"][1]["modality"] = "fact"
    add_goal(board2, arises_from=["T2"])
    assert found(board2, "error") == []
    # The classic profile flags `stance` on its reflexive positions too.
    two_boards = load_record(EXAMPLE / "two-boards-c1.board.yaml")
    el(two_boards, "p-reflexive")["stance"] = "reflexive"
    assert found(two_boards, "error") == []


def test_reflected_from_inside_is_warned(board2: dict[str, Any]) -> None:
    el(board2, "p-reflect")["stance"] = "inside"
    assert found(board2, "warning") == [
        "reflected_from: 'p-reflect' has stance inside: the reflexive exit is made "
        "from outside the place one acts in (GP-Guide11 ¶35)"
    ]


def test_object_from_inside(board: dict[str, Any]) -> None:
    el(board, "p-owner")["stance"] = "inside"
    hints = [h for h in found(board, "hint") if "inside the structure" in h]
    assert hints == [
        "f-old: drawn from inside the structure ('p-owner'): for G.P. a structure "
        "one works in is a condition of action, not an object (GP-Guide11 ¶36); "
        "draw it from an external position after reflection"
    ]


def test_external_without_reflection(board2: dict[str, Any]) -> None:
    el(board2, "p-organiser")["stance"] = "external"
    assert not [h for h in found(board2, "hint") if "external position" in h]
    del board2["reflected_from"]
    hints = [h for h in found(board2, "hint") if "external position" in h]
    assert hints == [
        "reflected_from: the object board is seen from an external position "
        "(p-organiser) and the cycle names no reflexive exit: for G.P. the external "
        "position is taken after reflection (GP-Guide11 ¶35, ¶47; GP-T5 p. 150)"
    ]
    # a reflexive position as the reflexive exit silences it too (gate Г5а Б)
    board2["elements"].append(
        {
            "id": "p-refl",
            "board": el(board2, "p-organiser")["board"],
            "kind": "reflexive_position",
            "label": "x",
        }
    )
    board2["reflected_from"] = "p-refl"
    assert not [h for h in found(board2, "hint") if "external position" in h]
    assert not [h for h in found(board2, "error") if "reflected_from" in h]


def test_goal_without_breakdown(board: dict[str, Any]) -> None:
    def goal_hints(record: dict[str, Any]) -> list[str]:
        return [h for h in found(record, "hint") if h.startswith("g-1:")]

    add_goal(board)
    assert goal_hints(board) == [
        "g-1: goal with no breakdown: for G.P. a goal arises at a прокол in habitual "
        "activity (GP-Guide11 ¶43; GP-T5 p. 151, «тупик»). Which difficulty or gap "
        "does it answer?"
    ]
    linked = copy.deepcopy(board)
    linked["relations"].append({"from": "g-1", "to": "gap-payer", "kind": "refers"})
    assert goal_hints(linked) == []
    el(board, "g-1")["arises_from"] = ["s-small-fact"]
    assert goal_hints(board) == []
    el(board, "g-1").update(goal_source="own")
    del el(board, "g-1")["arises_from"]
    assert goal_hints(board) == []
    el(board, "g-1")["goal_source"] = "assigned"
    assert goal_hints(board) == [
        "g-1: an assigned goal names no position that passed it down (assigned_by): "
        "руководство passes goals down as tasks (GP-Guide4 ¶12; GP-T5 p. 169)"
    ]
    el(board, "g-1").update(goal_source="breakdown")
    board["state"]["difficulty"] = "the plant has no payer"
    assert goal_hints(board) == [
        "g-1: a goal from a breakdown names none (arises_from): which gap, fact or "
        "difficulty does it answer? (GP-Guide11 ¶43)"
    ]


def test_position_without_object(board: dict[str, Any]) -> None:
    el(board, "p-owner")["acts_as"] = "politician"
    el(board, "p-organiser")["acts_as"] = "functionary"
    hints = [h for h in found(board, "hint") if "represents no object" in h]
    assert hints == [
        "p-owner: acts as politician and represents no object: which object does "
        "this position take? (GP-Guide10 ¶7, ¶19)"
    ]
    board["relations"].append({"from": "p-owner", "to": "f-old", "kind": "represents"})
    el(board, "f-new")["acts_as"] = "leader"  # an error, and no hint: not a position
    assert "f-new: 'acts_as' is only for positions" in found(board, "error")
    assert not [h for h in found(board, "hint") if "represents no object" in h]


def test_ought_without_fact(board: dict[str, Any]) -> None:
    el(board, "fn-dough")["modality"] = "ought"
    hints = [h for h in found(board, "hint") if h.startswith("fn-dough: ought")]
    assert hints == [
        "fn-dough: ought with no fact linked to it: for G.P. artificial action starts "
        "from the natural processes, which limit it (GP-T5 p. 252)"
    ]
    with_thesis = copy.deepcopy(board)
    with_thesis["theses"] = [
        {
            "id": "T1",
            "claim": "dough is made at night in each shop",
            "voice": "ai",
            "status": "ai_variant",
            "belt": "md",
            "kind": "statement",
            "modality": "fact",
            "about": ["fn-dough"],
        }
    ]
    assert not [h for h in found(with_thesis, "hint") if "fn-dough: ought" in h]
    board["relations"].append(
        {"from": "s-small-fact", "to": "fn-dough", "kind": "refers"}
    )
    assert not [h for h in found(board, "hint") if "fn-dough: ought" in h]


def test_design_the_natural(board: dict[str, Any]) -> None:
    el(board, "m-coop").update(modality="ought", nature="natural")
    el(board, "fn-dough").update(modality="ought", nature="artificial")
    hints = [h for h in found(board, "hint") if "cannot be designed" in h]
    assert hints == [
        "m-coop: ought on a natural process: a natural process cannot be designed, "
        "only used or managed (GP-STS, IT p. 443; GP-T5 p. 231)"
    ]


def test_information_without_cell(board2: dict[str, Any]) -> None:
    assert not [h for h in found(board2, "hint") if "cell of a scheme" in h]
    board2["theses"][0].pop("feeds")
    board2["theses"].append(dict(board2["theses"][0], id="T9", status="open"))
    assert [h for h in found(board2, "hint") if "cell of a scheme" in h] == [
        "theses: information not laid into a cell of a scheme (no feeds or about; "
        "GP-Guide11 ¶5): T1"
    ]


def test_cells_from_information(board: dict[str, Any], board2: dict[str, Any]) -> None:
    def cell_hints(record: dict[str, Any]) -> list[str]:
        return [h for h in found(record, "hint", board) if "cells drawn" in h]

    board2["run"] = {"procedure": "theses-to-board"}
    assert cell_hints(board2) == []  # T1 feeds place-mills, a cell of cycle 1
    for t in board2["theses"]:
        t["feeds"] = ["gap-risk"]
    board2["theses"][0]["feeds"] = ["p-reflect"]
    assert cell_hints(board2) == [
        "cycle: every element the new theses feed is new (gap-risk, p-reflect): "
        "were the cells drawn from the information, not before it? "
        "(GP-Guide11 ¶5; GP-T5 p. 233)"
    ]
    board2["run"] = {"procedure": "solo-session"}
    assert cell_hints(board2) == []
