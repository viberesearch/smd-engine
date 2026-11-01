"""What a flow carries (`carries`) shown where the group looks: the screen and
the frames (also lighter and zoomed), the index and the graph page."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from smd_engine.cli import main
from smd_engine.records import dump_record
from smd_engine.render import asset_text
from smd_engine.render.graph import graph_model
from smd_engine.render.index import render_index
from smd_engine.render.light import lighten
from smd_engine.render.svg import link_text, render_svg

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"
FLOUR = {"from": "place-mills", "to": "fn-dough", "kind": "flow"}


def words(svg: str) -> str:
    return "".join(ET.fromstring(svg).itertext())


def test_link_text_is_the_label_then_the_word() -> None:
    flow = {**FLOUR, "carries": "material", "label": "flour"}
    assert link_text(flow, "en") == "flour · material"
    assert link_text(flow, "ru") == "flour · материал"
    assert link_text({**flow, "label": ""}, "ru") == "материал"
    assert link_text({k: v for k, v in flow.items() if k != "carries"}, "ru") == "flour"
    assert link_text(FLOUR, "ru") == ""


def test_screen_writes_what_a_flow_carries(board2: dict[str, Any]) -> None:
    assert "flour · material" in words(render_svg(board2, "en"))
    text = words(render_svg(board2, "ru"))
    assert "flour · материал" in text and "pays per tonne · деньги" in text
    # A link with no `carries` is drawn as before.
    assert "other position" in text and "other position ·" not in text


def test_lighter_screen_drops_the_label_and_keeps_the_word(
    board2: dict[str, Any],
) -> None:
    light = lighten(board2)
    flour = next(r for r in light["relations"] if r["to"] == "fn-dough")
    assert "label" not in flour and flour["carries"] == "material"
    text = words(render_svg(light, "ru"))
    assert "материал" in text and "деньги" in text
    assert "flour ·" not in text and "pays per tonne" not in text


def test_frames_zoom_and_light_pages_write_the_word(
    board2: dict[str, Any], tmp_path: Path
) -> None:
    record = tmp_path / "b.board.yaml"
    record.write_text(dump_record(board2), encoding="utf-8")
    for flags in ([], ["--light"], ["--zoom"], ["--light", "--zoom"]):
        out = tmp_path / "frames.html"
        assert (
            main(["frames", str(record), *flags, "--lang", "ru", "-o", str(out)]) == 0
        )
        page = out.read_text(encoding="utf-8")
        # a zoomed step keeps only the links inside its board
        assert "деньги" in page and ("материал" in page or "--zoom" in flags), flags


def test_index_lists_the_flows_that_carry_something(board2: dict[str, Any]) -> None:
    path = EXAMPLE / "bakeries-c2.board.yaml"
    page = render_index(board2, path, "ru")
    assert 'id="sec-f"' in page and "Потоки: что по ним передаётся" in page
    section = page.split('id="sec-f"')[1].split("<h2")[0]
    assert "<b>материал</b>" in section and "flour" in section
    assert section.count("<tr>") == 1 + sum(
        1 for r in board2["relations"] if "carries" in r
    )
    assert "<b>material</b>" in render_index(board2, path, "en")
    plain = copy.deepcopy(board2)
    for r in plain["relations"]:
        r.pop("carries", None)
    assert 'id="sec-f"' not in render_index(plain, path, "ru")


def test_graph_edge_has_the_word_and_the_page_draws_it(board2: dict[str, Any]) -> None:
    model = graph_model(board2, "ru", None)
    flour = next(
        e for e in model["edges"] if (e["s"], e["t"]) == ("place-mills", "fn-dough")
    )
    assert flour["c"] == "материал" and flour["l"] == "flour"
    assert "c" not in next(e for e in model["edges"] if e["k"] == "shift")
    en = graph_model(board2, "en", None)["edges"]
    assert {e["c"] for e in en if "c" in e} == {
        "material",
        "money",
        "product",
        "information",
    }
    js = asset_text("graph.js")
    assert "e.c" in js and "fillText(e.c" in js


def test_markdown_digest_writes_the_word(board2: dict[str, Any]) -> None:
    from smd_engine.render.markdown import render_markdown

    assert "(поток, материал) — flour" in render_markdown(board2, "ru")
    assert "(flow, material) — flour" in render_markdown(board2, "en")
