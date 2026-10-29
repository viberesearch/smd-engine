"""Renderer follow-ups of 0.5.5 (gate Г4 В): `acts_as` and `stance` shown where
`pace` is, the frames panel shows the element fields, the graph and the vault
label their `extra` entries, the Markdown element line follows `--lang`, and a
standalone `smd index` holds no absolute path."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from smd_engine.cli import main
from smd_engine.records import load_record
from smd_engine.render.frames import lighten_frames, reading_frames, zoom_frames
from smd_engine.render.frames_page import render_frames_html
from smd_engine.render.graph import graph_model, render_graph_html
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.markdown import render_markdown
from smd_engine.render.vault import export_vault

CASES = Path(__file__).resolve().parents[1] / "cases"
ORU = CASES / "example_ru" / "pekarni-oru-c1.board.yaml"
HOLDING = CASES / "example_ru" / "pekarnya-holding-c1.board.yaml"


@pytest.fixture
def oru() -> dict[str, Any]:
    return copy.deepcopy(load_record(ORU))


def _panel(page: str) -> dict[str, Any]:
    start = page.index('id="smd-data">') + len('id="smd-data">')
    data: dict[str, Any] = json.loads(page[start : page.index("</script>", start)])
    return data


def test_acts_as_and_stance_are_shown_where_pace_is(oru: dict[str, Any]) -> None:
    line = "занимает место: руководитель; позиция: внутренняя"
    assert f"<small>{line}</small>" in render_html(oru, "ru")
    assert f"<small>{line}</small>" in render_index(oru, ORU, "ru")
    assert "<small>acts as: leader; stance: inside</small>" in render_html(oru, "en")
    nodes = {n["id"]: n for n in graph_model(oru, "ru")["nodes"]}
    assert nodes["p-reflexive"]["extra"] == {"stance": "рефлексивная"}
    assert "acts as: politician" in render_markdown(oru, "en")


def test_frames_panel_shows_the_element_fields() -> None:
    case = load_record(HOLDING)
    case["elements"][0]["pace"] = 5  # p-owner
    for frames in (
        reading_frames(case, "ru"),
        lighten_frames(reading_frames(case, "ru"), "ru"),
        zoom_frames(reading_frames(case, "ru"), "ru"),
    ):
        els = _panel(render_frames_html(frames, "ru"))[case["id"]]["el"]
        assert els["p-owner"]["fields"] == (
            "меняется за 5 лет; занимает место: руководитель; позиция: внутренняя"
        )
        assert els["post-owner"]["fields"] == "системы (Бир): 3, 4, 5"
        assert "fields" not in els["grp-bakers"]
    assert "d.fields" in render_frames_html(reading_frames(case, "en"), "en")


def test_graph_and_vault_label_the_extra_keys(tmp_path: Path) -> None:
    case = load_record(HOLDING)
    case["elements"][0]["pace"] = 5
    model = graph_model(case, "ru")
    nodes = {n["id"]: n for n in model["nodes"]}
    assert nodes[case["elements"][0]["id"]]["extra"]["pace"] == "5 лет"
    assert model["extra_labels"]["pace"] == "темп изменения"
    assert model["extra_labels"]["recovery_time"] == "срок восстановления"
    assert "M.extra_labels[k]" in render_graph_html(case, "ru")
    written = export_vault(case, tmp_path, "ru")
    flour = next(p for p in written if p.stem.startswith("ch-flour"))
    text = flour.read_text(encoding="utf-8")
    assert "**срок восстановления**: 2 дня" in text
    assert "**recovery_time**" not in text


def test_markdown_element_line_follows_the_language(oru: dict[str, Any]) -> None:
    md = render_markdown(oru, "ru")
    assert (
        "- `g-plant` goal: тесто из общего цеха к весне с позиции `p-organiser`" in md
    )
    lines = [x for x in md.splitlines() if x.startswith("- `")]
    assert not any("seen from" in x or "fillers:" in x for x in lines)
    assert "seen from `p-organiser`" in render_markdown(oru, "en")


def test_standalone_index_holds_no_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    record = tmp_path / "rec" / HOLDING.name
    record.parent.mkdir()
    shutil.copy(HOLDING, record)
    out = tmp_path / "pages" / "index.html"
    assert main(["index", str(record), "-o", str(out)]) == 0
    page = out.read_text(encoding="utf-8")
    assert f'href="../rec/{HOLDING.name}"' in page
    assert "file://" not in page and "vscode://" not in page
    assert str(tmp_path) not in page
    monkeypatch.chdir(tmp_path)  # printed: relative to the current folder
    assert main(["index", str(record)]) == 0
    assert f'href="rec/{HOLDING.name}"' in capsys.readouterr().out
