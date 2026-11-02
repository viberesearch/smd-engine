"""Deal mode, what an agenda still tells a reader about a point it hides: the
class of a value point, a buyer-side fact dispute, a rejected red line of the
annex, the pairs and the item numbers (`agenda_views.py`)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deal_helpers import by_id, edit_pack, set_answer
from smd_engine.task.model import load_task
from test_deal_views import ANNEX_DISCUSS, agendas, work  # noqa: F401

KEEP = {"handover": "keep"}
HANDOVER_KEEP = {m: dict(KEEP) for m in ("vera", "boris", "gleb")}


def entries(agenda: dict[str, Any], point: str) -> list[dict[str, Any]]:
    return [e for e in agenda["call"] + agenda["settled"] if e["id"] == point]


def add_items(work: Path) -> None:
    """A red line of the buyer's annex and a text for seller and buyer, put before
    the core items so that their numbers would skip."""

    def change(p: dict[str, Any]) -> None:
        p["items"][:0] = [
            {
                "id": "sb-shared",
                "section": "Own position",
                "question": "What do seller and buyer keep between them?",
                "kind": "text",
                "audience": ["seller", "buyer"],
                "call_title": "Between the parties",
            },
            {
                "id": "bx-line",
                "section": "Own position",
                "question": "Will you keep the staff for two years?",
                "kind": "line",
                "line": {
                    "metric": "staff kept",
                    "unit": "%",
                    "min": 90,
                    "since": "2026-12-01",
                    "until": "2027-12-31",
                    "recovery_days": 30,
                },
                "audience": ["buyer"],
                "call_title": "Own position",
            },
        ]

    edit_pack(work, change)
    set_answer(work, "vera", "sb-shared", {"value": "CANARY_SHARED_VERA"})
    set_answer(work, "boris", "sb-shared", {"value": "CANARY_SHARED_BORIS"})
    set_answer(work, "boris", "bx-line", {"value": "reject"})


def test_a_value_point_on_an_agenda_shows_open_or_settled_and_its_own_replies(
    work: Path, tmp_path: Path
) -> None:
    out = agendas(work, tmp_path, HANDOVER_KEEP)
    own = {"seller": {"vera", "gleb"}, "buyer": {"boris"}, "broker": {"vera", "gleb"}}
    for name, members in [(p, own[p]) for p in own] + [("", set())]:
        agenda = load_task(out / (f"agenda.{name}.yaml" if name else "agenda.yaml"))
        (entry,) = entries(agenda, "handover")
        assert entry["class"] in ("open", "settled")
        assert not {"class_by", "route", "subtype", "how"} & set(entry)
        assert set(entry.get("replies", {})) == members


def test_the_common_agenda_leaves_out_a_buyer_side_fact_dispute(
    work: Path, tmp_path: Path
) -> None:
    edit_pack(
        work,
        lambda p: next(i for i in p["items"] if i["id"] == "margin")["claim"].update(
            asserted_by="buyer"
        ),
    )
    out = agendas(work, tmp_path)
    point = by_id(load_task(out / "diff.yaml"))["margin"]
    assert point["class"] == "conflict" and point["buyer_claim"] is True
    for ext in ("yaml", "md"):
        shown = (out / f"agenda.{ext}").read_text(encoding="utf-8")
        assert "gross margin" not in shown and "Class: conflict" not in shown
    agenda = load_task(out / "agenda.yaml")
    assert not entries(agenda, "margin")
    c = agenda["counts"]
    assert c["points"] == len(agenda["call"]) + len(agenda["settled"])
    assert entries(load_task(out / "agenda.buyer.yaml"), "margin")


def test_a_rejected_annex_red_line_and_the_audience_of_a_point_stay_hidden(
    work: Path, tmp_path: Path
) -> None:
    add_items(work)
    discuss = {
        **ANNEX_DISCUSS,
        "vera": {"sale-reason": "discuss", "sb-shared": "discuss"},
    }
    out = agendas(work, tmp_path, discuss)
    agenda = load_task(out / "agenda.yaml")
    annex = [e for e in agenda["call"] if e.get("annex")]
    assert len(annex) >= 3 and all(e["why"] == {} for e in annex)
    handles = {e["id"] for e in annex}
    pairs = {pid for pair in agenda["call_by_pair"] for pid in pair["points"]}
    assert not handles & pairs
    text = (out / "agenda.md").read_text(encoding="utf-8")
    core = [
        e for e in agenda["call"] if not e.get("annex") and e["why"].get("blocking")
    ]
    assert text.count("red line always goes") == len(core) and "CANARY" not in text
    # the buyer's own agenda still says so
    buyer = {e["id"]: e for e in load_task(out / "agenda.buyer.yaml")["call"]}
    assert buyer["bx-line"]["why"]["blocking"] is True


def test_item_numbers_are_counted_over_the_items_the_reader_holds(
    work: Path, tmp_path: Path
) -> None:
    add_items(work)
    out = agendas(work, tmp_path)
    pack = load_task(work / "pack.yaml")
    core = [i["id"] for i in pack["items"] if "audience" not in i]
    seller = [
        i["id"] for i in pack["items"] if "seller" in i.get("audience", ["seller"])
    ]
    for name, ids in (("agenda", core), ("agenda.seller", seller)):
        numbers = load_task(out / f"{name}.yaml")["labels"]["numbers"]
        assert numbers == {i: n for n, i in enumerate(ids, 1)}, name
