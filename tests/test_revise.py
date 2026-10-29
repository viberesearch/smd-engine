from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine.cli import main
from smd_engine.records import dump_record, load_record
from smd_engine.revise import next_id, revise
from smd_engine.validate import validate_record

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"


def errors(record: dict[str, Any], prev: dict[str, Any]) -> list[Any]:
    return [f for f in validate_record(record, None, prev) if f.level == "error"]


def test_next_cycle_carries_decisions(board2: dict[str, Any]) -> None:
    new, todo = revise(board2, date="2026-02-01")
    assert new["id"] == "bakeries-c3" and new["cycle"] == 3
    assert new["revises"] == "bakeries-c2" and new["status"] == "draft"
    assert "reflected_from" not in new and "transitions" not in new
    assert new["signoffs"] == board2["signoffs"]
    assert new["state"] == {"version": "0.3", "accepted": [], "open": ["K1", "T3"]}
    assert any("reflected_from" in t for t in todo)
    assert errors(new, board2) == []


def test_signoffs_are_applied(board2: dict[str, Any]) -> None:
    decisions = {
        "reflected_from": "p-reflect",
        "difficulty": "the plant still has no payer",
        "signoffs": [
            {"function": "close_k", "target": "K1", "by": "group"},
            {"function": "accept_move", "target": "T3", "by": "group"},
            {"function": "accept_result", "target": "H2", "by": "group"},
        ],
    }
    new, todo = revise(board2, date="2026-02-01", decisions=decisions)
    k1 = next(q for q in new["qualifications"] if q["id"] == "K1")
    t3 = next(t for t in new["theses"] if t["id"] == "T3")
    assert k1["status"] == "closed" and k1["closed_in"] == 3
    assert t3["move"]["status"] == "accepted"
    assert new["state"]["open"] == ["T3"]
    assert new["state"]["difficulty"] == "the plant still has no payer"
    assert new["signoffs"][-1] == {
        "function": "accept_result",
        "target": "H2",
        "by": "group",
        "cycle": 3,
        "date": "2026-02-01",
    }
    assert any(t.startswith("H2: set status") for t in todo)
    assert errors(new, board2) == []


def test_k_can_be_reopened_or_marked_partly(board2: dict[str, Any]) -> None:
    decisions = {
        "reflected_from": "p-reflect",
        "signoffs": [
            {"function": "reopen_k", "target": "K2", "by": "group"},
            {"function": "partly_k", "target": "K1", "by": "group"},
        ],
    }
    new, _ = revise(board2, date="2026-02-01", decisions=decisions)
    ks = {q["id"]: q for q in new["qualifications"]}
    assert ks["K2"]["status"] == "open" and "closed_in" not in ks["K2"]
    assert ks["K1"]["status"] == "partly"
    assert new["state"]["open"][-1] == "K2" and "K1" in new["state"]["open"]
    assert [f for f in validate_record(new, None, board2) if f.level != "hint"] == []


@pytest.mark.parametrize(
    "signoff",
    [
        {"function": "close_k", "target": "K9", "by": "group"},
        {"function": "accept_move", "target": "K1", "by": "group"},
        {"function": "close_k", "target": "K1", "by": "AI"},
        {"function": "verify_record", "by": "group"},
    ],
)
def test_bad_signoffs_are_refused(board2: dict[str, Any], signoff: Any) -> None:
    with pytest.raises(ValueError):
        revise(board2, decisions={"signoffs": [signoff]})


def test_stance_and_goal_fields_are_carried(board2: dict[str, Any]) -> None:
    owner = next(e for e in board2["elements"] if e["id"] == "p-owner")
    owner.update(stance="inside", acts_as="leader")
    reflect = next(e for e in board2["elements"] if e["id"] == "p-reflect")
    reflect["stance"] = "reflexive"
    new, _ = revise(
        board2, date="2026-02-01", decisions={"reflected_from": "p-reflect"}
    )
    els = {e["id"]: e for e in new["elements"]}
    assert (
        els["p-owner"]["stance"] == "inside" and els["p-owner"]["acts_as"] == "leader"
    )
    assert els["p-reflect"]["stance"] == "reflexive"
    assert errors(new, board2) == []


def test_next_id_needs_a_trailing_number() -> None:
    assert next_id("case-m9") == "case-m10"
    with pytest.raises(ValueError):
        next_id("case")


def test_cli_revise(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.yaml"
    decisions.write_text(
        yaml.safe_dump(
            {"signoffs": [{"function": "close_k", "target": "K1", "by": "group"}]}
        ),
        encoding="utf-8",
    )
    out = tmp_path / "bakeries-c3.board.yaml"
    prev = str(EXAMPLE / "bakeries-c2.board.yaml")
    assert main(["revise", prev, "--decisions", str(decisions), "-o", str(out)]) == 0
    assert load_record(out)["qualifications"][0]["status"] == "closed"
    assert main(["revise", str(EXAMPLE / "sources.yaml")]) == 2


def test_dump_record_is_compact_and_lossless(board2: dict[str, Any]) -> None:
    text = dump_record(board2)
    assert yaml.safe_load(text) == board2
    assert "- {id: K1, targets: [p-organiser]" in text
