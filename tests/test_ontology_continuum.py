"""The space-time continuum of an ontology record: `lives_in`, `tempos`,
`horizon`, `covers`, the element field `pace` and the hint
`ontology-outlives-pace` (Khaprov, podcast 28.10.2026)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smd_engine.apply import apply_patch
from smd_engine.compare import report
from smd_engine.render.graph import graph_model
from smd_engine.render.html import render_html
from smd_engine.render.index import render_index
from smd_engine.render.markdown import render_markdown
from smd_engine.render.text import years_text
from smd_engine.render.vault import export_vault
from smd_engine.revise import revise
from smd_engine.validate import validate_record

EXAMPLE = Path(__file__).resolve().parents[1] / "cases" / "example"
HINT = "the continuum is exhausted before the horizon"
CITE = " (Khaprov, podcast 28.10.2026, l.154-172)"
PATCH = {
    "record": "board_patch",
    "schema_version": "0.1",
    "id": "bakeries-c2-9",
    "applies_to": "bakeries-c2",
    "version": "0.2.9",
}


def levels(record: dict[str, Any], level: str) -> list[str]:
    return [
        f"{f.ref}: {f.message}" for f in validate_record(record) if f.level == level
    ]


def hints(record: dict[str, Any]) -> list[str]:
    return [h for h in levels(record, "hint") if HINT in h]


def with_continuum(board2: dict[str, Any]) -> dict[str, Any]:
    els = {e["id"]: e for e in board2["elements"]}
    els["fn-logistics"]["pace"] = 5
    els["coop-plant"]["pace"] = 20
    board2["ontology"][0] |= {
        "lives_in": [
            {"id": "s-big"},
            {"id": "fn-logistics"},
            {"text": "Регион: сети и мельницы"},
        ],
        "tempos": [{"text": "delivery business models", "years": 5}],
        "horizon": 10,
    }
    return board2


def test_fields_are_valid_and_ids_are_checked(board2: dict[str, Any]) -> None:
    board2 = with_continuum(board2)
    assert levels(board2, "error") == []
    o1 = board2["ontology"][0]
    o1["lives_in"].append({"id": "mills"})
    o1["covers"] = ["ghost"]
    o1["tempos"].append({"id": "plant-x", "years": 3})
    assert levels(board2, "error") == [
        "O1: lives_in 'mills' is not an element",
        "O1: covers 'ghost' is not an element",
        "O1: tempos 'plant-x' is not an element",
    ]
    board2["elements"][0]["pace"] = 0
    o1["lives_in"].append({"id": "s-big", "text": "both"})
    o1["covers"] = ["s-big", "s-big"]
    errors = levels(board2, "error")
    assert any("pace: 0 is less than or equal to the minimum of 0" in e for e in errors)
    assert any("lives_in/4" in e for e in errors)
    assert any(
        "covers: ['s-big', 's-big'] has non-unique elements" in e for e in errors
    )


def test_hint_when_pace_or_tempo_is_shorter_than_horizon(
    board2: dict[str, Any],
) -> None:
    board2 = with_continuum(board2)
    assert hints(board2) == [
        "O1: the ontology is expected to hold 10 years, but 'fn-logistics' changes "
        "every 5 years: " + HINT + CITE,
        "O1: the ontology is expected to hold 10 years, but 'delivery business "
        "models' changes every 5 years: " + HINT + CITE,
    ]
    del board2["ontology"][0]["horizon"]
    assert hints(board2) == []


def test_covers_adds_to_lives_in(board2: dict[str, Any]) -> None:
    els = {e["id"]: e for e in board2["elements"]}
    els["fn-logistics"]["pace"] = 2
    els["fn-dough"]["pace"] = 1
    board2["ontology"][0] |= {
        "lives_in": [{"id": "fn-logistics"}],
        "covers": ["fn-dough"],
        "horizon": 10,
    }
    assert hints(board2) == [
        "O1: the ontology is expected to hold 10 years, but 'fn-logistics' changes "
        "every 2 years: " + HINT + CITE,
        "O1: the ontology is expected to hold 10 years, but 'fn-dough' changes "
        "every 1 year: " + HINT + CITE,
    ]


def test_no_fields_no_hint(board2: dict[str, Any]) -> None:
    board2["elements"][0]["pace"] = 1
    assert hints(board2) == []


def test_years_in_russian_and_english() -> None:
    got = [years_text(n, "ru") for n in (1, 2, 5, 11, 21, 22, 112, 2.5)]
    assert got == [
        "1 год",
        "2 года",
        "5 лет",
        "11 лет",
        "21 год",
        "22 года",
        "112 лет",
        "2.5 года",
    ]
    assert [years_text(n, "en") for n in (1, 3)] == ["1 year", "3 years"]


def test_patch_sets_and_remove_unlinks(board2: dict[str, Any]) -> None:
    fields = {
        "lives_in": [{"id": "s-big"}, {"text": "Регион"}],
        "tempos": [{"id": "s-big", "years": 3}, {"text": "сети", "years": 4}],
        "horizon": 8,
        "covers": ["s-big"],
    }
    new = apply_patch(board2, {**PATCH, "set": [{"id": "O1", **fields}]})
    assert {k: new["ontology"][0][k] for k in fields} == fields
    gone = apply_patch(
        new,
        {**PATCH, "id": "bakeries-c2-10", "remove": [{"id": "s-big", "reason": "x"}]},
    )
    assert gone["ontology"][0]["lives_in"] == [{"text": "Регион"}]
    assert gone["ontology"][0]["tempos"] == [{"text": "сети", "years": 4}]
    assert "covers" not in gone["ontology"][0]


def test_revise_carries_and_renderers_show(board2: dict[str, Any]) -> None:
    board2 = with_continuum(board2)
    new, _ = revise(board2, date="2026-02-01")
    assert new["ontology"] == board2["ontology"]
    assert new["elements"] == board2["elements"]
    md = render_markdown(board2, "en")
    assert "  - lives in: s-big, fn-logistics, Регион: сети и мельницы" in md
    assert "  - tempos: delivery business models 5 years" in md
    assert "  - horizon: 10 years" in md and "pace: 5 years" in md
    assert "  - горизонт: 10 лет" in render_markdown(board2, "ru")
    page = render_index(board2, EXAMPLE / "bakeries-c2.board.yaml", "ru")
    assert "темпы: delivery business models 5 лет; горизонт: 10 лет" in page
    assert "<small>меняется за 5 лет</small>" in page
    other = with_continuum(revise(board2, date="2026-02-01")[0])
    other["ontology"][0]["horizon"] = 4
    text = report(board2, other)
    assert "## ontology: continuum" in text
    assert "; horizon 10 years / 4 years" in text


def test_index_shows_covers_alone(board2: dict[str, Any]) -> None:
    board2["ontology"][0]["covers"] = ["fn-dough"]
    page = render_index(board2, EXAMPLE / "bakeries-c2.board.yaml", "ru")
    assert "<small>охватывает: fn-dough</small>" in page


def test_compare_without_fields_has_no_section(board2: dict[str, Any]) -> None:
    assert "## ontology" not in report(board2, board2)


def test_graph_vault_and_html_show_the_fields(
    board2: dict[str, Any], tmp_path: Path
) -> None:
    plain = graph_model(board2, "en")
    assert "covers" not in plain["edge_kinds"] and "lives_in" not in plain["edge_kinds"]
    board2 = with_continuum(board2)
    board2["ontology"][0]["covers"] = ["fn-dough"]
    model = graph_model(board2, "en")
    nodes = {n["id"]: n for n in model["nodes"]}
    assert nodes["O1"]["extra"]["horizon"] == "10 years"
    assert nodes["O1"]["extra"]["covers"] == "fn-dough"
    assert nodes["fn-logistics"]["extra"] == {"pace": "5 years"}
    links = {(e["t"], e["k"]) for e in model["edges"] if e["s"] == "O1"}
    assert {("s-big", "lives_in"), ("fn-logistics", "lives_in")} <= links
    assert ("fn-dough", "covers") in links and model["edge_kinds"]["covers"] == "covers"
    written = export_vault(board2, tmp_path, "en")
    note = next(p for p in written if p.stem.startswith("O1"))
    text = note.read_text(encoding="utf-8")
    assert "**tempos**: delivery business models 5 years" in text
    assert "covers:" in text
    page = render_html(board2, "ru")
    assert "живёт в: s-big, fn-logistics" in page and "охватывает: fn-dough" in page
    assert "<small>меняется за 5 лет</small>" in page
