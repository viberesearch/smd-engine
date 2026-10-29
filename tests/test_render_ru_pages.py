"""Russian on the pages (gate Г5в, option Б): the Markdown digest's own words,
the move names, the kind in the page's element table, and a singular label per
kind where one element's kind is named. The English output keeps its words."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine import profile as profile_module
from smd_engine.profile import ProfileError, load_profile, profile_ids, profiles_dir
from smd_engine.records import load_record
from smd_engine.render.frames import reading_frames
from smd_engine.render.frames_page import render_frames_html
from smd_engine.render.graph import graph_model
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.markdown import render_markdown
from smd_engine.render.svg import render_svg
from smd_engine.render.text import MOVE_NAMES
from smd_engine.render.vault import export_vault

CASES = Path(__file__).resolve().parents[1] / "cases"
C2 = CASES / "example" / "bakeries-c2.board.yaml"
C2_RU = CASES / "example_ru" / "pekarni-c2.board.yaml"
ORU = CASES / "example_ru" / "pekarni-oru-c1.board.yaml"
SCHEMA = Path(profile_module.__file__).parent / "schemas" / "board_set.schema.json"


@pytest.fixture
def oru() -> dict[str, Any]:
    return copy.deepcopy(load_record(ORU))


def test_digest_words_follow_the_language(oru: dict[str, Any]) -> None:
    md = render_markdown(load_record(C2_RU), "ru") + render_markdown(oru, "ru")
    assert "пересматривает `pekarni-c1`" in md
    assert ". чем проверяем: Предложить форму обязательства" in md
    assert "; кооперация `coop-plant`; проверяется гипотезой H1" in md
    assert "  - что с чем конкурирует: цех участников" in md
    assert "- версия: 0.2" in md
    assert (
        "`pb-dough` доска по шаблону `process` развёртывает `wp-dough` "
        "с позиции `p-organiser`"
    ) in md
    for word in ("board of", "unfolds", "seen from", "revises", "version:"):
        assert word not in md
    for word in ("action:", "result:", "changes:", "cooperation", "competes:"):
        assert word not in md
    en = render_markdown(load_record(C2), "en")
    assert "revises `bakeries-c1`" in en and "- version: 0.2" in en
    assert ". action: Offer a pledge form" in en
    assert "; cooperation `coop-plant`; test H1" in en
    assert "  - competes: the members' plant" in en


def test_move_names_follow_the_language() -> None:
    record = load_record(C2_RU)
    glue = "m-coop: склеить с другой областью (γ) ← f-new"
    assert glue in render_svg(record, "ru")
    assert "ход: склеить с другой областью (γ) из f-new" in render_markdown(
        record, "ru"
    )
    assert "glue across" not in render_svg(record, "ru") + render_markdown(record, "ru")
    assert "m-coop: glue across domains (γ) ← f-new" in render_svg(record, "en")
    ops = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))["$defs"]["move"]
    assert (
        set(MOVE_NAMES["ru"])
        == set(MOVE_NAMES["en"])
        == set(ops["properties"]["op"]["enum"])
    )


def test_page_element_table_names_the_kind(oru: dict[str, Any]) -> None:
    ru = "<td>Оргдеятельностная доска</td><td>цель</td><td>тесто из общего цеха"
    assert ru in render_html(oru, "ru")
    page = render_html(oru, "en")
    assert "<td>Org-activity board</td><td>goal</td><td>" in page
    assert "<td>reflexive_position</td>" not in page
    assert "<td>reflexive position</td>" in page


def test_kinds_take_a_singular_label(oru: dict[str, Any]) -> None:
    for pid in profile_ids():
        for kind in load_profile(pid).kinds:
            assert kind.label_one["ru"] and kind.label_one["en"]
    profile = load_profile("management-four-boards")
    assert profile.kind_label("position", "ru") == "позиции"
    assert profile.kind_label_one("position", "ru") == "позиция"
    assert "- `p-organiser` позиция: " in render_markdown(oru, "ru")
    assert "<td>позиция</td>" in render_index(oru, ORU, "ru")
    nodes = {n["id"]: n for n in graph_model(oru, "ru")["nodes"]}
    assert nodes["p-organiser"]["kind"] == "позиция"
    data = yaml.safe_load(
        (profiles_dir() / "classic-two-boards.yaml").read_text(encoding="utf-8")
    )
    for bad in ({"ru": "позиция"}, "позиция", None):
        broken = copy.deepcopy(data)
        broken["kinds"][0]["label_one"] = bad
        if bad is None:
            del broken["kinds"][0]["label_one"]
        with pytest.raises(ProfileError, match="label_one needs ru and en"):
            profile_module._parse(broken, "classic-two-boards")


def test_frames_panel_and_vault_name_one_kind(
    oru: dict[str, Any], tmp_path: Path
) -> None:
    page = render_frames_html(reading_frames(oru, "ru"), "ru")
    start = page.index('id="smd-data">') + len('id="smd-data">')
    panel = json.loads(page[start : page.index("</script>", start)])
    metas = [e["meta"] for e in panel[oru["id"]]["el"].values()]
    assert any(m.startswith("позиция · ") for m in metas)
    assert not any(m.startswith("позиции · ") for m in metas)
    notes = export_vault(oru, tmp_path, "ru")
    text = "".join(p.read_text(encoding="utf-8") for p in notes if p.suffix == ".md")
    assert "вид: позиция" in text and "вид: позиции" not in text
