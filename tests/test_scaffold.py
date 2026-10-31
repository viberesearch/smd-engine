from __future__ import annotations

from pathlib import Path

import pytest

from smd_engine.cli import main
from smd_engine.profile import profile_ids
from smd_engine.records import load_record
from smd_engine.validate import validate_record


@pytest.mark.parametrize("lang", ["ru", "en"])
@pytest.mark.parametrize("profile", profile_ids())
def test_new_folder_validates_strictly(profile: str, lang: str, tmp_path: Path) -> None:
    folder = tmp_path / "Family Bakery"
    code = main(["new", str(folder), "--profile", profile, "--lang", lang])
    assert code == 0
    assert sorted(p.name for p in folder.iterdir()) == [
        "README.md",
        "family-bakery-c1.board.yaml",
        "sources.yaml",
    ]
    # --strict: no warning either; only hints are left
    argv = ["validate", str(folder), "--sources", str(folder / "sources.yaml")]
    assert main([*argv, "--strict"]) == 0
    board = load_record(folder / "family-bakery-c1.board.yaml")
    assert board["id"] == "family-bakery-c1" and board["profile"] == profile
    assert [f for f in validate_record(board) if f.level in ("error", "warning")] == []


def test_new_takes_case_and_title_and_names_the_first_procedure(
    tmp_path: Path,
) -> None:
    default = tmp_path / "a"
    main(["new", str(default), "--case", "bakery", "--title", "Bakery: handover"])
    board = load_record(default / "bakery-c1.board.yaml")
    assert board["title"] == "Bakery: handover" and board["case"] == "bakery"
    readme_default = (default / "README.md").read_text("utf-8")
    assert "smd pack small-situation" in readme_default
    # a transcript or notes go to ingest-transcript first, on any profile
    assert "smd pack ingest-transcript" in readme_default
    assert "`ingest-transcript`, затем `theses-to-board`" in readme_default
    # the default profile's procedures do not run on the classic profile
    classic = tmp_path / "b"
    main(["new", str(classic), "--profile", "classic-two-boards", "--lang", "en"])
    readme = (classic / "README.md").read_text("utf-8")
    assert "smd pack positional-construction" in readme
    assert "smd pack ingest-transcript" in readme
    assert "small-situation" not in readme


def test_new_refuses_to_overwrite(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["new", str(tmp_path), "--case", "bakery"]) == 0
    board = tmp_path / "bakery-c1.board.yaml"
    board.write_text("kept\n")
    (tmp_path / "README.md").unlink()
    assert main(["new", str(tmp_path), "--case", "bakery"]) == 2
    assert "not overwriting" in capsys.readouterr().err
    assert board.read_text() == "kept\n"
    assert not (tmp_path / "README.md").exists()  # nothing is written on a refusal


def test_new_rejects_a_bad_profile_and_a_bad_case(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["new", str(tmp_path / "x"), "--profile", "nope"]) == 2
    assert "unknown profile" in capsys.readouterr().err
    assert main(["new", str(tmp_path / "y"), "--case", "Bad Id"]) == 2
    assert not (tmp_path / "x").exists() and not (tmp_path / "y").exists()
