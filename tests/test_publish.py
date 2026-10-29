from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

from smd_engine.cli import main
from smd_engine.records import dump_record
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
