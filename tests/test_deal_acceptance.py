"""Deal mode, map acceptance: the record, its pin to the board's sha256, the void
state and the elements to ask again, with the invented boards of cases/example/."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from deal_helpers import copy_deal, errors
from smd_engine.cli import main
from smd_engine.task.acceptance import load_board, reask
from smd_engine.task.check import check_pack
from smd_engine.task.model import load_task, schema_issues, sha256_file

CASES = Path(__file__).resolve().parents[1] / "cases" / "example"
C1, C2 = CASES / "bakeries-c1.board.yaml", CASES / "bakeries-c2.board.yaml"


def stamp(path: Path) -> dict[str, str]:
    board = load_board(path)
    version = str(board.get("state", {}).get("version", board["cycle"]))
    return {"id": board["id"], "version": version, "sha256": sha256_file(path)}


def write_acceptance(path: Path, board: Path, **over: Any) -> Path:
    acc: dict[str, Any] = {
        "record": "task_acceptance",
        "schema_version": "0.1",
        "board": stamp(board),
        "member": "boris",
        "date": "2026-11-03",
        "vocabulary": "accept",
        "elements": {"p-owner": "accept", "f-old": "reject", "f-new": "not_read"},
        "check": "not_done",
        **over,
    }
    path.write_text(yaml.safe_dump(acc, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    """The deal example whose map is the board set bakeries-c2."""
    folder = copy_deal(tmp_path / "deal")
    path = folder / "pack.yaml"
    pack = yaml.safe_load(path.read_text(encoding="utf-8"))
    pack["map"] = stamp(C2)
    path.write_text(yaml.safe_dump(pack, sort_keys=False), encoding="utf-8")
    return folder


def check(
    work: Path, *acceptances: Path, board: Path | None = None, prior: Path | None = None
) -> int:
    args = ["task", "check", str(work / "pack.yaml"), "--acceptance"]
    args += [str(a) for a in acceptances]
    if board:
        args += ["--board", str(board)]
    if prior:
        args += ["--prior", str(prior)]
    return main(args)


def test_an_acceptance_on_the_current_map_is_valid_and_summarised(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acc = write_acceptance(tmp_path / "acc.yaml", C2)
    assert check(work, acc, board=C2) == 0
    out = capsys.readouterr().out
    assert (
        "acceptance boris: vocabulary accept; elements 1 accept, 1 reject, 1 not read"
        in out
    )
    assert "check not_done" in out and "void" not in out
    assert "element(s) of the board have no act: not_read" in out


def test_an_act_on_an_element_not_on_the_board_is_an_error(
    work: Path, tmp_path: Path
) -> None:
    acc = write_acceptance(tmp_path / "acc.yaml", C2, elements={"ghost": "accept"})
    assert check(work, acc, board=C2) == 1


def test_an_edited_board_voids_the_acceptance_and_only_changed_elements_are_asked(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acc = write_acceptance(tmp_path / "acc.yaml", C1)  # given on cycle 1
    assert check(work, acc) == 0  # a void acceptance is a state, not a fault
    assert "(bakeries-c1 is now bakeries-c2)" in capsys.readouterr().out
    assert check(work, acc, board=C2, prior=C1) == 0
    out = capsys.readouterr().out
    got = reask(load_board(C1), load_board(C2))
    assert f"ask again {len(got['changed'])} changed element(s)" in out
    assert f"{len(got['unchanged'])} unchanged" in out and "(void)" in out
    assert "fn-dough" in got["changed"] and "p-owner" in got["unchanged"]


def test_a_comment_in_the_board_file_voids_it_and_nothing_is_asked_again(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    edited = tmp_path / "edited.board.yaml"
    shutil.copy(C2, edited)
    edited.write_text(edited.read_text(encoding="utf-8") + "# a comment\n")
    pack = load_task(work / "pack.yaml")
    pack["map"] = stamp(edited)
    (work / "pack.yaml").write_text(yaml.safe_dump(pack, sort_keys=False))
    acc = write_acceptance(tmp_path / "acc.yaml", C2)
    assert check(work, acc, board=edited, prior=C2) == 0
    out = capsys.readouterr().out
    assert "void: the map changed" in out and "ask again 0 changed element(s)" in out


def test_the_boards_given_must_be_the_ones_the_pack_and_the_acceptance_name(
    work: Path, tmp_path: Path
) -> None:
    acc = write_acceptance(tmp_path / "acc.yaml", C1)
    assert check(work, acc, board=C1) == 1  # not the pack's map
    assert check(work, acc, board=C2, prior=C2) == 1  # not the board of the act
    other = write_acceptance(tmp_path / "other.yaml", C2, member="ghost")
    assert check(work, other) == 1  # not a member


def test_the_pack_needs_a_map(work: Path, tmp_path: Path) -> None:
    acc = write_acceptance(tmp_path / "acc.yaml", C2)
    pack = load_task(work / "pack.yaml")
    del pack["map"]
    (work / "pack.yaml").write_text(yaml.safe_dump(pack, sort_keys=False))
    assert check(work, acc) == 1


def test_the_layers_the_check_needs_a_checker_and_he_is_not_a_member(
    work: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    acc = write_acceptance(tmp_path / "a.yaml", C2, check="done")
    assert schema_issues(load_task(acc), "task_acceptance", "a")  # no checked_by
    acc = write_acceptance(tmp_path / "b.yaml", C2, check="done", checked_by="Vera")
    assert check(work, acc) == 0
    assert "the check is not independent" in capsys.readouterr().out
    acc = write_acceptance(
        tmp_path / "c.yaml", C2, check="done", checked_by="Audit Ltd"
    )
    assert check(work, acc) == 0
    assert "not independent" not in capsys.readouterr().out
    bad = write_acceptance(tmp_path / "d.yaml", C2, vocabulary="maybe")
    assert schema_issues(load_task(bad), "task_acceptance", "d")


def test_a_pack_map_needs_all_three_pins(work: Path) -> None:
    pack = load_task(work / "pack.yaml")
    assert not errors(check_pack(pack, "p"))
    del pack["map"]["sha256"]
    assert errors(check_pack(pack, "p"))
