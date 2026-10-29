from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine.apply import PatchError, apply_patch
from smd_engine.cli import main
from smd_engine.records import dump_record, load_record
from smd_engine.validate import validate_record

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"
PATCH = EXAMPLE / "patches" / "bakeries-c2-1.patch.yaml"


def patch(**fields: Any) -> dict[str, Any]:
    return {
        "record": "board_patch",
        "schema_version": "0.1",
        "id": "bakeries-c2-9",
        "applies_to": "bakeries-c2",
        "version": "0.2.9",
        **fields,
    }


def errors(record: dict[str, Any]) -> list[Any]:
    return [f for f in validate_record(record) if f.level == "error"]


def test_apply_adds_sets_and_removes(board2: dict[str, Any]) -> None:
    new = apply_patch(board2, load_record(PATCH))
    els = {e["id"]: e for e in new["elements"]}
    assert els["fact-pledges"]["kind"] == "fact"
    assert els["place-mills"]["label_note"] == "regional mills"
    assert "gap-risk" not in els
    assert new["state"]["accepted"][-1] == "pledged members carry unsold dough"
    assert "gap-risk" in {e["id"] for e in board2["elements"]}
    assert errors(new) == []
    table = {"columns": ["who", "tier"], "rows": [["owner", "t1"]]}
    fact = {"id": "fact-t", "board": "s", "half": "small", "kind": "fact"}
    fact |= {"label": "who is where", "seen_from": "p-owner", "detail": table}
    new = apply_patch(
        board2,
        patch(
            add={"elements": [fact], "sources": ["s4", "s2"]},
            set=[
                {"id": "fact-t", "detail": {"keys": {"tier": "tier"}}},
                {"id": "m-coop", "move": {"from": ["f-new", "f-old"], "via": None}},
                {"id": "p-organiser", "epistemic": None},
            ],
            state={"remove_open": ["T3"], "next_move": "sign", "difficulty": "d"},
        ),
    )
    els = {e["id"]: e for e in new["elements"]}
    assert els["fact-t"]["detail"] == table | {"keys": {"tier": "tier"}}
    assert els["m-coop"]["move"] == {
        "op": "glue",
        "from": ["f-new", "f-old"],
        "status": "accepted",
    }
    assert "epistemic" not in els["p-organiser"]
    assert new["sources"] == ["s1", "s3", "s4", "s2"]
    assert new["state"]["open"] == ["K1"]
    assert new["state"]["next_move"] == "sign" and new["state"]["difficulty"] == "d"
    assert errors(new) == []


def test_remove_drops_links_and_records_the_reason(board2: dict[str, Any]) -> None:
    gone = ("p-owner", "p-reflect", "coop-plant", "K2")
    new = apply_patch(board2, patch(remove=[{"id": i, "reason": "x"} for i in gone]))
    els = {e["id"]: e for e in new["elements"]}
    assert not set(gone) & set(els) and "seen_from" not in els["f-old"]
    assert new["relations"] == [] and "reflected_from" not in new
    # Transition 1 named p-reflect; the one after it moves up to 1.
    assert new["transitions"] == [{"n": 1, "from": "f-new", "to": "s-big"}]
    o1 = new["ontology"][0]
    assert o1["valid_for"] == ["p-organiser"] and "cooperation" not in o1
    assert [s["position"] for s in o1["subjects"]] == ["p-organiser"]
    assert [q["id"] for q in new["qualifications"]] == ["K1"]
    assert all(s.get("target") != "K2" for s in new["signoffs"])
    assert new["notes"].splitlines() == [
        "bakeries-c2-9: removed p-owner: x",
        "bakeries-c2-9: removed p-reflect: x",
        "bakeries-c2-9: removed coop-plant: x",
        "bakeries-c2-9: removed K2: x; dropped sign-off close_k K2 (group, 2026-01-17)",
    ]
    assert errors(new) == []


def test_apply_refuses_to_write_an_invalid_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.patch.yaml"
    relation = {"from": "p-owner", "to": "ghost", "kind": "refers"}
    bad.write_text(yaml.safe_dump(patch(add={"relations": [relation]})), "utf-8")
    out = tmp_path / "out.board.yaml"
    board = str(EXAMPLE / "bakeries-c2.board.yaml")
    assert main(["apply", board, str(bad), "-o", str(out)]) == 1
    assert not out.exists()
    assert main(["apply", board, str(bad), "-o", str(out), "--force"]) == 1
    assert out.exists()
    # Items of a wrong shape reach the schema check, not a traceback.
    broken = patch(
        add={
            "elements": [{"id": "x-bad", "board": "zz", "kind": "fact", "label": "x"}],
            "relations": [{"to": "p-owner"}],
            "transitions": [{"from": "p-owner"}],
        },
        remove=[{"id": "p-reflect", "reason": "x"}],
    )
    bad.write_text(yaml.safe_dump(broken), "utf-8")
    capsys.readouterr()
    assert main(["apply", board, str(bad), "-o", str(tmp_path / "x.yaml")]) == 1
    assert "x-bad: unknown board 'zz'" in capsys.readouterr().err


def test_apply_sets_version_and_notes(board2: dict[str, Any]) -> None:
    new = apply_patch(board2, patch(title="Bakeries, after the pledges"))
    assert new["state"]["version"] == "0.2.9"
    assert new["applied"] == ["bakeries-c2-9"]
    assert list(new).index("applied") == list(new).index("elements") - 1
    assert new["title"] == "Bakeries, after the pledges" and "notes" not in new
    with pytest.raises(ValueError, match="already applied"):
        apply_patch(new, patch())


@pytest.mark.parametrize(
    "fields",
    [
        {"set": [{"id": "no-such", "label": "x"}]},
        {"remove": [{"id": "K9", "reason": "x"}]},
        {"applies_to": "bakeries-c1"},
    ],
)
def test_unknown_id_is_an_error(board2: dict[str, Any], fields: Any) -> None:
    with pytest.raises(PatchError):
        apply_patch(board2, patch(**fields))


def test_cli_apply(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "b.board.yaml"
    board = str(EXAMPLE / "bakeries-c2.board.yaml")
    sources = str(EXAMPLE / "sources.yaml")
    args = ["apply", board, str(PATCH), "-o", str(out), "--sources", sources]
    assert main(args) == 0
    assert load_record(out)["applied"] == ["bakeries-c2-1"]
    unknown = tmp_path / "unknown.patch.yaml"
    unknown.write_text(yaml.safe_dump(patch(set=[{"id": "nope", "label": "x"}])))
    assert main(["apply", board, str(unknown), "-o", str(out)]) == 2
    assert "'nope'" in capsys.readouterr().err
    assert main(["apply", str(out), str(PATCH), "-o", str(out)]) == 1
    other = tmp_path / "other.patch.yaml"
    # An unquoted version is kept as text.
    other.write_text(yaml.safe_dump(patch(version=5.8)), "utf-8")
    assert main(["apply", board, str(other), "-o", str(out)]) == 0
    assert load_record(out)["state"]["version"] == "5.8"
    # Sources and cites are checked against the manifest.
    other.write_text(yaml.safe_dump(patch(add={"sources": ["s9"]})), "utf-8")
    assert main(["apply", board, str(other), "-o", str(out), "--sources", sources]) == 1
    other.write_text(yaml.safe_dump(patch(cites=["s9#p=2"])), "utf-8")
    assert main(["apply", board, str(other), "-o", str(out), "--sources", sources]) == 2
    assert "'s9#p=2'" in capsys.readouterr().err
    # Tags are checked against the taxonomy file.
    taxonomies = tmp_path / "taxonomies.yaml"
    tiers = {"tier": [{"id": "t1"}]}
    taxonomies.write_text(
        yaml.safe_dump(
            {"record": "taxonomies", "schema_version": "0.1", "taxonomies": tiers}
        ),
        "utf-8",
    )
    tagged = {"id": "p-owner", "tags": {"tier": ["t7"]}}
    other.write_text(yaml.safe_dump(patch(set=[tagged])), "utf-8")
    args = ["apply", board, str(other), "-o", str(out), "--taxonomies", str(taxonomies)]
    assert main(args) == 1
    assert "'t7' is not a value of taxonomy 'tier'" in capsys.readouterr().err


def test_set_a_transition_by_n(board2: dict[str, Any]) -> None:
    change = {"n": 1, "to": "s-small", "label": None, "voice": "ai"}
    new = apply_patch(board2, patch(set=[change]))
    assert new["transitions"][0] == {
        "n": 1,
        "from": "p-reflect",
        "to": "s-small",
        "voice": "ai",
    }
    assert new["transitions"][1] == board2["transitions"][1]
    assert board2["transitions"][0]["to"] == "f-new"
    assert errors(new) == []


def test_unknown_transition_is_an_error(
    board2: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changes = {"set": {"n": 9, "label": "x"}, "remove": {"n": 9, "reason": "x"}}
    for field, change in changes.items():
        with pytest.raises(PatchError, match="unknown transition 9"):
            apply_patch(board2, patch(**{field: [change]}))
    bad = tmp_path / "bad.patch.yaml"
    bad.write_text(yaml.safe_dump(patch(set=[changes["set"]])), "utf-8")
    board = str(EXAMPLE / "bakeries-c2.board.yaml")
    assert main(["apply", board, str(bad), "-o", str(tmp_path / "o.yaml")]) == 2
    assert "unknown transition 9" in capsys.readouterr().err


def test_remove_a_transition_by_n_renumbers_and_notes(board2: dict[str, Any]) -> None:
    new = apply_patch(board2, patch(remove=[{"n": 1, "reason": "not a trajectory"}]))
    assert new["transitions"] == [{"n": 1, "from": "f-new", "to": "s-big"}]
    assert new["notes"] == "bakeries-c2-9: removed transition 1: not a trajectory"
    assert len(board2["elements"]) == len(new["elements"]) and errors(new) == []


def test_board_notes_are_appended_before_removals(board2: dict[str, Any]) -> None:
    board2["notes"] = "kept"
    removal = {"id": "K2", "reason": "r"}
    new = apply_patch(
        board2, patch(board_notes="The group chose X.\n", remove=[removal])
    )
    assert new["notes"].splitlines() == [
        "kept",
        "The group chose X.",
        "bakeries-c2-9: removed K2: r; dropped sign-off close_k K2 (group, 2026-01-17)",
    ]


def test_patch_with_both_is_deterministic(board2: dict[str, Any]) -> None:
    fields = {
        "set": [{"n": 2, "label": "to the future"}],
        "remove": [{"n": 1, "reason": "x"}],
        "board_notes": "Decided after session 3.",
    }
    new = apply_patch(board2, patch(**fields))
    assert dump_record(new) == dump_record(apply_patch(board2, patch(**fields)))
    # `set` addresses transition 2 before the removal of 1 renumbers it.
    assert new["transitions"] == [
        {"n": 1, "from": "f-new", "to": "s-big", "label": "to the future"}
    ]
    assert new["notes"].splitlines()[0] == "Decided after session 3."
