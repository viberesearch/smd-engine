from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from smd_engine.cli import main
from smd_engine.compare import MATCH, compare, merge, report, similarity
from smd_engine.validate import validate_record

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"


def kinds(pairs: list[Any]) -> dict[tuple[str | None, str | None], str]:
    return {(p.a, p.b): p.kind for p in pairs}


def test_similarity() -> None:
    assert similarity("Night logistics", "night logistics.") == 1.0
    assert similarity("dough production", "dough production, paid per tonne") >= MATCH
    assert similarity("regional mills", "quality standard") < MATCH


def test_compare_classifies_pairs(
    board: dict[str, Any], board2: dict[str, Any]
) -> None:
    got = kinds(compare(board, board2))
    assert got[("f-new", "f-new")] == "agreement"
    assert got[("fn-dough", "fn-dough")] == "refinement"
    assert got[("fn-quality", None)] == "only_a"
    assert got[(None, "p-reflect")] == "only_b"


def test_conflict_on_kind_or_board(board: dict[str, Any]) -> None:
    other = copy.deepcopy(board)
    fn = next(e for e in other["elements"] if e["id"] == "fn-logistics")
    fn["kind"] = "cooperation"
    frame = next(e for e in other["elements"] if e["id"] == "f-old")
    frame["frame_state"] = "new"
    got = {(p.a, p.b): p for p in compare(board, other)}
    assert got[("fn-logistics", "fn-logistics")].kind == "conflict"
    assert "kind function / cooperation" in got[("fn-logistics", "fn-logistics")].note
    assert got[("f-old", "f-old")].kind == "conflict"


def test_merge_is_a_valid_new_cycle(
    board: dict[str, Any], board2: dict[str, Any]
) -> None:
    proposal = merge(board, board2, "bakeries-m3")
    assert proposal["cycle"] == 3 and proposal["revises"] == "bakeries-c2"
    imported = next(e for e in proposal["elements"] if e["id"] == "fn-quality")
    assert imported["epistemic"] == "hypothesis" and imported["in"] == ["f-new"]
    assert "from-bakeries-c1" in imported["lineage"]
    assert [f for f in validate_record(proposal) if f.level == "error"] == []


def test_merge_remaps_the_links_of_a_goal(
    board: dict[str, Any], board2: dict[str, Any]
) -> None:
    goal = {"id": "g-1", "board": "od", "kind": "goal", "label": "a plant in a year"}
    goal |= {"seen_from": "p-owner", "arises_from": ["s-small-fact", "T1"]}
    goal |= {"goal_source": "assigned", "assigned_by": "place-bank"}
    board["elements"].append(goal)
    board["elements"].append(dict(goal, id="g-2", label="x", assigned_by="f-old"))
    proposal = merge(board, board2, "bakeries-m3")
    els = {e["id"]: e for e in proposal["elements"]}
    assert els["g-1"]["arises_from"] == ["s-small-fact"]
    assert els["g-1"]["assigned_by"] == "place-bank" and "assigned_by" not in els["g-2"]
    assert [f for f in validate_record(proposal) if f.level == "error"] == []


def test_merge_remaps_performed_by_of_a_function(
    board: dict[str, Any], board2: dict[str, Any]
) -> None:
    fn = {"id": "fn-x", "board": "oo", "kind": "function", "label": "winter leasing"}
    fn |= {"performed_by": "place-bank"}
    board["elements"].append(fn)
    board["elements"].append(dict(fn, id="fn-y", label="zzz", performed_by="f-old"))
    proposal = merge(board, board2, "bakeries-m3")
    els = {e["id"]: e for e in proposal["elements"]}
    assert els["fn-x"]["performed_by"] == "place-bank"
    assert "performed_by" not in els["fn-y"]
    assert [f for f in validate_record(proposal) if f.level == "error"] == []


def test_merge_turns_conflicts_into_open_k(board: dict[str, Any]) -> None:
    other = copy.deepcopy(board)
    next(e for e in other["elements"] if e["id"] == "f-old")["frame_state"] = "new"
    proposal = merge(board, other, "x")
    new_k = proposal["qualifications"][-1]
    assert new_k["status"] == "open" and new_k["by"] == "compare"
    assert "frame old / new" in new_k["text"]


def test_report_and_cli(tmp_path: Path) -> None:
    out, merged = tmp_path / "r.md", tmp_path / "m.board.yaml"
    c1, c2 = EXAMPLE / "bakeries-c1.board.yaml", EXAMPLE / "bakeries-c2.board.yaml"
    assert (
        main(["compare", str(c1), str(c2), "-o", str(out), "--merge", str(merged)]) == 0
    )
    assert "## functions" in out.read_text() and merged.exists()
    assert main(["compare", str(c1), str(EXAMPLE / "sources.yaml")]) == 2


def test_report_counts(board: dict[str, Any], board2: dict[str, Any]) -> None:
    text = report(board, board2)
    assert text.startswith("# Comparison: `bakeries-c1` (A) and `bakeries-c2` (B)")
    assert "only_a 4" in text


def test_report_lists_lenses(board: dict[str, Any], board2: dict[str, Any]) -> None:
    board["elements"][1]["lens"] = "khaprov-levels"
    board2["theses"][0]["lens"] = "schukin-boundaries"
    text = report(board, board2)
    assert "- only A: khaprov-levels" in text and "- only B: schukin-boundaries" in text
