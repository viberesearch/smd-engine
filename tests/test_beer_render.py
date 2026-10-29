"""The renderers show the Beer fields of `management-four-boards` where they
show `pace`: `vsm_system` of posts and positions, `threshold` and
`recovery_time` of algedonic channels (BEER1972)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.records import load_record
from smd_engine.render.graph import graph_model
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.markdown import render_markdown
from smd_engine.render.vault import export_vault

CASE = (
    Path(__file__).resolve().parents[1]
    / "cases"
    / "example_ru"
    / "pekarnya-holding-c1.board.yaml"
)


@pytest.fixture
def case() -> dict[str, Any]:
    return copy.deepcopy(load_record(CASE))


def test_graph_puts_the_fields_in_extra(case: dict[str, Any]) -> None:
    nodes = {n["id"]: n for n in graph_model(case, "ru")["nodes"]}
    assert nodes["post-owner"]["extra"] == {"vsm_system": "3, 4, 5"}
    assert nodes["ch-flour"]["extra"] == {
        "threshold": "мука меньше чем на 4 дня выпечки",
        "recovery_time": "2 дня",
    }
    assert "extra" not in nodes["grp-bakers"]
    case["elements"][0]["pace"] = 5
    first = graph_model(case, "en")["nodes"][0]
    assert first["extra"] == {
        "pace": "5 years",
        "acts_as": "leader",
        "stance": "inside",
    }


def test_vault_notes_show_the_fields(case: dict[str, Any], tmp_path: Path) -> None:
    written = export_vault(case, tmp_path, "en")
    text = next(p for p in written if p.stem.startswith("ch-flour")).read_text(
        encoding="utf-8"
    )
    assert "**threshold**: мука меньше чем на 4 дня выпечки" in text
    assert "**recovery time**: 2 days" in text
    post = next(p for p in written if p.stem.startswith("post-shift"))
    assert "**systems (Beer)**: 1" in post.read_text(encoding="utf-8")


def test_html_shows_the_fields_under_the_label(case: dict[str, Any]) -> None:
    page = render_html(case, "ru")
    assert (
        "<small>порог: мука меньше чем на 4 дня выпечки; "
        "срок восстановления: 2 дня</small>"
    ) in page
    assert "<small>системы (Бир): 4, 5</small>" in page
    assert "<small>systems (Beer): 3, 4, 5</small>" in render_html(case, "en")


def test_index_shows_the_fields_under_the_label(case: dict[str, Any]) -> None:
    page = render_index(case, CASE, "ru")
    assert "<small>порог: задержка больше 1 дня</small>" in page
    assert "<small>системы (Бир): 1</small>" in page
    el = next(e for e in case["elements"] if e["id"] == "ch-flour")
    el["recovery_time"] = 5
    assert "срок восстановления: 5 дней" in render_index(case, CASE, "ru")
    assert "recovery time: 5 days" in render_index(case, CASE, "en")


def test_markdown_line_shows_the_fields(case: dict[str, Any]) -> None:
    md = render_markdown(case, "ru")
    assert (
        "- `ch-flour` алгедонический канал: запас муки ниже нормы "
        "порог: мука меньше чем на 4 дня выпечки срок восстановления: 2 дня "
        "с позиции `p-map`"
    ) in md
    assert "кто может занять: владелец системы (Бир): 3, 4, 5" in md


def test_model_of_whole_is_shown(case: dict[str, Any]) -> None:
    nodes = {n["id"]: n for n in graph_model(case, "ru")["nodes"]}
    assert nodes["m-bakery"]["extra"] == {"of_whole": "да"}
    assert "модель целого (Бир): да" in render_html(case, lang="ru")
    assert "model of the whole (Beer): yes" in render_markdown(case, lang="en")
    for e in case["elements"]:
        if e["id"] == "m-bakery":
            e["of_whole"] = False
    nodes = {n["id"]: n for n in graph_model(case, "ru")["nodes"]}
    assert "extra" not in nodes["m-bakery"]


def test_written_model_of_whole_is_shown(case: dict[str, Any]) -> None:
    for e in case["elements"]:
        if e["id"] == "m-bakery":
            e["written"] = True
    nodes = {n["id"]: n for n in graph_model(case, "ru")["nodes"]}
    assert nodes["m-bakery"]["extra"] == {"of_whole": "да", "written": "да"}
    assert "записана: да" in render_html(case, lang="ru")
    assert "written down: yes" in render_markdown(case, lang="en")
