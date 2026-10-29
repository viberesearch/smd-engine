from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from smd_engine.cli import main
from smd_engine.render.frames import (
    apply_notes,
    cycle_frames,
    parse_notes,
    reading_frames,
    write_notes,
)
from smd_engine.render.svg import render_svg

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"


def test_reading_frames_build_up_to_the_full_screen(board2: dict[str, Any]) -> None:
    frames = reading_frames(board2, "en")
    ids = [f.id for f in frames]
    assert ids[0] == "entry" and ids[-1] == "full"
    assert ids.index("small") < ids.index("big") < ids.index("new-frame")
    shown: set[str] = set()
    for f in frames[:-1]:
        assert f.show is not None and shown <= f.show
        assert f.focus is not None and f.focus <= f.show
        shown = f.show
    assert shown == {e["id"] for e in board2["elements"]}
    assert frames[-1].show is None


def test_cycle_frames_ring_what_each_cycle_added(
    board: dict[str, Any], board2: dict[str, Any]
) -> None:
    first, second = cycle_frames([board2, board], "en")
    assert first.record is board and first.focus is None
    old = {e["id"] for e in board["elements"]}
    assert second.focus == {e["id"] for e in board2["elements"]} - old


def test_notes_round_trip_keeps_edited_text(board2: dict[str, Any]) -> None:
    frames = reading_frames(board2, "en")
    notes = parse_notes(write_notes(frames, "reading", "en"))
    assert set(notes) == {f.id for f in frames}
    notes["small"] = "Read this aloud."
    del notes["full"]
    again = reading_frames(board2, "en")
    assert apply_notes(again, notes) == ["full"]
    assert next(f for f in again if f.id == "small").text == "Read this aloud."


def test_svg_draws_only_the_elements_shown(board2: dict[str, Any]) -> None:
    keep = {"entry"}
    svg = render_svg(board2, "en", show=keep, focus=keep, layers=frozenset())
    text = "".join(ET.fromstring(svg).itertext())
    hidden = next(e for e in board2["elements"] if e["kind"] == "frame")
    assert hidden["label"] not in text


def test_cli_frames_writes_page_and_notes(tmp_path: Path) -> None:
    out, notes = tmp_path / "frames.html", tmp_path / "notes.md"
    record = str(EXAMPLE / "bakeries-c2.board.yaml")
    args = ["frames", record, "--notes", str(notes), "--write-notes", "-o", str(out)]
    assert main(args) == 0
    page = out.read_text(encoding="utf-8")
    assert page.count("<section ") == len(parse_notes(notes.read_text()))
    cycles = [str(EXAMPLE / "bakeries-c1.board.yaml"), record]
    assert main(["frames", *cycles, "--by", "cycle", "-o", str(out)]) == 0
    assert main(["frames", *cycles, "--by", "cycle", "--zoom", "-o", str(out)]) == 0
    assert main(["frames", *cycles, "-o", str(out)]) == 2


def test_light_screen_keeps_structure_and_lists_the_rest(
    board2: dict[str, Any], tmp_path: Path
) -> None:
    from smd_engine.records import dump_record
    from smd_engine.render.frames import lighten_frames
    from smd_engine.render.light import lighten

    fact = {"id": "s-fact", "board": "s", "half": "small", "kind": "fact"}
    board2["elements"].append({**fact, "label": "sales fell 12% in 2025"})
    board2["relations"].append({"from": "s-fact", "to": "f-new", "kind": "refers"})
    light = lighten(board2)
    kept = {e["id"] for e in light["elements"]}
    assert kept == {e["id"] for e in board2["elements"]} - {"s-fact"}
    assert all(r["kind"] != "refers" and "label" not in r for r in light["relations"])
    assert len(light["qualifications"]) == len(board2["qualifications"])
    frames = lighten_frames(reading_frames(board2, "en"), "en")
    assert all(f.show is None or f.show <= kept for f in frames)
    small = next(f for f in frames if f.id == "small")
    assert "Not on the screen" in small.text and "sales fell 12%" in small.text
    record, out = tmp_path / "b.board.yaml", tmp_path / "page.html"
    record.write_text(dump_record(board2), encoding="utf-8")
    assert (
        main(["render", str(record), "--light", "--format", "html", "-o", str(out)])
        == 0
    )
    assert "sales fell 12%" in out.read_text(encoding="utf-8")  # still in the tables


def test_screen_shows_short_or_cut_label_and_validate_warns(
    board2: dict[str, Any],
) -> None:
    from smd_engine.validate import validate_record

    place, other = [e for e in board2["elements"] if e["kind"] == "place_for_others"]
    place["label"] = "a place for others whose label runs on " * 3
    other["label"] = place["label"].upper()
    other["short"] = "short name"
    text = "".join(ET.fromstring(render_svg(board2, "en")).itertext())
    assert "short name" in text and other["label"][:30] not in text
    assert place["label"].strip() not in text and "others…" in text
    warned = [
        f.ref for f in validate_record(board2) if "cut on the screen" in f.message
    ]
    assert warned == [place["id"]]


def test_zoom_cuts_reading_steps_and_folds_the_overview(
    board2: dict[str, Any],
) -> None:
    from smd_engine.render.frames import zoom_frames

    place = next(e for e in board2["elements"] if e["kind"] == "place_for_others")
    board2["qualifications"].append(
        {"id": "K9", "text": "who pays", "status": "open", "targets": [place["id"]]}
    )
    frames = zoom_frames(reading_frames(board2, "en"), "en")
    by_id = {f.id: f for f in frames}
    assert by_id["places"].board == "od" and by_id["small"].board == "s.small"
    full = render_svg(board2, "en")
    cut = render_svg(board2, "en", board="od")
    assert ET.fromstring(cut).get("viewBox") != ET.fromstring(full).get("viewBox")
    folded = by_id["full"].record
    ids = {e["id"] for e in folded["elements"]}
    assert place["id"] not in ids and "more-od" in ids
    counter = next(e for e in folded["elements"] if e["id"] == "more-od")
    assert counter["label"].startswith("+2") and place["label"] in counter["folded"]
    k9 = next(q for q in folded["qualifications"] if q["id"] == "K9")
    assert k9["targets"] == ["more-od"]
    assert "legend" not in by_id["full"].layers and by_id["full"].show is None


def test_page_has_layer_switches_and_details(board2: dict[str, Any]) -> None:
    from smd_engine.render.frames_page import render_frames_html

    page = render_frames_html(reading_frames(board2, "en"), "en")
    for layer in ("ai", "function", "places", "k", "transitions"):
        assert f'data-layer="{layer}"' in page
    assert 'data-layer="clean-room"' not in page  # the example has no clean room
    assert 'class="el" data-id="f-new"' in page and 'data-origin="ai"' in page
    data = page.split('id="smd-data">')[1].split("</script>")[0]
    details = json.loads(data)[board2["id"]]
    assert details["el"]["f-new"]["label"] == next(
        e["label"] for e in board2["elements"] if e["id"] == "f-new"
    )
    assert any("K2" in k for k in details["el"]["f-new"]["k"])
