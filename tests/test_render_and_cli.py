from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine.records import load_schema
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.sessionflow import render_sessionflow
from smd_engine.render.text import LABELS
from smd_engine.validate import SIGNOFF_EFFECT
from smd_engine.profile import default_profile
from smd_engine.render.layout import layout, region_of, regions
from smd_engine.render.markdown import render_markdown
from smd_engine.render.mermaid import render_mermaid
from smd_engine.render.svg import render_svg
from smd_engine.sources import (
    check_files,
    clean_room,
    refresh,
    rewrite_sha_lines,
    sha256_of,
)

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"


def test_svg_is_well_formed_and_shows_every_label(board: dict[str, Any]) -> None:
    svg = render_svg(board, "en")
    ET.fromstring(svg)
    text = "".join(ET.fromstring(svg).itertext())
    compact = text.replace(" ", "")
    for el in board["elements"]:
        assert el["label"].replace(" ", "") in compact, el["id"]
    for q in board["qualifications"]:
        assert q["id"] in text


def test_layout_keeps_items_in_their_region(board: dict[str, Any]) -> None:
    boxes = layout(board, 960)
    for el in board["elements"]:
        region = f"s.{el['half']}" if el["board"] == "s" else el["board"]
        x0, y0, x1, _ = regions(default_profile())[region]
        box = boxes[el["id"]]
        assert x0 - 1 <= box.x and box.x + box.w <= x1 + 1, el["id"]
        assert box.y >= y0 - 1, el["id"]


def test_children_sit_inside_their_frame(board: dict[str, Any]) -> None:
    boxes = layout(board, 960)
    frame = boxes["f-new"]
    for fid in ("fn-dough", "fn-logistics", "fn-quality"):
        b = boxes[fid]
        assert frame.x < b.x and b.x + b.w < frame.x + frame.w
        assert frame.y < b.y and b.y + b.h < frame.y + frame.h


def test_geom_overrides_layout(board: dict[str, Any]) -> None:
    board["elements"][1]["geom"] = [0.1, 0.2, 0.1, 0.05]
    box = layout(board, 960)[board["elements"][1]["id"]]
    assert (round(box.x), round(box.y)) == (160, 192)


def test_markdown_html_mermaid(board: dict[str, Any]) -> None:
    md = render_markdown(board, "en")
    assert "## Object board" in md and "glue across domains" in md and "**K2**" in md
    html = render_html(board, "ru")
    assert html.startswith("<!doctype html>") and "Квалификации" in html
    mm = render_mermaid(board, "en")
    assert mm.startswith("flowchart LR") and "==>|3|" in mm


def test_clean_room_split(manifest: dict[str, Any]) -> None:
    allowed, denied = clean_room(manifest, {"earlier-concept"})
    assert [s["id"] for s in allowed] == ["s1", "s3", "s4"]
    assert [s["id"] for s in denied] == ["s2"]


def test_check_files(manifest: dict[str, Any], tmp_path: Path) -> None:
    manifest["sources"][0]["file"] = "a.txt"
    manifest["sources"][0]["sha256"] = "0" * 64
    manifest["sources"][1]["file"] = "b.txt"
    (tmp_path / "a.txt").write_text("x")
    problems = check_files(manifest, tmp_path)
    assert any("checksum differs" in p for p in problems)
    assert any("not found" in p for p in problems)


def test_refresh_rewrites_sha_of_named_sources(
    manifest: dict[str, Any], tmp_path: Path
) -> None:
    manifest["sources"][0]["file"] = "a.txt"
    manifest["sources"][0]["sha256"] = "0" * 64
    (tmp_path / "a.txt").write_text("x\n")
    assert refresh(manifest, tmp_path, ["s1"]) == ["s1"]
    assert check_files(manifest, tmp_path) == []
    assert refresh(manifest, tmp_path, ["s1"]) == []
    text = (
        "# header comment\nsources:\n"
        '  - id: s1\n    file: "a.txt"\n    sha256: "old"\n'
        "  - id: s3\n    title:   odd   spacing\n    file: b.txt\n"
    )
    out = rewrite_sha_lines(text, {"s1": "new", "s3": "n3"})
    assert out == text.replace('"old"', '"new"').replace(
        "file: b.txt\n", "file: b.txt\n    sha256: n3\n"
    )


def test_refresh_leaves_other_sources_untouched(
    manifest: dict[str, Any], tmp_path: Path
) -> None:
    manifest["sources"][0]["file"] = "a.txt"
    manifest["sources"][1]["file"] = "b.txt"
    manifest["sources"][1]["sha256"] = "0" * 64
    manifest["sources"][2]["kind"] = "decision_log"
    manifest["sources"][2]["file"] = "\u0439.txt"
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    (tmp_path / "\u0438\u0306.txt").write_text("z")  # the same name, as NFD
    assert refresh(manifest, tmp_path, []) == ["s4"]
    assert "sha256" not in manifest["sources"][0]
    assert manifest["sources"][1]["sha256"] == "0" * 64


def test_refresh_writes_lines_where_the_entry_carries_them(tmp_path: Path) -> None:
    manifest_path = tmp_path / "sources.yaml"
    head = '# hand-written\nrecord: source_manifest\nschema_version: "0.3"\n'
    head += "case: c\nlocation: here\nsources:\n"
    item = "  - id: {id}\n    title: T\n    origin: team\n    kind: decision_log\n"
    old = "a" * 64
    text = (
        head
        + item.format(id="log")
        + f'    file: log.txt\n    sha256: "{old}"\n    lines: 2  # the sha256 covers\n'
        + item.format(id="log2")
        + f"    file: log2.txt\n    sha256: {old}\n"
    )
    manifest_path.write_text(text, encoding="utf-8")
    (tmp_path / "log.txt").write_text("a\nb\nc\n")
    (tmp_path / "log2.txt").write_text("a\n")
    argv = ["sources", str(manifest_path), "--folder", str(tmp_path), "--refresh"]
    assert main(argv) == 0
    want = text.replace("lines: 2 ", "lines: 3 ")
    want = want.replace(old, sha256_of(tmp_path / "log.txt"), 1)
    want = want.replace(old, sha256_of(tmp_path / "log2.txt"), 1)
    assert manifest_path.read_text(encoding="utf-8") == want  # log2: no lines added
    (tmp_path / "log.txt").write_text("a\nb\n")  # lines changes with the sha256
    assert main(argv) == 0
    assert "lines: 2  # the sha256 covers" in manifest_path.read_text(encoding="utf-8")


def test_cli_validate_render_sources(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        main(
            [
                "validate",
                str(EXAMPLE),
                "--sources",
                str(EXAMPLE / "sources.yaml"),
                "--hints",
            ]
        )
        == 0
    )
    assert "0 error(s)" in capsys.readouterr().out
    out = tmp_path / "x.svg"
    assert (
        main(["render", str(EXAMPLE / "bakeries-c1.board.yaml"), "-o", str(out)]) == 0
    )
    assert out.read_text().startswith("<svg")
    assert (
        main(
            [
                "sources",
                str(EXAMPLE / "sources.yaml"),
                "--clean-room",
                "--deny-lineage",
                "earlier-concept",
            ]
        )
        == 0
    )
    assert "denied:\n  s2" in capsys.readouterr().out


def test_cli_reports_bad_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.board.yaml"
    bad.write_text("record: nothing\n")
    assert main(["validate", str(bad)]) == 1
    assert main(["validate", str(tmp_path / "missing.board.yaml")]) == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["validate", str(empty)]) == 2
    assert main(["render", str(bad)]) == 2


def test_render_creates_output_folder(tmp_path: Path) -> None:
    out = tmp_path / "new" / "screen.svg"
    assert (
        main(["render", str(EXAMPLE / "bakeries-c1.board.yaml"), "-o", str(out)]) == 0
    )
    assert out.exists()


def test_sources_rejects_other_records(capsys: pytest.CaptureFixture[str]) -> None:
    board = str(EXAMPLE / "bakeries-c1.board.yaml")
    assert main(["sources", board]) == 2
    assert main(["validate", board, "--sources", board]) == 2


def test_discovery_matches_exact_names(tmp_path: Path) -> None:
    from smd_engine.records import discover

    for name in ("sources.yaml", "x.board.yaml", "resources.yaml", "notes.yaml"):
        (tmp_path / name).write_text("record: source_manifest\n")
    assert sorted(p.name for p in discover([tmp_path])) == [
        "sources.yaml",
        "x.board.yaml",
    ]


def test_nested_frame_is_placed(board: dict[str, Any]) -> None:
    board["elements"].append(
        {
            "id": "f-inner",
            "board": "oo",
            "kind": "frame",
            "label": "inner",
            "in": ["f-new"],
        }
    )
    boxes = layout(board, 960)
    assert boxes["f-inner"].y > 150 and boxes["f-inner"].x >= 820


def test_mermaid_ids_do_not_collide(board: dict[str, Any]) -> None:
    board["elements"].append(
        {"id": "p.owner", "board": "od", "kind": "note", "label": "x"}
    )
    ids = [
        ln.split("[")[0].split("(")[0].strip()
        for ln in render_mermaid(board).splitlines()
        if ln.startswith("    n")
    ]
    assert len(ids) == len(set(ids))


def test_dense_record_grows_the_boards_without_overlap(board: dict[str, Any]) -> None:
    from smd_engine.render.layout import Geometry, plan

    assert plan(board)[0] == Geometry()
    long = "a fact that takes a whole line or two of the small situation board " * 2
    board["elements"] += [
        {"id": f"f{i}", "board": "s", "half": "small", "kind": "fact", "label": long}
        for i in range(30)
    ] + [
        {
            "id": f"pl{i}",
            "board": "od",
            "kind": "place_for_others",
            "label": f"place {i}",
        }
        for i in range(40)
    ]
    geo, boxes = plan(board)
    assert geo.wide and geo.cy > Geometry().cy
    for region, (x0, y0, x1, y1) in geo.regions.items():
        mine = [boxes[e["id"]] for e in board["elements"] if region_of(e) == region]
        mine = [b for b in mine if b.id not in {c.id for m in mine for c in m.children}]
        for b in mine:
            assert x0 - 1 <= b.x and b.x + b.w <= x1 + 1 and y0 - 1 <= b.y, b.id
            assert b.y + b.h <= max(y1, geo.bottom) + 1, b.id
        for i, a in enumerate(mine):
            for b in mine[i + 1 :]:
                apart = (
                    a.x + a.w <= b.x
                    or b.x + b.w <= a.x
                    or a.y + a.h <= b.y
                    or b.y + b.h <= a.y
                )
                assert apart, (a.id, b.id)


def test_relation_labels_in_a_narrow_half_cover_nothing(
    board: dict[str, Any],
) -> None:
    import re

    from smd_engine.profile import profile_of
    from smd_engine.render.layout import plan
    from smd_engine.render.svg import _obstacles, _text_rects, _three_boards

    def apart(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
        return a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]

    def labels(svg: str) -> list[tuple[float, float, float, float]]:
        out = []
        for g in re.findall(r'<g class="rel"[^>]*>(.*?)</g>', svg):
            r = _text_rects(g)
            out.append((r[0][0], r[0][1], max(x[2] for x in r), r[-1][3]))
        return out

    alone = labels(render_svg(board, "en"))
    # three labelled links between the two items of the small half share a middle
    board["relations"] += [
        {"from": "s-small", "to": "s-small-fact", "kind": "refers", "label": text}
        for text in (
            "payroll",
            "the night shift is what makes the flat sales unprofitable",
            "seen by the owner",
        )
    ]
    placed = labels(render_svg(board, "en"))
    assert placed[0] == alone[0]  # a label that covers nothing stays put
    assert len(placed) == 4
    geo, boxes = plan(board, 960)
    profile = profile_of(board)
    screen = _three_boards(profile, geo, "en")  # the program profile
    for i, a in enumerate(placed):
        assert all(apart(a, b) for b in placed[i + 1 :])
        assert all(apart(a, o) for o in _obstacles(board, boxes, profile, screen))


def test_fillers_and_detail_stay_off_the_board(board: dict[str, Any]) -> None:
    from smd_engine.render.frames import reading_frames
    from smd_engine.render.frames_page import render_frames_html

    place = next(e for e in board["elements"] if e["kind"] == "place_for_others")
    place["fillers"] = ["regional fund"]
    place["detail"] = {
        "title": "by level",
        "columns": ["level"],
        "rows": [["owner intent"]],
    }
    assert "regional fund" not in render_svg(board, "en")
    assert "owner intent" not in render_svg(board, "en")
    for page in (render_html(board, "en"), render_markdown(board, "en")):
        assert "regional fund" in page and "owner intent" in page
    frames = render_frames_html(reading_frames(board, "en"), "en")
    data = frames.split('id="smd-data">')[1].split("</script>")[0]
    assert "regional fund" in data and "owner intent" in data


def test_every_signoff_function_has_labels_and_renders(
    board2: dict[str, Any], tmp_path: Path
) -> None:
    """Each sign-off function the schema allows has a label in ru and en and a
    licensed state, and every renderer that prints sign-offs takes it."""
    schema = load_schema("board_set")
    functions = schema["$defs"]["signoff"]["properties"]["function"]["enum"]
    for lang in ("ru", "en"):
        assert list(LABELS[lang]["signoff"]) == functions
    assert set(SIGNOFF_EFFECT) == set(functions)
    k = board2["qualifications"][0]["id"]
    board2["signoffs"] = [
        {"function": f, "by": "group"} | ({} if f == "verify_record" else {"target": k})
        for f in functions
    ]
    record = tmp_path / "r.board.yaml"
    record.write_text("", encoding="utf-8")
    flow = render_sessionflow(board2)
    for f in functions:
        assert LABELS["ru"]["signoff"][f] in flow
    for lang in ("ru", "en"):
        for page in (
            render_markdown(board2, lang),
            render_html(board2, lang),
            render_index(board2, record, lang),
        ):
            assert all(f in page for f in functions)
