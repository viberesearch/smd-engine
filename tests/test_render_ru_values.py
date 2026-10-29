"""Russian words for the fixed values of a record (gate Г6, option Б): relation
kinds, epistemic status, move status, frame state, record status, a thesis's
voice, belt and kind, sign-off functions and the board of an element. The
English pages keep the ids; ids in code spans and data stay as recorded."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from smd_engine.records import load_record
from smd_engine.render.frames import reading_frames
from smd_engine.render.frames_page import render_frames_html
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.markdown import render_markdown
from smd_engine.render.svg import render_svg

CASES = Path(__file__).resolve().parents[1] / "cases"
C2_RU = CASES / "example_ru" / "pekarni-c2.board.yaml"
ORU = CASES / "example_ru" / "pekarni-oru-c1.board.yaml"


@pytest.fixture
def c2() -> dict[str, Any]:
    return copy.deepcopy(load_record(C2_RU))


def test_relation_kinds_by_the_graph_and_profile_words() -> None:
    md = render_markdown(load_record(C2_RU), "ru")
    assert "- `p-owner` → `p-organiser` (сдвиг позиции) — другая позиция" in md
    assert "(shift)" not in md and "(represents)" not in md
    oru = render_markdown(load_record(ORU), "ru")
    assert "- `p-organiser` → `wp-dough` (управляет) — через договор" in oru
    assert "(shift) — другая позиция" in render_markdown(load_record(C2_RU), "en")


def test_epistemic_status(c2: dict[str, Any]) -> None:
    md = render_markdown(c2, "ru")
    assert "организатор общего производства [гипотеза]" in md
    assert "[hypothesis]" not in md
    page = render_frames_html(reading_frames(c2, "ru"), "ru")
    start = page.index('id="smd-data">') + len('id="smd-data">')
    panel = json.loads(page[start : page.index("</script>", start)])
    metas = [e["meta"] for e in panel[c2["id"]]["el"].values()]
    assert any(m.endswith(" · гипотеза") for m in metas)
    assert not any("hypothesis" in m for m in metas)
    assert "[hypothesis]" in render_markdown(c2, "en")


def test_move_status(c2: dict[str, Any]) -> None:
    assert "(принят)" in render_markdown(c2, "ru")
    move = next(e for e in c2["elements"] if e.get("move"))
    move["move"]["status"] = "candidate"
    assert "(кандидат)" in render_markdown(c2, "ru")
    assert "(candidate)" in render_markdown(c2, "en")


def test_frame_state() -> None:
    md = render_markdown(load_record(C2_RU), "ru")
    assert "розничная пекарня (старая) с позиции `p-owner`" in md
    assert "для независимых пекарен (новая) с позиции" in md
    assert "(new) seen from" in render_markdown(load_record(C2_RU), "en")


def test_record_status(c2: dict[str, Any]) -> None:
    assert "· цикл 2 · черновик ·" in render_markdown(c2, "ru")
    assert "ЦИКЛ 2 · ЧЕРНОВИК" in render_svg(c2, "ru")
    c2["status"] = "verified"
    assert "· цикл 2 · сверено ·" in render_markdown(c2, "ru")
    assert "· cycle 2 · verified ·" in render_markdown(c2, "en")


def test_thesis_voice_belt_and_kind(c2: dict[str, Any]) -> None:
    md = render_markdown(c2, "ru")
    assert "[Прозвучало в группе] группа, мД, затруднение:" in md
    assert "[Предложение модератора / эксперта] модератор, М-К, задача:" in md
    assert "<td>модератор</td>" in render_html(c2, "ru")
    assert "<td>модератор, Предложение" in render_index(c2, C2_RU, "ru")
    assert "group, md, difficulty:" in render_markdown(c2, "en")


def test_signoff_function_by_its_words(c2: dict[str, Any]) -> None:
    assert "- принять ход `m-coop`: group" in render_markdown(c2, "ru")
    assert "<tr><td>принять ход</td>" in render_html(c2, "ru")
    index = render_index(c2, C2_RU, "ru")
    assert "<tr><td>принять ход<br>" in index and "accept_move" not in index
    assert "- accept_move `m-coop`: group" in render_markdown(c2, "en")


def test_page_element_table_names_the_board(c2: dict[str, Any]) -> None:
    page = render_html(c2, "ru")
    assert "<td>Ситуационная доска / малая</td>" in page
    assert "<td>s/small</td>" not in page and "<td>od</td>" not in page
    assert "<td>Ситуационная доска / малая</td>" in render_index(c2, C2_RU, "ru")
    assert "<td>Situation board / small</td>" in render_html(c2, "en")
