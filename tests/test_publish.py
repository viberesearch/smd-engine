from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine.records import dump_record, load_record
from smd_engine.render.index import render_index

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"
BOARD = EXAMPLE / "bakeries-c2.board.yaml"
BUNDLE = {
    "bakeries-c2_frames.html",
    "bakeries-c2_cycle_frames.html",
    "bakeries-c2_index.html",
    "bakeries-c2_graph.html",
    "bakeries-c2.html",
}


def test_index_lists_every_item_with_a_yaml_line(
    board2: dict[str, Any], manifest: dict[str, Any]
) -> None:
    page = render_index(board2, BOARD, "en", manifest)
    lines = BOARD.read_text(encoding="utf-8").splitlines()
    items = [
        item["id"]
        for key in ("qualifications", "theses", "hypotheses", "ontology", "elements")
        for item in board2.get(key, [])
    ]
    assert items and len(set(items)) == len(items)
    for id_ in items:
        m = re.search(rf'<b id="{re.escape(id_)}">.*?:(\d+)">YAML:\1</a>', page)
        assert m and id_ in lines[int(m.group(1)) - 1]
    signoffs = board2["signoffs"]
    assert len(re.findall(r">YAML:\d+<", page)) == len(items) + len(signoffs)
    assert f"<h1>{board2['title']} · cycle 0.2</h1>" in page
    assert "Sources the record cites" in page


def test_index_links_sources_only_when_the_file_exists(
    board2: dict[str, Any], manifest: dict[str, Any], tmp_path: Path
) -> None:
    name = "Транскрипт 1.txt"
    source = next(s for s in manifest["sources"] if s["id"] == "s1")
    source["file"] = name
    archive = tmp_path / "archive" / "sessions"
    archive.mkdir(parents=True)
    # macOS file names may come back decomposed (NFD); the match must not depend on it
    (archive / unicodedata.normalize("NFD", name)).write_text("x", encoding="utf-8")

    without = render_index(board2, BOARD, "en", manifest)
    assert "file://" not in without.replace("file://" + str(BOARD.resolve()), "")
    assert source["title"] in without
    elsewhere = render_index(board2, BOARD, "en", manifest, tmp_path / "empty")
    assert "Транскрипт" not in elsewhere
    web = next(s for s in manifest["sources"] if s["id"] == "s3")
    web["url"] = "javascript:alert(1)"
    unsafe = render_index(board2, BOARD, "en", manifest)
    assert "javascript:alert(1)" in unsafe and 'href="javascript' not in unsafe

    linked = render_index(board2, BOARD, "ru", manifest, tmp_path / "archive")
    assert "%D0%A2" in linked and "sessions" in linked  # percent-encoded path


def test_publish_writes_the_bundle_or_nothing(
    board2: dict[str, Any], tmp_path: Path
) -> None:
    out = tmp_path / "pub"
    args = ["publish", str(BOARD), "--sources", str(EXAMPLE / "sources.yaml")]
    assert main([*args, "--out", str(out), "--lang", "en"]) == 0
    assert {p.name for p in out.iterdir()} == BUNDLE
    assert "cycle 0.2" in (out / "bakeries-c2_frames.html").read_text("utf-8")
    assert "<section " in (out / "bakeries-c2_cycle_frames.html").read_text("utf-8")

    board2["relations"].append(
        {"from": "no-such-element", "to": "f-new", "kind": "refers"}
    )
    bad = tmp_path / "bad" / "bakeries-c2.board.yaml"
    bad.parent.mkdir()
    bad.write_text(dump_record(board2), encoding="utf-8")
    empty = tmp_path / "empty-out"
    assert main(["publish", str(bad), "--out", str(empty)]) == 1
    assert not empty.exists()


def _warn(record: dict[str, Any]) -> None:
    """A K closed without a human sign-off: a warning, not an error."""
    record["qualifications"].append(
        {
            "id": "K9",
            "text": "x",
            "by": "methodologist",
            "status": "closed",
            "closed_in": 1,
        }
    )


def test_publish_strict_fails_on_the_record_not_on_earlier_cycles(
    board: dict[str, Any],
    board2: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _warn(board)
    (tmp_path / "bakeries-c1.board.yaml").write_text(dump_record(board), "utf-8")
    record = tmp_path / "bakeries-c2.board.yaml"
    record.write_text(dump_record(board2), "utf-8")
    args = ["publish", str(record), "--strict", "--lang", "en"]
    assert main([*args, "--out", str(tmp_path / "a")]) == 0
    err = capsys.readouterr().err
    assert "bakeries-c1.board.yaml: warning: K9" in err
    assert "earlier cycle: not failing" in err

    _warn(board2)
    record.write_text(dump_record(board2), "utf-8")
    assert main([*args, "--out", str(tmp_path / "b")]) == 1
    assert "bakeries-c2.board.yaml: warning: K9" in capsys.readouterr().err
    assert not (tmp_path / "b").exists()


def test_publish_index_has_no_absolute_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "smd").mkdir(parents=True)
    record = repo / "smd" / BOARD.name
    record.write_text(BOARD.read_text("utf-8"), "utf-8")
    manifest = load_record(EXAMPLE / "sources.yaml")
    source = next(s for s in manifest["sources"] if s["id"] == "s1")
    source["file"] = "session 1.txt"
    (repo / "archive").mkdir()
    (repo / "archive" / "session 1.txt").write_text("x", "utf-8")
    sources = repo / "sources.yaml"
    sources.write_text(dump_record(manifest), "utf-8")
    args = ["publish", str(record), "--sources", str(sources), "--lang", "en"]
    args += ["--archive", str(repo / "archive"), "--out", str(repo / "out" / "pub")]
    assert main(args) == 0
    page = (repo / "out" / "pub" / "bakeries-c2_index.html").read_text("utf-8")
    assert str(tmp_path) not in page and "file://" not in page
    assert "vscode://" not in page and ">YAML:" in page
    assert 'href="../../smd/bakeries-c2.board.yaml"' in page
    assert 'href="../../archive/session%201.txt"' in page

    # a bundle that shares no folder but the root with the record links neither
    page = render_index(load_record(record), record, "en", manifest, base=Path("/"))
    assert str(tmp_path) not in page and ".board.yaml</a>" not in page
