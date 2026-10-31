"""Gate ИИ1 Б: `ai` on roles and functions, `red_line` on elements, the
effective-ai rule, the hint ai-decision-unanswered (validate/ai.py) and the AI
share line of `smd status` and `smd index`."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.records import load_record
from smd_engine.render.index import render_index
from smd_engine.render.text import element_parts, field_lines
from smd_engine.status import render_status
from smd_engine.validate import validate_record
from smd_engine.validate.ai import ai_share, effective_ai

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "cases" / "example"
ORU = ROOT / "cases" / "example_ru" / "pekarni-oru-c1.board.yaml"
HINT = "AI performs this function at a red line"


def el(record: dict[str, Any], eid: str) -> dict[str, Any]:
    return next(e for e in record["elements"] if e["id"] == eid)


def messages(record: dict[str, Any], level: str) -> list[str]:
    return [
        f"{f.ref}: {f.message}" for f in validate_record(record) if f.level == level
    ]


def fired(record: dict[str, Any]) -> list[str]:
    return [m.split(":")[0] for m in messages(record, "hint") if HINT in m]


@pytest.fixture
def plan(board2: dict[str, Any]) -> dict[str, Any]:
    """bakeries-c2 with a red line linked to fn-logistics, and its performer
    p-organiser run by AI: the hint fires for fn-logistics alone."""
    board2["elements"].append(
        {
            "id": "rl-fresh",
            "board": "oo",
            "kind": "concept",
            "label": "dough older than six hours is not delivered",
            "seen_from": "p-owner",
            "red_line": True,
        }
    )
    board2["relations"].append(
        {"from": "rl-fresh", "to": "fn-logistics", "kind": "refers"}
    )
    el(board2, "p-organiser")["ai"] = "performs"
    return board2


@pytest.fixture
def oru() -> dict[str, Any]:
    """pekarni-oru-c1 with an algedonic channel (a red line by its threshold)
    linked to fn-mix, which AI performs."""
    data = copy.deepcopy(load_record(ORU))
    data["elements"].append(
        {
            "id": "ch-dough",
            "board": "ot",
            "kind": "algedonic_channel",
            "label": "тесто старше шести часов",
            "seen_from": "p-organiser",
            "threshold": "6 часов",
            "recovery_time": 1,
        }
    )
    data["relations"] += [
        {"from": "ch-dough", "to": "fn-mix", "kind": "refers"},
        {"from": "ch-dough", "to": "post-director", "kind": "escalates"},
    ]
    el(data, "fn-mix")["ai"] = "performs"
    return data


def test_schema_accepts_ai_and_red_line(plan: dict[str, Any]) -> None:
    el(plan, "fn-dough")["ai"] = "performs"
    el(plan, "place-mills")["ai"] = "assists"
    el(plan, "gap-risk")["ai"] = "performs"  # a gap of: position
    assert messages(plan, "error") == []


@pytest.mark.parametrize(
    ("eid", "field", "value"),
    [
        ("fn-dough", "ai", "helps"),
        ("fn-dough", "ai", True),
        ("f-new", "red_line", "yes"),
    ],
)
def test_schema_refuses_bad_values(
    board2: dict[str, Any], eid: str, field: str, value: Any
) -> None:
    el(board2, eid)[field] = value
    assert any(eid in m or field in m for m in messages(board2, "error"))


@pytest.mark.parametrize("eid", ["f-new", "m-coop", "s-small"])
def test_ai_only_on_roles_and_functions(board2: dict[str, Any], eid: str) -> None:
    el(board2, eid)["ai"] = "assists"
    assert any(
        m.startswith(f"{eid}: 'ai' is only for functions and roles")
        for m in messages(board2, "error")
    )


def test_ai_on_a_gap_needs_of_position(board2: dict[str, Any]) -> None:
    gap = el(board2, "gap-risk")
    gap["ai"] = "performs"
    gap["of"] = "product"
    assert any("'ai' is only for" in m for m in messages(board2, "error"))


def test_effective_ai_own_else_performer() -> None:
    by_id = {
        "p": {"id": "p", "kind": "position", "ai": "performs"},
        "q": {"id": "q", "kind": "position"},
    }
    fn = {"id": "f", "kind": "function", "performed_by": "p"}
    assert effective_ai(fn, by_id) == "performs"
    assert effective_ai({**fn, "ai": "assists"}, by_id) == "assists"
    assert effective_ai({**fn, "performed_by": "q"}, by_id) is None
    assert effective_ai({"id": "f", "kind": "function"}, by_id) is None
    # a role's own value; only a function takes its performer's
    assert effective_ai(by_id["p"], by_id) == "performs"


def test_hint_fires_through_the_performer(plan: dict[str, Any]) -> None:
    # fn-dough keeps its own `ai: assists`; fn-logistics has none and takes
    # `performs` from p-organiser
    assert fired(plan) == ["fn-logistics"]
    hint = next(f for f in validate_record(plan) if HINT in f.message)
    assert hint.procedure == "procedures/functional-plan.md §3"
    assert "rl-fresh" in hint.message


def test_hint_needs_a_red_line(plan: dict[str, Any]) -> None:
    plan["relations"] = [r for r in plan["relations"] if r["from"] != "rl-fresh"]
    assert fired(plan) == []
    el(plan, "fn-logistics")["red_line"] = True  # the function is the line
    assert fired(plan) == ["fn-logistics"]
    el(plan, "fn-logistics")["red_line"] = False
    assert fired(plan) == []


def test_red_line_linked_either_way(plan: dict[str, Any]) -> None:
    rel = next(r for r in plan["relations"] if r["from"] == "rl-fresh")
    rel["from"], rel["to"] = "fn-logistics", "rl-fresh"
    assert fired(plan) == ["fn-logistics"]


def test_hint_not_when_ai_assists_or_a_person_performs(plan: dict[str, Any]) -> None:
    el(plan, "p-organiser")["ai"] = "assists"
    assert fired(plan) == []
    # its own `performs`, but performed by a role without `ai: performs`
    el(plan, "fn-logistics")["ai"] = "performs"
    assert fired(plan) == []


def test_information_flow_back_answers(plan: dict[str, Any]) -> None:
    back = {"from": "fn-logistics", "to": "p-owner", "kind": "flow"}
    plan["relations"].append({**back, "carries": "product"})
    assert fired(plan) == ["fn-logistics"]
    plan["relations"].append({**back, "carries": "information"})
    assert fired(plan) == []


def test_information_to_an_ai_role_does_not_answer(plan: dict[str, Any]) -> None:
    plan["relations"].append(
        {
            "from": "fn-logistics",
            "to": "p-organiser",
            "kind": "flow",
            "carries": "information",
        }
    )
    assert fired(plan) == ["fn-logistics"]


def test_management_channel_is_a_red_line(oru: dict[str, Any]) -> None:
    assert fired(oru) == ["fn-mix"]
    del el(oru, "ch-dough")["threshold"]
    assert fired(oru) == []


@pytest.mark.parametrize(
    "rel",
    [
        {"from": "fn-mix", "to": "post-shift", "kind": "escalates"},
        {"from": "post-shift", "to": "fn-mix", "kind": "subordinates"},
    ],
)
def test_management_escalates_or_subordinates_answer(
    oru: dict[str, Any], rel: dict[str, str]
) -> None:
    oru["relations"].append(rel)
    assert fired(oru) == []


@pytest.mark.parametrize(
    "rel",
    [
        # the wrong way round: the function is not over the post
        {"from": "fn-mix", "to": "post-shift", "kind": "subordinates"},
        # a missing role does not answer
        {"from": "fn-mix", "to": "gap-shares", "kind": "escalates"},
    ],
)
def test_management_links_that_do_not_answer(
    oru: dict[str, Any], rel: dict[str, str]
) -> None:
    oru["relations"].append(rel)
    assert fired(oru) == ["fn-mix"]


def test_classic_profile_enables_the_hint() -> None:
    data = copy.deepcopy(load_record(EXAMPLE / "two-boards-c1.board.yaml"))
    el(data, "fn-dough")["red_line"] = True
    el(data, "p-organiser")["ai"] = "performs"
    assert fired(data) == ["fn-dough"]


def test_ai_share_line_in_status_and_index(board2: dict[str, Any]) -> None:
    # the example: fn-dough `ai: assists`, fn-logistics none
    assert ai_share(board2) == (0, 1, 2)
    assert "- functions: AI performs 0, AI assists 1, of 2" in render_status(
        board2, "en"
    )
    el(board2, "p-organiser")["ai"] = "performs"  # fn-logistics takes it
    assert "- функции: выполняет ИИ 1, ИИ помогает 1, из 2" in render_status(
        board2, "ru"
    )
    page = render_index(board2, EXAMPLE / "bakeries-c2.board.yaml", "ru")
    assert "<p>функции: выполняет ИИ 1, ИИ помогает 1, из 2</p>" in page


def test_no_ai_share_line_without_ai(board: dict[str, Any]) -> None:
    assert ai_share(board) is None
    assert "функции:" not in render_status(board, "ru")
    assert "functions:" not in render_status(board, "en")
    page = render_index(board, EXAMPLE / "bakeries-c1.board.yaml", "ru")
    assert "функции: выполняет ИИ" not in page


def test_fields_shown_in_words() -> None:
    fn = {"id": "f", "kind": "function", "ai": "performs", "red_line": True}
    assert element_parts(fn, "ru") == {"ai": "выполняет ИИ", "red_line": "да"}
    assert element_parts({**fn, "ai": "assists"}, "en") == {
        "ai": "AI assists",
        "red_line": "yes",
    }


def test_english_field_label() -> None:
    fn = {"id": "f", "kind": "function", "ai": "performs"}
    assert field_lines(element_parts(fn, "en"), "en") == ["AI's part: AI performs"]
    assert field_lines(element_parts(fn, "ru"), "ru") == ["участие ИИ: выполняет ИИ"]


@pytest.mark.parametrize(("kind", "word"), [("note", "notes"), ("fact", "facts")])
def test_red_line_refused_on_light_off_kinds(
    board2: dict[str, Any], kind: str, word: str
) -> None:
    board2["elements"].append(
        {
            "id": "x-1",
            "board": "s",
            "half": "small",
            "kind": kind,
            "label": "x",
            "seen_from": "p-owner",
            "red_line": True,
        }
    )
    assert f"x-1: 'red_line' is not for {word}" in messages(board2, "error")


def test_threshold_on_a_red_line(plan: dict[str, Any]) -> None:
    line = el(plan, "rl-fresh")
    line["threshold"] = "6 hours"
    assert messages(plan, "error") == []
    del line["red_line"]
    assert any("'threshold' is only for" in m for m in messages(plan, "error"))


def test_red_line_without_value(plan: dict[str, Any]) -> None:
    hint = next(
        f for f in validate_record(plan) if f.message.startswith("red line with no")
    )
    assert hint.ref == "rl-fresh"
    assert hint.procedure == "procedures/functional-plan.md §4"
    el(plan, "rl-fresh")["threshold"] = "yes/no: dough older than six hours"
    assert not any("red line with no" in m for m in messages(plan, "hint"))


def test_red_line_by_in_or_performer(plan: dict[str, Any]) -> None:
    plan["relations"] = [r for r in plan["relations"] if r["from"] != "rl-fresh"]
    assert fired(plan) == []
    el(plan, "f-new")["red_line"] = True  # fn-logistics is `in` f-new
    assert fired(plan) == ["fn-logistics"]
    el(plan, "f-new")["red_line"] = False
    el(plan, "p-organiser")["red_line"] = True  # the performer is a red line
    assert fired(plan) == ["fn-logistics"]
