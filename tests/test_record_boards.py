"""Boards a record makes of its profile's templates (`per_record: true`): each
working process of `management-four-boards` on a process board of its own,
handled as a board by every part of the engine."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from smd_engine.apply import apply_patch
from smd_engine.compare import merge, report
from smd_engine.pack import pack
from smd_engine.profile import RESERVED_BOARD_IDS, load_profile, profile_of
from smd_engine.records import load_record
from smd_engine.render.frames import lighten_frames, reading_frames, zoom_frames
from smd_engine.render.frames_page import render_frames_html
from smd_engine.render.graph import graph_model, planes, render_graph_html
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.layout import plan
from smd_engine.render.markdown import render_markdown
from smd_engine.render.svg import LEGEND_SIZE, LEGEND_WIDTH, _wrap_parts, render_svg
from smd_engine.render.text import text_width
from smd_engine.render.vault import export_vault
from smd_engine.revise import revise
from smd_engine.validate import validate_record

ROOT = Path(__file__).resolve().parents[1]
ORU = ROOT / "cases" / "example_ru" / "pekarni-oru-c1.board.yaml"
TWO_BOARDS = ROOT / "cases" / "example" / "two-boards-c1.board.yaml"
PROCESS_KINDS = "function, cooperation, gap, note"


@pytest.fixture
def oru() -> dict[str, Any]:
    return copy.deepcopy(load_record(ORU))


def found(record: dict[str, Any], level: str = "error") -> list[str]:
    return [str(f) for f in validate_record(record) if f.level == level]


def el(record: dict[str, Any], eid: str) -> dict[str, Any]:
    return next(e for e in record["elements"] if e["id"] == eid)


def test_record_boards_join_the_profile_below_the_fixed_boards(
    oru: dict[str, Any],
) -> None:
    base = load_profile("management-four-boards")
    profile = profile_of(oru)
    assert [b.id for b in profile.record_boards] == ["pb-dough", "pb-delivery"]
    dough = profile.board("pb-dough")
    template = base.template("process")
    assert dough.template == "process" and template is not None
    assert template.unfolds == ("work_process",) and dough.colour == template.colour
    assert dough.label["en"] == "Process board: ночной замес теста"
    assert dough.region == (60, 910, 780, 1210)
    assert profile.board("pb-delivery").region == (820, 910, 1540, 1210)
    assert [[b.id for b in row] for row in profile.rows][-1] == [
        "pb-dough",
        "pb-delivery",
    ]
    assert len(base.boards) == 4 and profile_of(oru) is profile
    # a record without boards, and a profile without templates, are unchanged
    del oru["boards"]
    assert profile_of(oru) is base
    two = load_record(TWO_BOARDS)
    assert profile_of(two | {"boards": oru.get("boards", [])}) is profile_of(two)


def test_layout_places_and_grows_each_record_board(oru: dict[str, Any]) -> None:
    geo, boxes = plan(oru)
    for e in oru["elements"]:
        x0, y0, x1, _ = geo.regions[e["board"]]
        assert x0 - 1 <= boxes[e["id"]].x <= x1 + 1 and y0 <= boxes[e["id"]].y
    oru["boards"].append({"id": "pb-third", "template": "process", "label": "третий"})
    oru["elements"] += [
        {
            "id": f"fn-{n}",
            "board": "pb-dough",
            "kind": "function",
            "label": f"шаг процесса номер {n}",
        }
        for n in range(80)
    ]
    geo, _ = plan(oru)
    low, high = geo.regions["pb-dough"], geo.regions["pb-third"]
    assert low[3] > 1210 and geo.regions["pb-delivery"][3] == low[3]
    assert high[0] == 60 and high[1] > low[3]  # a third board starts a new row
    text = "".join(ET.fromstring(render_svg(oru, "en")).itertext())
    assert "Process board: третий" in text


ADD_ELEMENT = {"id": "x-post", "board": "pb-dough", "kind": "post", "label": "место"}


@pytest.mark.parametrize(
    "change, message",
    [
        (
            lambda r: r["boards"][0].update(template="nope"),
            "board pb-dough: unknown board template 'nope' in profile "
            "'management-four-boards'; known: process",
        ),
        (
            lambda r: r["boards"].append(
                {"id": "ot", "template": "process", "label": "x"}
            ),
            "board ot: board id 'ot' is a board or template of the profile",
        ),
        (
            lambda r: r["boards"].append(copy.deepcopy(r["boards"][0])),
            "board pb-dough: duplicate board id",
        ),
        (
            lambda r: r["elements"].append(ADD_ELEMENT),
            "x-post: kind 'post' is not taken by board 'pb-dough' (template "
            f"'process': {PROCESS_KINDS})",
        ),
        (
            lambda r: r["boards"][0].update(id="pb.dough"),
            "boards/0/id: 'pb.dough' does not match",
        ),
        (
            lambda r: r["boards"].append(
                {"id": "fn-mix", "template": "process", "label": "x"}
            ),
            "board fn-mix: board id is also an element id",
        ),
        (
            lambda r: r["boards"][0].update(seen_from="wp-dough"),
            "board pb-dough: seen_from must be a position",
        ),
        (
            lambda r: r["boards"][0].update(unfolds="wp-nope"),
            "board pb-dough: unfolds 'wp-nope' is not an element",
        ),
        (
            lambda r: r["boards"][0].update(unfolds="post-shift"),
            "board pb-dough: unfolds 'post-shift', a post; a board of template "
            "'process' unfolds work_process",
        ),
        (
            lambda r: r["boards"].append(
                {"id": "records", "template": "process", "label": "x"}
            ),
            "board records: board id 'records' is a layer of smd graph",
        ),
    ],
)
def test_record_boards_are_checked(
    oru: dict[str, Any], change: Callable[[dict[str, Any]], None], message: str
) -> None:
    change(oru)
    assert any(f.startswith(f"error: {message}") for f in found(oru)), found(oru)


def test_an_element_off_its_record_board_is_an_error_or_a_warning(
    oru: dict[str, Any],
) -> None:
    assert found(oru) == [] and found(oru, "warning") == []
    del oru["boards"][1]
    assert "error: fn-load: unknown board 'pb-delivery' in profile " in "".join(
        found(oru)
    )
    del oru["boards"]
    el(oru, "fn-mix")["board"] = "ot"
    oru["elements"] = [
        e for e in oru["elements"] if e["board"] in ("ot", "od", "ap", "us")
    ]
    oru["relations"] = [
        r
        for r in oru["relations"]
        if {r["from"], r["to"]} <= {e["id"] for e in oru["elements"]}
    ]
    oru["transitions"] = oru["transitions"][:3]
    assert found(oru, "warning") == [
        "warning: fn-mix: function usually lies on a board of template 'process'"
    ]


def test_an_unknown_kind_on_a_record_board_is_reported_once(
    oru: dict[str, Any],
) -> None:
    oru["elements"].append({**ADD_ELEMENT, "kind": "nope"})
    assert found(oru) == [
        "error: x-post: unknown kind 'nope' in profile 'management-four-boards'"
    ]


def test_graph_layers_are_no_board_ids(oru: dict[str, Any]) -> None:
    profile = profile_of(oru)
    layers = set(planes(profile)) - {b.id for b in profile.boards}
    assert layers == set(RESERVED_BOARD_IDS)
    oru["boards"].append({"id": "sources", "template": "process", "label": "x"})
    assert "sources" not in {b.id for b in profile_of(oru).boards}
    assert set(graph_model(oru, "en")["boards"]) == {b.id for b in profile.boards}


def test_seen_from_is_expected_on_a_process_board(oru: dict[str, Any]) -> None:
    del oru["boards"][0]["seen_from"]
    assert found(oru, "warning") == [
        "warning: board pb-dough: no position it is seen from"
    ]


def test_seen_from_takes_a_reflexive_position(oru: dict[str, Any]) -> None:
    """Gate Г3 Б: an element or a record board may be seen from a reflexive
    position, and a merge keeps the link."""
    el(oru, "k-retro")["seen_from"] = "p-reflexive"
    oru["boards"][0]["seen_from"] = "p-reflexive"
    assert found(oru) == []
    a = copy.deepcopy(oru)
    a["id"] = "pekarni-oru-a"
    a["elements"].append(
        {
            "id": "m-new",
            "board": "ot",
            "kind": "model",
            "label": "x",
            "seen_from": "p-reflexive",
        }
    )
    merged = merge(a, oru, "pekarni-oru-c2")
    assert el(merged, "m-new")["seen_from"] == "p-reflexive"
    assert merged["boards"][0]["seen_from"] == "p-reflexive"


def test_seen_from_refuses_a_place_for_others(oru: dict[str, Any]) -> None:
    el(oru, "k-retro")["seen_from"] = "place-mills"
    oru["boards"][0]["seen_from"] = "place-mills"
    message = "seen_from must be a position or a reflexive position"
    assert found(oru) == [
        f"error: k-retro: {message}",
        f"error: board pb-dough: {message}",
    ]


def test_reflected_from_takes_a_reflexive_position(oru: dict[str, Any]) -> None:
    """Gate Г5а Б: the reflexive exit of a cycle may be recorded on a reflexive
    position; `smd revise` sets it, and the stance warning reads it too."""
    oru["reflected_from"] = "p-reflexive"
    assert found(oru) == [] and found(oru, "warning") == []
    el(oru, "p-reflexive")["stance"] = "inside"
    assert found(oru, "warning") == [
        "warning: reflected_from: 'p-reflexive' has stance inside: the reflexive "
        "exit is made from outside the place one acts in (GP-Guide11 ¶35)"
    ]
    del oru["reflected_from"]
    new, todo = revise(
        oru, date="2026-11-01", decisions={"reflected_from": "p-reflexive"}
    )
    assert new["reflected_from"] == "p-reflexive"
    assert not any("reflected_from" in t for t in todo)
    assert not [f for f in found(new) if "reflected_from" in f]


def test_reflected_from_refuses_a_place_for_others(oru: dict[str, Any]) -> None:
    oru["reflected_from"] = "place-mills"
    assert found(oru) == [
        "error: reflected_from: reflected_from must be a position or a reflexive "
        "position"
    ]


def test_merge_drops_reflected_from_and_keeps_the_reflexive_position(
    oru: dict[str, Any],
) -> None:
    """A merge is a new cycle on top of B: B's reflexive exit is not the
    merge's, so `reflected_from` is dropped whatever its kind, and the
    reflexive position stays on the board for the next exit to name."""
    oru["reflected_from"] = "p-reflexive"
    a = copy.deepcopy(oru)
    a["id"] = "pekarni-oru-a"
    merged = merge(a, oru, "pekarni-oru-c2")
    assert "reflected_from" not in merged
    assert el(merged, "p-reflexive")["kind"] == "reflexive_position"
    merged["reflected_from"] = "p-reflexive"
    assert not [f for f in found(merged) if "reflected_from" in f]


def test_frames_read_and_cut_each_record_board(oru: dict[str, Any]) -> None:
    frames = reading_frames(oru, "ru")
    step = next(f for f in frames if f.id == "process-pb-delivery")
    assert step.title == "Доска процесса: доставка теста в пекарни"
    assert step.elements == ["fn-load", "fn-deliver", "coop-delivery"]
    assert step.text.startswith("Рабочий процесс, идеализированный")
    zoomed = zoom_frames(lighten_frames(reading_frames(oru, "en"), "en"), "en")
    step = next(f for f in zoomed if f.id == "process-pb-dough")
    assert step.board == "pb-dough" and step.counts is not None
    assert step.counts["pb-dough"] == 3
    page = render_frames_html(zoomed, "en")
    assert 'id="process-pb-dough"' in page


def test_graph_vault_index_markdown_and_pack(
    oru: dict[str, Any], tmp_path: Path
) -> None:
    model = graph_model(oru, "en")
    assert list(model["boards"])[:2] == ["pb-delivery", "pb-dough"]  # planes on top
    assert model["board_colours"]["pb-dough"] == "#6b4fa8"
    export_vault(oru, tmp_path / "v", "ru")
    assert (tmp_path / "v" / "Доска процесса ночной замес теста").is_dir()
    assert (tmp_path / "v" / "Экран — четыре доски и ещё 2.canvas").exists()
    index = render_index(oru, ORU, "en")
    assert 'id="sec-b"' in index and "Process board: доставка теста в пекарни" in index
    md = render_markdown(oru, "en")
    assert (
        "## Process board: ночной замес теста\n\n"
        "`pb-dough` board of `process` unfolds `wp-dough` seen from `p-organiser`"
    ) in md
    text = pack("solo-session", [ORU])
    assert "pb-delivery: board of process: доставка теста в пекарни" in text


def test_legend_and_index_name_boards_and_templates_by_label(
    oru: dict[str, Any],
) -> None:
    """Gate Г7б Б: the SVG legend names the boards of a transition, and the
    index's record-boards table the template, by their labels; the legend by
    the boards' short names, a record board by its own label (gate Г8б В),
    and a transition's label after a dash, not in brackets (gate Г8в В)."""
    svg = render_svg(oru, "ru")
    assert "4 аппарат → ночной замес теста — кто передаёт тесто" in svg
    assert "2 полисистема → ОРУ (верх) — идеал в будущем" in svg
    assert ") (" not in svg
    assert "Переходы: 1 ОД доска → полисистема" in svg
    assert "AP → PB-DOUGH" not in svg
    assert "1 OA board → polysystem" in render_svg(oru, "en")
    c1 = load_record(ROOT / "cases" / "example_ru" / "pekarni-c1.board.yaml")
    assert "2 ситуационная / малая → ситуационная / большая" in render_svg(c1, "ru")
    index = render_index(oru, ORU, "ru")
    assert "</td><td>Доска процесса</td><td>ночной замес теста</td>" in index
    assert "<td>process</td>" not in index
    assert "</td><td>Process board</td>" in render_index(oru, ORU, "en")


def test_an_empty_record_board_is_in_the_markdown(oru: dict[str, Any]) -> None:
    oru["boards"].append({"id": "pb-empty", "template": "process", "label": "пусто"})
    assert (
        render_markdown(oru, "en").count(
            "## Process board: пусто\n\n`pb-empty` board of `process`\n\n## "
        )
        == 1
    )


def test_vault_folders_of_record_boards_are_unique_and_named(
    oru: dict[str, Any], tmp_path: Path
) -> None:
    oru["boards"] += [
        {"id": "pb-x", "template": "process", "label": "a/b:c"},
        {"id": "pb-y", "template": "process", "label": "a b c"},
        {"id": "pb-z", "template": "process", "label": "///"},
    ]
    oru["elements"] += [
        {"id": f"fn-{b}", "board": f"pb-{b}", "kind": "function", "label": b}
        for b in "xyz"
    ]
    export_vault(oru, tmp_path, "en")
    for folder in (
        "Process board a b c",
        "Process board a b c pb-y",
        "Process board pb-z",
    ):
        assert (tmp_path / folder).is_dir(), folder


def test_compare_matches_record_boards_by_id(oru: dict[str, Any]) -> None:
    a = copy.deepcopy(oru)
    a["id"] = "pekarni-oru-a"
    a["boards"].append(
        {
            "id": "pb-bake",
            "template": "process",
            "label": "выпечка",
            "seen_from": "p-organiser",
            "unfolds": "wp-dough",
        }
    )
    a["boards"].append(
        {"id": "pb-odd", "template": "process", "label": "x", "unfolds": "post-shift"}
    )
    a["boards"][0]["label"] = "замес теста ночью"
    a["elements"].append(
        {
            "id": "fn-bake",
            "board": "pb-bake",
            "kind": "function",
            "label": "посадка в печь",
        }
    )
    text = report(a, oru)
    assert "## boards" in text
    assert "- only A `pb-bake` выпечка (elements: A 1, B 0)" in text
    assert (
        "- both `pb-dough` ночной замес теста (elements: A 3, B 3); label замес "
        "теста ночью / ночной замес теста"
    ) in text
    merged = merge(a, oru, "pekarni-oru-c2")
    assert [b["id"] for b in merged["boards"]] == [
        "pb-dough",
        "pb-delivery",
        "pb-bake",
        "pb-odd",
    ]
    assert merged["boards"][2]["unfolds"] == "wp-dough"
    assert "unfolds" not in merged["boards"][3]  # a post is no work process
    assert list(merged).index("boards") < list(merged).index("elements")
    assert merged["boards"][2]["seen_from"] == "p-organiser"
    assert el(merged, "fn-bake")["board"] == "pb-bake"
    assert found(merged) == []
    assert "## boards" not in report(load_record(TWO_BOARDS), load_record(TWO_BOARDS))


def test_revise_carries_record_boards(oru: dict[str, Any]) -> None:
    new, _ = revise(oru, date="2026-11-01")
    assert new["boards"] == oru["boards"] and new["boards"] is not oru["boards"]


def test_apply_adds_sets_and_removes_record_boards(oru: dict[str, Any]) -> None:
    patch = {
        "record": "board_patch",
        "schema_version": "0.1",
        "id": "pekarni-oru-c1-1",
        "applies_to": "pekarni-oru-c1",
        "version": "0.2",
        "add": {
            "boards": [
                {
                    "id": "pb-bake",
                    "template": "process",
                    "label": "выпечка",
                    "seen_from": "p-organiser",
                }
            ],
            "elements": [
                {
                    "id": "fn-bake",
                    "board": "pb-bake",
                    "kind": "function",
                    "label": "посадка в печь",
                }
            ],
        },
        "set": [{"id": "pb-dough", "label": "замес теста ночью"}],
        "remove": [
            {"id": "pb-delivery", "reason": "доставка вне пилота"},
            {"id": "wp-dough", "reason": "проверка"},
        ],
    }
    assert found(patch) == []
    new = apply_patch(oru, patch)
    assert [b["id"] for b in new["boards"]] == ["pb-dough", "pb-bake"]
    assert new["boards"][0]["label"] == "замес теста ночью"
    assert "unfolds" not in new["boards"][0]  # its work process was removed
    ids = {e["id"] for e in new["elements"]}
    assert "fn-bake" in ids and not ids & {"fn-load", "fn-deliver", "coop-delivery"}
    assert all("fn-load" not in (r["from"], r["to"]) for r in new["relations"])
    assert (
        "pekarni-oru-c1-1: removed pb-delivery: доставка вне пилота; with fn-load, "
        "fn-deliver, coop-delivery"
    ) in new["notes"]
    assert found(new) == []
    del oru["boards"]
    oru["elements"] = [e for e in oru["elements"] if not e["board"].startswith("pb-")]
    oru["relations"] = [r for r in oru["relations"] if r["kind"] != "flow"]
    oru["transitions"] = oru["transitions"][:3]
    first = apply_patch(oru, {**patch, "set": [], "remove": []})
    assert list(first).index("boards") < list(first).index("elements")


def test_legend_lines_break_between_transitions() -> None:
    parts = [
        f"{n} Оргдеятельностная доска → Ситуационная доска / малая" for n in "12345"
    ]
    lines = _wrap_parts(parts, LEGEND_WIDTH, LEGEND_SIZE)
    assert len(lines) > 1
    assert all(text_width(line, LEGEND_SIZE) <= LEGEND_WIDTH for line in lines)
    # every part whole on one line: lines break only between transitions
    assert sorted(p for line in lines for p in line.split(" · ")) == parts
    long = " ".join(["слово"] * 400)  # one part wider than a line: wrapped by words
    wrapped = _wrap_parts([long], LEGEND_WIDTH, LEGEND_SIZE)
    assert len(wrapped) > 1
    assert all(text_width(line, LEGEND_SIZE) <= LEGEND_WIDTH for line in wrapped)
    assert _wrap_parts([], LEGEND_WIDTH, LEGEND_SIZE) == []


def test_short_names_on_the_graph_planes_and_in_the_frames(
    oru: dict[str, Any],
) -> None:
    """Gate Г8б В: the graph writes the short names on its planes, and the
    frames name an element's board by it; the panels and tables keep labels."""
    model = graph_model(oru, "ru")
    assert model["board_shorts"]["ap"] == "аппарат"
    assert model["board_shorts"]["pb-dough"] == "ночной замес теста"
    assert model["boards"]["pb-dough"] == "Доска процесса: ночной замес теста"
    assert "(M.board_shorts || M.boards)[b]" in render_graph_html(oru, "ru")
    page = render_frames_html(reading_frames(oru, "ru"), "ru")
    assert "ОРУ (верх)" in page
    # a short name equal to a kind's label would be merged away from the meta
    c1 = load_record(ROOT / "cases" / "example" / "bakeries-c1.board.yaml")
    en = render_frames_html(reading_frames(c1, "en"), "en")
    assert '"meta": "situation · situation board"' in en
    assert "<td>Аппарат руководства</td>" in render_html(oru, "ru")
    assert "<td>Верхняя система ОРУ</td>" in render_html(oru, "ru")
