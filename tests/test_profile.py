from __future__ import annotations

import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from collections.abc import Callable, Iterator
from typing import Any

import pytest
import yaml

from smd_engine.cli import main
from smd_engine.pack import pack
from smd_engine import profile as profile_module
from smd_engine.profile import (
    ProfileError,
    default_profile,
    load_profile,
    profiles_dir,
)
from smd_engine.records import load_record
from smd_engine.render import asset_text
from smd_engine.render.frames import reading_frames, zoom_frames
from smd_engine.render.frames_page import render_frames_html
from smd_engine.render.graph import graph_model, render_graph_html
from smd_engine.render.layout import plan, region_of
from smd_engine.render.svg import render_svg
from smd_engine.render.vault import export_vault
from smd_engine.validate import validate_record

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"
TWO_BOARDS = EXAMPLE / "two-boards-c1.board.yaml"

# The tables as they stood in validate/structure.py and render/layout.py before profiles.
HOME_BOARD = {
    "position": "od",
    "place_for_others": "od",
    "goal": "od",
    "frame": "oo",
    "function": "oo",
    "model": "oo",
    "concept": "oo",
    "standard": "oo",
    "cooperation": "oo",
    "normality_boundary": "s",
    "signal": "s",
    "garland": "s",
    "vision": "s",
    "fact": "s",
    "situation": "s",
}
NEEDS_POSITION = {
    "frame",
    "model",
    "concept",
    "standard",
    "normality_boundary",
    "signal",
    "garland",
    "vision",
    "fact",
    "situation",
    "goal",
}
KIND_ORDER = [
    "entry",
    "position",
    "goal",
    "place_for_others",
    "frame",
    "standard",
    "model",
    "concept",
    "function",
    "cooperation",
    "situation",
    "normality_boundary",
    "fact",
    "signal",
    "garland",
    "vision",
    "other",
    "note",
    "gap",
]
# validate/hints.py SCHEME_KINDS and render/light.py SKELETON_KINDS.
SCHEME_KINDS = {"frame", "function", "model", "concept", "standard", "cooperation"}
SKELETON_KINDS = {"entry", "position", "frame", "function", "situation"}
# render/layout.py and render/svg.py drew these kinds by id; the situation was the
# bold paragraph, now the shape `heading`; PARAGRAPH_KINDS spanned the region.
SHAPE_OF = {
    "entry": "marker",
    "position": "figure",
    "place_for_others": "ellipse",
    "gap": "question",
    "frame": "frame",
    "situation": "heading",
}
PARAGRAPH_KINDS = {
    "normality_boundary",
    "fact",
    "signal",
    "garland",
    "vision",
    "other",
    "note",
}
# render/text.py LABELS: the boards and LABELS[lang]["kinds"].
LABELS = {
    "ru": (
        {
            "od": "Оргдеятельностная доска",
            "oo": "Объектная доска",
            "s": "Ситуационная доска",
        },
        {
            "entry": "вход",
            "position": "позиции",
            "place_for_others": "места для других",
            "goal": "цели",
            "frame": "рамки",
            "function": "функции",
            "model": "модели",
            "concept": "понятия",
            "standard": "стандарты",
            "normality_boundary": "границы нормальности",
            "signal": "сигналы",
            "garland": "серии связанных событий",
            "vision": "визионеры",
            "fact": "факты",
            "situation": "ситуации",
            "gap": "разрывы",
            "note": "заметки",
            "other": "прочее",
            "cooperation": "кооперации",
        },
    ),
    "en": (
        {"od": "Org-activity board", "oo": "Object board", "s": "Situation board"},
        {
            "entry": "entry",
            "position": "positions",
            "place_for_others": "places for others",
            "goal": "goals",
            "frame": "frames",
            "function": "functions",
            "model": "models",
            "concept": "concepts",
            "standard": "standards",
            "normality_boundary": "boundaries of normality",
            "signal": "signals",
            "garland": "series of linked events",
            "vision": "visionaries",
            "fact": "facts",
            "situation": "situations",
            "gap": "gaps",
            "note": "notes",
            "other": "other",
            "cooperation": "cooperations",
        },
    ),
}


@pytest.fixture
def two_boards() -> dict[str, Any]:
    return copy.deepcopy(load_record(TWO_BOARDS))


@pytest.fixture
def broken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, two_boards: dict[str, Any]
) -> Iterator[Callable[..., list[str]]]:
    """Write the classic profile, changed, as `broken.yaml` next to copies of the
    shipped profiles; give the errors `validate_record` finds on the two-board
    record (or on `record`) that names it. The profile stays loadable until the
    test ends."""
    for shipped in profiles_dir().glob("*.yaml"):
        (tmp_path / shipped.name).write_bytes(shipped.read_bytes())
    classic = yaml.safe_load((tmp_path / "classic-two-boards.yaml").read_text())
    monkeypatch.setattr(profile_module, "profiles_dir", lambda: tmp_path)

    def errors(
        change: Callable[[dict[str, Any]], None],
        record: dict[str, Any] | None = None,
    ) -> list[str]:
        data = copy.deepcopy(classic) | {"id": "broken"}
        change(data)
        (tmp_path / "broken.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
        load_profile.cache_clear()
        record = (record or two_boards) | {"profile": "broken"}
        return [str(f) for f in validate_record(record) if f.level == "error"]

    yield errors
    load_profile.cache_clear()


def _set(**values: Any) -> Callable[[dict[str, Any]], None]:
    return lambda data: data.update(values)


def _on_kind(index: int, **values: Any) -> Callable[[dict[str, Any]], None]:
    return lambda data: data["kinds"][index].update(values)


@pytest.mark.parametrize(
    "change, message",
    [
        (_set(kinds={"a": 1}), "kinds must be a list"),
        (_set(sessionflow=[1]), "sessionflow must be a mapping"),
        (_set(sessionflow={"who": "position"}), "sessionflow: who must be a list"),
        (_set(compare_groups=["frames"]), "compare_groups must be a mapping"),
        (_set(boards=["od"]), "boards must be mappings"),
    ],
)
def test_malformed_profile_file_is_an_error_not_a_traceback(
    broken: Callable[..., list[str]],
    change: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    assert broken(change) == [f"error: profile: broken: {message}"]


@pytest.mark.parametrize(
    "change, message",
    [
        (
            lambda data: data["boards"][0]["colour"].__setitem__(0, "#AABBCC"),
            "board od: a colour is written #rrggbb, lowercase",
        ),
        (_set(compare_groups=None), "compare_groups must be a mapping"),
        (
            lambda data: data["boards"][0].update(id=7),
            "board 7: id is missing or not a string",
        ),
        (
            lambda data: data["boards"][0].pop("id"),
            "board None: id is missing or not a string",
        ),
    ],
)
def test_colour_compare_groups_and_ids_are_checked(
    broken: Callable[..., list[str]],
    change: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    assert broken(change) == [f"error: profile: broken: {message}"]


def test_reading_step_without_texts_is_refused(
    broken: Callable[..., list[str]],
) -> None:
    def mystery(data: dict[str, Any]) -> None:
        data["reading"].append({"step": "mystery", "board": "od", "pick": {}})

    [error] = broken(mystery)
    assert "reading step 'mystery' has no texts in smd frames" in error
    assert broken(lambda data: None) == []


def test_duplicate_board_or_kind_id_is_refused(
    broken: Callable[..., list[str]],
) -> None:
    def twice(section: str) -> Callable[[dict[str, Any]], None]:
        return lambda data: data[section].append(copy.deepcopy(data[section][0]))

    assert broken(twice("boards")) == [
        "error: profile: broken: duplicate board ids ['od']"
    ]
    assert broken(twice("kinds")) == [
        "error: profile: broken: duplicate kind ids ['position']"
    ]


@pytest.mark.parametrize(
    "change, message",
    [
        (_on_kind(2, needs_positon=True), "kind goal: unknown keys ['needs_positon']"),
        (_on_kind(2, needs_position="no"), "kind goal: needs_position must be true"),
        (_set(relations="shift"), "relations must be a list of strings"),
        (_set(hints="entry"), "hints must be a list of strings"),
        (_set(hints=["gaps", "mystery"]), "unknown hints ['mystery']; known: "),
        (_set(hints=["gaps", "gaps"]), "duplicate hint ids ['gaps']"),
        (_set(relations=["flow", "flow"]), "duplicate relation ids ['flow']"),
        (
            lambda data: data["boards"][0].update(halves={"small": 1}),
            "board od: halves is none or a list of distinct halves",
        ),
        (
            lambda data: data["boards"][0].update(halves=["small", "small"]),
            "board od: halves is none or a list of distinct halves",
        ),
        (
            _set(sessionflow={"who": [{}]}),
            "sessionflow who: an empty pick would match every element",
        ),
    ],
)
def test_kind_keys_flags_and_string_lists_are_checked(
    broken: Callable[..., list[str]],
    change: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    [error] = broken(change)
    assert error.startswith(f"error: profile: broken: {message}")


def test_default_profile_equals_the_old_tables() -> None:
    profile = default_profile()
    assert profile.id == "program-three-boards"
    assert profile.home_board == HOME_BOARD
    assert profile.kinds_where("needs_position") == NEEDS_POSITION
    assert profile.kind_order == KIND_ORDER
    assert profile.kinds_where("container") == {
        "frame",
        "function",
        "situation",
        "garland",
        "other",
    }
    assert profile.kinds_where("role") == {"position", "place_for_others", "gap"}
    assert [b.id for b in profile.boards] == ["od", "oo", "s"]
    assert profile.kinds_where("scheme") == SCHEME_KINDS
    assert profile.kinds_where("skeleton") == SKELETON_KINDS
    assert profile.kinds_where("light_off") == {"fact", "signal", "note"}
    assert profile.kinds_where("stance") == {"position"}
    assert profile.kinds_where("factual") == {"fact"}
    assert profile.compare_skip == ("entry", "note")
    assert {k.id: k.shape for k in profile.kinds} == {
        k: SHAPE_OF.get(k, "paragraph" if k in PARAGRAPH_KINDS else "box")
        for k in KIND_ORDER
    }
    for lang, (boards, kinds) in LABELS.items():
        assert {b.id: b.label[lang] for b in profile.boards} == boards
        assert {k.id: k.label[lang] for k in profile.kinds} == kinds
    assert profile.board("oo").object and profile.subject_boards == ["od"]
    assert profile.screen == "triangles" and profile.board("s").split == 800


def test_profile_is_hashable() -> None:
    profile = default_profile()
    assert {profile: 1}[load_profile("program-three-boards")] == 1


def test_unknown_kind_or_board_is_an_error(
    board: dict[str, Any], two_boards: dict[str, Any]
) -> None:
    board["elements"][1]["kind"] = "totem"
    board["elements"][2]["board"] = "zz"
    errors = [str(f) for f in validate_record(board) if f.level == "error"]
    assert any("p-owner" in e and "unknown kind 'totem'" in e for e in errors)
    assert any("p-organiser" in e and "unknown board 'zz'" in e for e in errors)
    # the situation board and its kinds are not in the classic profile
    two_boards["elements"][0].update({"board": "s", "half": "small"})
    two_boards["elements"][1]["kind"] = "situation"
    errors = [str(f) for f in validate_record(two_boards) if f.level == "error"]
    assert any("unknown board 's'" in e for e in errors)
    assert any("unknown kind 'situation'" in e for e in errors)
    two_boards["profile"] = "no-such-profile"
    errors = [str(f) for f in validate_record(two_boards) if f.level == "error"]
    assert errors == [
        "error: profile: unknown profile 'no-such-profile'; known: "
        "classic-two-boards, management-four-boards, program-three-boards"
    ]


def test_two_board_record_gets_no_situation_hints(two_boards: dict[str, Any]) -> None:
    findings = validate_record(two_boards)
    assert not [f for f in findings if f.level != "hint"]
    hints = [f.message for f in findings if f.level == "hint"]
    assert hints and not any("situation" in h or "entry" in h for h in hints)
    hint_ids = set(load_profile("classic-two-boards").hints)
    assert not {"situation-halves", "entry"} & hint_ids


def test_two_board_layout_and_svg(two_boards: dict[str, Any]) -> None:
    geo, boxes = plan(two_boards)
    assert set(geo.regions) == {"od", "oo"}
    for el in two_boards["elements"]:
        x0, _, x1, _ = geo.regions[el["board"]]
        assert x0 - 1 <= boxes[el["id"]].x <= x1 + 1, el["id"]
    svg = render_svg(two_boards, "en")
    root = ET.fromstring(svg)
    text = "".join(root.itertext())
    assert "Org-activity board" in text and "Object-ontological board" in text
    assert "Situation board" not in text and "<polygon" not in svg
    ns = "{http://www.w3.org/2000/svg}"
    boards = [r for r in root.iter(f"{ns}rect") if r.get("y") == "100"]
    assert [(r.get("x"), r.get("width")) for r in boards] == [
        ("40", "760"),
        ("800", "760"),
    ]


def test_pack_refuses_a_procedure_of_another_profile(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["pack", "qualification-pass", str(TWO_BOARDS)]) == 2
    assert "procedure is for profile program-three-boards" in capsys.readouterr().err
    text = pack("solo-session", [TWO_BOARDS])
    assert "# Procedure: procedures/small-situation.md" not in text
    assert "left out: `qualification-pass`, `small-situation`, `visionary" in text
    assert "# Procedure: procedures/small-situation.md" in pack(
        "solo-session", [EXAMPLE / "bakeries-c2.board.yaml"]
    )


def _on_step(index: int, **values: Any) -> Callable[[dict[str, Any]], None]:
    return lambda data: data["reading"][index].update(values)


@pytest.mark.parametrize(
    "change, message",
    [
        (
            _on_step(0, board="od.left"),
            "reading step positions: board 'od.left' is neither a board nor a half",
        ),
        (
            _on_step(0, pick={"board": "od", "kinds": "position"}),
            "reading step positions: kinds must be a list of strings",
        ),
        (
            lambda data: data["reading"].append(copy.deepcopy(data["reading"][0])),
            "duplicate reading step ids ['positions']",
        ),
        (
            _set(sessionflow={"why": [{"kinds": ["position"]}]}),
            "sessionflow: unknown blocks ['why']",
        ),
        (
            _set(sessionflow={"who": [{"kinds": ["situation"]}]}),
            "sessionflow who: unknown kinds ['situation']",
        ),
        (
            _set(sessionflow={"who": [{"board": "od", "half": "small"}]}),
            "sessionflow who: unknown half 'small'",
        ),
    ],
)
def test_reading_steps_and_sessionflow_picks_are_checked(
    broken: Callable[..., list[str]],
    change: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    [error] = broken(change)
    assert error.startswith(f"error: profile: broken: {message}")


def _third_board(data: dict[str, Any]) -> None:
    data["boards"][0]["region"] = [60, 150, 780, 450]
    data["boards"].append(
        copy.deepcopy(data["boards"][0])
        | {"id": "x", "region": [60, 510, 780, 850], "object": False}
    )


@pytest.mark.parametrize(
    "change, message",
    [
        (_set(screen="triangles"), "the triangles screen takes three boards"),
        (_set(screen="columns"), "screen must be one of regions, triangles"),
        (
            lambda data: data["boards"][1].update(region=[700, 150, 1500, 850]),
            "the boards od and oo overlap as drawn",
        ),
        # touching regions: the rectangles drawn around them overlap by 40
        (
            lambda data: data["boards"][1].update(region=[800, 150, 1540, 850]),
            "the boards od and oo overlap as drawn: regions side by side need 40",
        ),
        (_set(boards=[]), "a profile takes at least one board"),
        (
            lambda data: data["boards"][0].update(split=400),
            "board od: split is a number, for a board with two halves",
        ),
        (_third_board, "od and x share a row of the screen, but one lies above"),
    ],
)
def test_screen_and_regions_are_checked(
    broken: Callable[..., list[str]],
    change: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    [error] = broken(change)
    assert error.startswith(f"error: profile: broken: {message}")


@pytest.mark.parametrize(
    "regions, message",
    [
        # review 6b: the object board runs down into the situation triangle
        (
            {"od": [60, 150, 780, 800], "s": [445, 820, 1160, 900]},
            "board od must lie within x 40..800, y 100..440 as drawn: region "
            "60 <= x0 < x1 <= 780, 150 <= y0 < y1 <= 430",
        ),
        # review 6b: the object board below the apex, above the situation board
        ({"oo": [820, 450, 1540, 600]}, "board oo must lie within x 800..1560"),
        (
            {"s": [445, 625, 1160, 900]},
            "board s must lie within x 40..1560, y 440..860",
        ),
    ],
)
def test_triangles_refuse_boards_outside_their_parts(
    regions: dict[str, list[int]], message: str
) -> None:
    data = yaml.safe_load(
        (profiles_dir() / "program-three-boards.yaml").read_text(encoding="utf-8")
    )
    for board in data["boards"]:
        board["region"] = regions.get(board["id"], board["region"])
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(data, "program-three-boards")
    assert str(exc.value).startswith(
        f"program-three-boards: on the triangles screen {message}"
    )


def test_a_halved_board_follows_its_region_and_split(
    broken: Callable[..., list[str]], two_boards: dict[str, Any]
) -> None:
    def moved(data: dict[str, Any]) -> None:
        od, oo = data["boards"]
        oo["region"] = [100, 150, 1500, 400]
        od.update(halves=["small", "big"], region=[300, 520, 1300, 800], split=700)

    for el in two_boards["elements"]:
        if el["board"] == "od":
            roles = ("position", "reflexive_position")
            el["half"] = "small" if el["kind"] in roles else "big"
    two_boards["profile"] = "broken"
    assert broken(moved, two_boards) == []
    geo, boxes = plan(two_boards)
    x0, y0, x1, _ = geo.regions["od.small"]
    assert (x0, x1, geo.regions["od.big"][0]) == (300, 690.0, 710.0)
    # the halved board lies below the object board and moves down as it grows
    assert y0 - 520 == geo.regions["oo"][3] - 400
    for el in two_boards["elements"]:
        rx0, ry0, rx1, _ = geo.regions[region_of(el)]
        box = boxes[el["id"]]
        assert rx0 - 1 <= box.x and box.x + box.w <= rx1 + 1 and ry0 <= box.y, el["id"]
    svg = render_svg(two_boards, "en")
    assert '<line x1="700" ' in svg and "<polygon" not in svg
    assert render_svg(two_boards, "en", board="od.small").count('viewBox="270 ') == 1
    page = render_frames_html(zoom_frames(reading_frames(two_boards, "en")), "en")
    # the map spans the outlines of these regions, not the triangles' fixed view
    assert 'class="map" viewBox="60 80 1480 750"' in page
    assert 'viewBox="20 80 1560 800"' not in page
    # a counter is centred in its rectangle: the middle of 470..810 plus 70
    assert '<text x="800.0" y="710.0" font-size="200"' in page


def test_kinds_are_named_by_attribute_or_required(
    broken: Callable[..., list[str]], two_boards: dict[str, Any]
) -> None:
    def renamed(data: dict[str, Any]) -> None:
        data["kinds"][4]["id"] = "scheme_frame"
        data["compare_groups"]["frames"] = ["scheme_frame"]

    for el in two_boards["elements"]:
        if el["kind"] == "frame":
            el["kind"] = "scheme_frame"
    two_boards["elements"][-1]["label"] = "we must keep each recipe"
    two_boards["profile"] = "broken"
    # frame_state and the old and new frame steps go by the shape `frame`
    assert broken(renamed, two_boards) == []
    steps = [f.id for f in reading_frames(two_boards, "en")]
    assert {"old-frame", "new-frame"} <= set(steps)
    warnings = [str(f) for f in validate_record(two_boards) if f.level == "warning"]
    assert warnings == [
        "warning: n-recipe: subject-object talk ('we must', 'our task') belongs on "
        "'od', not on the object-ontological board"
    ]

    def no_note(data: dict[str, Any]) -> None:
        data["kinds"] = [k for k in data["kinds"] if k["id"] != "note"]
        data["compare_skip"] = []

    assert broken(no_note) == [
        "error: profile: broken: missing kinds the engine names: ['note']"
    ]


def test_frames_by_cycle_refuses_records_of_two_profiles(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chain = [str(EXAMPLE / "bakeries-c1.board.yaml"), str(TWO_BOARDS)]
    out = str(tmp_path / "f.html")
    assert main(["frames", "--by", "cycle", *chain, "-o", out]) == 2
    err = capsys.readouterr().err
    assert "bakeries-c1 follows program-three-boards" in err
    assert "two-boards-c1 follows classic-two-boards" in err


def test_graph_takes_board_colours_from_the_profile(two_boards: dict[str, Any]) -> None:
    for data in (two_boards, load_record(EXAMPLE / "bakeries-c1.board.yaml")):
        profile = load_profile(str(data.get("profile", "program-three-boards")))
        model = graph_model(data, "en")
        assert model["board_colours"] == {b.id: b.colour[1] for b in profile.boards}
        assert '"board_colours"' in render_graph_html(data, "en")
    board_color = next(
        line for line in asset_text("graph.js").splitlines() if "BOARD_COLOR =" in line
    )
    assert board_color.startswith("const BOARD_COLOR = {...M.board_colours, records:")


def test_vault_takes_colours_and_screen_name_from_the_profile(
    two_boards: dict[str, Any], tmp_path: Path
) -> None:
    export_vault(two_boards, tmp_path, "en")
    profile = load_profile("classic-two-boards")
    graph = json.loads((tmp_path / ".obsidian" / "graph.json").read_text())
    inks = [int(b.colour[1][1:], 16) for b in reversed(profile.boards)]
    assert [g["color"]["rgb"] for g in graph["colorGroups"][:2]] == inks
    assert (tmp_path / "Screen — two boards.canvas").exists()
    assert "two boards in the screen layout" in (tmp_path / "Start.md").read_text()


TEMPLATE = {
    "id": "detail",
    "per_record": True,
    "label": {"ru": "Деталь", "en": "Detail"},
    "colour": ["#ffffff", "#333333"],
    "kinds": ["function", "note"],
}


def _template(**values: Any) -> Callable[[dict[str, Any]], None]:
    def change(data: dict[str, Any]) -> None:
        data["boards"].append({**TEMPLATE, **values})
        data["reading"].append(
            {"step": "process", "board": "detail", "pick": {"board": "detail"}}
        )

    return change


def _home_on_template(data: dict[str, Any]) -> None:
    _template(kinds=["note"])(data)
    function = next(k for k in data["kinds"] if k["id"] == "function")
    function["home"] = "detail"


@pytest.mark.parametrize(
    "change, message",
    [
        (_template(kinds=["nope"]), "template detail: unknown kinds ['nope']"),
        (_template(kinds=[]), "template detail: a template takes at least one kind"),
        (_template(per_record=False), "template detail: per_record must be true"),
        (_template(region=[60, 150, 700, 450]), "template detail: unknown keys"),
        (_template(id="od"), "duplicate board ids ['od']"),
        (_home_on_template, "template detail: kinds ['function'] live on it"),
        (_template(unfolds=["nope"]), "template detail: unfolds: unknown kinds"),
        (_template(id="records"), "board ids ['records'] are the layers of smd graph"),
        (
            lambda data: (
                _template()(data),
                data["reading"][-1]["pick"].update(board="od"),
            ),
            "reading step process: a step on a template takes a filter without half",
        ),
    ],
)
def test_board_templates_are_checked(
    broken: Callable[..., list[str]],
    change: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    [error] = broken(change)
    assert error.startswith(f"error: profile: broken: {message}")


def test_a_template_of_any_profile_gives_record_boards(
    broken: Callable[..., list[str]], two_boards: dict[str, Any]
) -> None:
    record = copy.deepcopy(two_boards)
    record["boards"] = [{"id": "d1", "template": "detail", "label": "one"}]
    record["elements"].append(
        {"id": "fn-d1", "board": "d1", "kind": "function", "label": "step"}
    )
    assert broken(_template(), record) == []
    record["profile"] = "broken"
    profile = profile_module.profile_of(record)
    assert [b.id for b in profile.boards] == ["od", "oo", "d1"]
    # one column per board of the widest row: the classic screen has two
    assert profile.board("d1").region == (60, 910, 780, 1210)
    frames = reading_frames(record, "en")
    assert [f.title for f in frames if f.id == "process-d1"] == ["Detail: one"]
