from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine.migrate import migrate, migrate_text
from smd_engine.records import dump_record, load_record
from smd_engine.validate import validate_record


def old(record: dict[str, Any]) -> dict[str, Any]:
    record["schema_version"] = "0.2"
    return record


def errors(record: dict[str, Any]) -> list[str]:
    return [str(f) for f in validate_record(record) if f.level == "error"]


def test_0_2_record_migrates_to_0_3(
    board2: dict[str, Any], manifest: dict[str, Any]
) -> None:
    for record in (old(board2), old(manifest)):
        assert errors(record) == ["error: schema_version: schema 0.2: run smd migrate"]
        notes: list[str] = []
        new = migrate(record, notes)
        assert new["schema_version"] == "0.3"
        assert record["schema_version"] == "0.2"
        assert notes[0] == "schema_version: 0.2 -> 0.3"
        assert errors(new) == []
    board2["schema_version"] = 0.2  # unquoted in YAML
    assert migrate(board2)["schema_version"] == "0.3"


def test_migrate_is_idempotent(board2: dict[str, Any]) -> None:
    board2["elements"][0]["voice"] = "AI"
    once = migrate(old(board2))
    notes: list[str] = []
    assert migrate(once, notes) == once
    assert notes == []


def test_voice_normalisation_keeps_the_old_text(board: dict[str, Any]) -> None:
    els = board["elements"]
    els[1]["voice"] = "AI"
    els[2]["voice"] = "группа; аналогия участника 17.10"
    els[3]["voice"] = "Group"
    notes: list[str] = []
    new = migrate(old(board), notes)["elements"]
    assert (new[1]["voice"], "voice_note" in new[1]) == ("ai", False)
    assert new[2]["voice"] == "participant"
    assert new[2]["voice_note"] == "группа; аналогия участника 17.10"
    assert list(new[2]).index("voice_note") == list(new[2]).index("voice") + 1
    assert (new[3]["voice"], "voice_note" in new[3]) == ("group", False)
    assert "voice: 'AI' -> ai (1 element(s))" in notes
    assert any("participant, old text in voice_note" in n for n in notes)
    text = (
        "record: board_set\nschema_version: 0.2\nid: x\ntitle: t\ncycle: 1\n"
        "status: draft\nelements:\n"
        "  - {id: a, board: od, kind: position, label: p, voice: Иван}\n"
        "  - id: b\n    board: od\n    kind: position\n    label: q\n"
        "    voice: 'группа'  # said\n    cites: [s1]\n"
    )
    assert migrate_text(text) == text.replace("0.2", '"0.3"').replace(
        "voice: Иван}", "voice: participant, voice_note: Иван}"
    ).replace(
        "voice: 'группа'  # said\n",
        "voice: 'participant'  # said\n    voice_note: 'группа'\n",
    )


def test_cli_migrate_reports_without_write(
    board2: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    board2["elements"][0]["voice"] = "AI"
    path = tmp_path / "x.board.yaml"
    text = "# kept\n" + dump_record(old(board2))
    path.write_text(text, encoding="utf-8")
    assert main(["migrate", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert f"to migrate {path}" in out and "voice: 'AI' -> ai" in out
    assert path.read_text(encoding="utf-8") == text
    assert main(["migrate", str(path), "--write"]) == 0
    assert load_record(path)["schema_version"] == "0.3"
    assert path.read_text(encoding="utf-8").startswith("# kept\n")
    assert main(["validate", str(path)]) == 0
