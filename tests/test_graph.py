from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from smd_engine.cli import main
from smd_engine.profile import default_profile
from smd_engine.render.graph import (
    EDGE_KINDS,
    LAYER,
    graph_model,
    planes,
    render_graph_html,
)
from smd_engine.render.vault import export_vault

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"


def test_graph_model_puts_boards_on_planes_and_types_links(
    board2: dict[str, Any], manifest: dict[str, Any]
) -> None:
    model = graph_model(board2, "en", manifest)
    nodes = {n["id"]: n for n in model["nodes"]}
    for el in board2["elements"]:
        assert nodes[el["id"]]["z"] == planes(default_profile())[el["board"]] * LAYER
    kinds = {e["k"] for e in model["edges"]}
    assert {r["kind"] for r in board2["relations"]} <= kinds
    for h in board2.get("hypotheses", []):
        tested = {
            e["t"] for e in model["edges"] if e["s"] == h["id"] and e["k"] == "tests"
        }
        assert tested == set(h.get("targets", []))
    cited = {c.split("#")[0] for n in model["nodes"] for c in n["cites"]}
    assert {f"src:{s}" for s in cited} <= set(nodes)
    titles = {s["id"]: s["title"] for s in manifest["sources"]}
    for s in cited & set(titles):
        assert nodes[f"src:{s}"]["label"] == titles[s]


def test_graph_page_is_self_contained(board2: dict[str, Any]) -> None:
    page = render_graph_html(board2, "ru")
    assert "<script src" not in page and "<link" not in page
    data = json.loads(
        re.search(r"const DATA = (.*?);\nconst UI_TEXT", page, re.S).group(1)
    )
    assert len(data["nodes"]) >= len(board2["elements"])
    assert "Ситуационная доска" in page


def test_vault_notes_carry_typed_links_and_canvas(
    tmp_path: Path, board2: dict[str, Any]
) -> None:
    written = export_vault(board2, tmp_path, "en")
    notes = [p for p in written if p.suffix == ".md"]
    assert len(notes) >= len(board2["elements"]) + 1
    rel = board2["relations"][0]
    note = next(
        p
        for p in notes
        if p.name.startswith(rel["from"] + " ") or p.stem == rel["from"]
    )
    head = note.read_text(encoding="utf-8").split("---")[1]
    props = yaml.safe_load(head)
    kind = EDGE_KINDS["en"][rel["kind"]].replace(" ", "_")
    assert any(f"{rel['to']}" in link for link in props[kind])
    canvas = json.loads(next(p for p in written if p.suffix == ".canvas").read_text())
    assert {n["id"] for n in canvas["nodes"]} == {e["id"] for e in board2["elements"]}
    ids = {n["id"] for n in canvas["nodes"]}
    assert all(e["fromNode"] in ids and e["toNode"] in ids for e in canvas["edges"])
    for n in canvas["nodes"]:
        assert (tmp_path / n["file"]).exists()


def test_cli_graph_and_vault(tmp_path: Path) -> None:
    board = str(EXAMPLE / "bakeries-c2.board.yaml")
    sources = str(EXAMPLE / "sources.yaml")
    out = tmp_path / "g.html"
    assert main(["graph", board, "--sources", sources, "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert main(["vault", board, str(tmp_path / "v"), "--lang", "en"]) == 0
    assert (tmp_path / "v" / "Start.md").exists()
    assert (tmp_path / "v" / ".obsidian" / "graph.json").exists()


def test_graph_page_links_only_web_urls(
    board2: dict[str, Any], manifest: dict[str, Any]
) -> None:
    manifest["sources"][0]["url"] = "javascript:alert(1)"
    page = render_graph_html(board2, "en", manifest)
    assert "/^https?:\\/\\//i.test(n.url)" in page
