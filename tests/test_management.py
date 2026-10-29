"""Gate Ш13 В amended by Ш15 В: G.P.'s management scheme as the profile
`management-four-boards`, its example and its hints (validate/management.py)."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine import profile as profile_module
from smd_engine.cli import main
from smd_engine.profile import ProfileError, load_profile, profiles_dir
from smd_engine.records import load_record
from smd_engine.render.frames import reading_frames
from smd_engine.render.graph import graph_model
from smd_engine.render.layout import plan
from smd_engine.render.svg import render_svg
from smd_engine.render.vault import export_vault
from smd_engine.validate import validate_record

ROOT = Path(__file__).resolve().parents[1]
ORU = ROOT / "cases" / "example_ru" / "pekarni-oru-c1.board.yaml"


@pytest.fixture
def oru() -> dict[str, Any]:
    return copy.deepcopy(load_record(ORU))


def hints(record: dict[str, Any], start: str = "") -> list[str]:
    return [
        f"{f.ref}: {f.message}"
        for f in validate_record(record)
        if f.level == "hint" and f.ref.startswith(start)
    ]


def rels(record: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = record["relations"]
    return out


def drop(record: dict[str, Any], test: Callable[[dict[str, Any]], bool]) -> None:
    record["relations"] = [r for r in rels(record) if not test(r)]


def el(record: dict[str, Any], eid: str) -> dict[str, Any]:
    return next(e for e in record["elements"] if e["id"] == eid)


def test_example_validates_with_only_the_open_gap(oru: dict[str, Any]) -> None:
    findings = [str(f) for f in validate_record(oru)]
    assert findings == [
        "hint: gap-shares: open gap: кто управляет цехом, если мельницы войдут в долю?"
    ]


def test_four_boards_upper_system_above_the_managed_one(oru: dict[str, Any]) -> None:
    profile = load_profile("management-four-boards")
    assert [[b.id for b in row] for row in profile.rows] == [["od", "ot"], ["ap", "us"]]
    assert {b.id for b in profile.boards if b.object} == {"ot", "us"}
    geo, boxes = plan(oru)
    assert geo.regions["ot"][3] < geo.regions["us"][1]
    assert geo.regions["ot"][0] == geo.regions["us"][0]
    for e in oru["elements"]:
        x0, y0, x1, _ = geo.regions[e["board"]]
        assert x0 - 1 <= boxes[e["id"]].x <= x1 + 1 and y0 <= boxes[e["id"]].y
    text = "".join(ET.fromstring(render_svg(oru, "en")).itertext())
    for name in profile.boards:
        assert name.label["en"] in text


def test_reading_steps_cover_the_four_boards(oru: dict[str, Any]) -> None:
    frames = reading_frames(oru, "en")
    assert [f.id for f in frames][:7] == [
        "positions",
        "places",
        "upper",
        "process-pb-dough",
        "process-pb-delivery",
        "apparatus",
        "managed",
    ]
    assert frames[3].title == "Process board: ночной замес теста"


def test_publish_and_vault_run_on_four_boards(tmp_path: Path) -> None:
    out = tmp_path / "pub"
    sources = str(ORU.parent / "sources.yaml")
    assert main(["publish", str(ORU), "--sources", sources, "--out", str(out)]) == 0
    assert (out / "pekarni-oru-c1_graph.html").exists()
    export_vault(load_record(ORU), tmp_path / "v", "en")
    assert (tmp_path / "v" / "Screen — four boards and 2 more.canvas").exists()


def test_a_hint_needs_the_kinds_and_relations_it_names() -> None:
    data = yaml.safe_load(
        (profiles_dir() / "classic-two-boards.yaml").read_text(encoding="utf-8")
    )
    data["hints"].append("polysystem")
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(copy.deepcopy(data), "classic-two-boards")
    assert str(exc.value) == (
        "classic-two-boards: missing kinds the engine names: ['monosystem']"
    )
    data["kinds"].append(dict(data["kinds"][-1], id="monosystem", home="oo"))
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(data, "classic-two-boards")
    assert str(exc.value) == (
        "classic-two-boards: missing relation kinds the hints name: "
        "['mechanism_of', 'parasitic', 'symbiotic']"
    )


def test_profile_relations_carry_labels(oru: dict[str, Any]) -> None:
    assert graph_model(oru, "ru")["edge_kinds"]["captures"] == "захватывает"
    data = yaml.safe_load(
        (profiles_dir() / "classic-two-boards.yaml").read_text(encoding="utf-8")
    )
    data["relations"].append("manages")
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(data, "classic-two-boards")
    assert str(exc.value) == (
        "classic-two-boards: relation 'manages' is not the engine's and needs a "
        "label {ru, en}"
    )
    data["relations"][-1] = {"id": "shift", "label": {"ru": "сдвиг", "en": "shift"}}
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(data, "classic-two-boards")
    assert "relation 'shift' is the engine's; it takes no label" in str(exc.value)


def test_lead_vs_manage(oru: dict[str, Any]) -> None:
    assert hints(oru, "relation p-owner->post-shift") == []
    oru["elements"].append(
        {
            "id": "g-own",
            "board": "od",
            "kind": "goal",
            "label": "своя смена",
            "seen_from": "p-baker",
            "goal_source": "own",
        }
    )
    oru["elements"].append(
        {"id": "p-baker", "board": "od", "kind": "position", "label": "пекарь"}
    )
    rels(oru).append({"from": "p-baker", "to": "post-shift", "kind": "belongs"})
    assert hints(oru, "relation p-owner->post-shift") == [
        "relation p-owner->post-shift: 'post-shift' is led, yet has goals of its own "
        "(g-own): management, not leadership? Руководство assumes the subordinate "
        "has no goals of its own (GP-T5 pp. 169-170; GP1975a p. 429)"
    ]


def test_manage_via_organizedness(oru: dict[str, Any]) -> None:
    drop(oru, lambda r: r["kind"] == "uses")
    assert hints(oru, "relation p-organiser->wp-dough") == [
        "relation p-organiser->wp-dough: managed through nothing: no element that "
        "'p-organiser' produces and 'wp-dough' uses. For G.P. one manages through "
        "organizednesses that then direct the processes (GP-T5 pp. 199, 222-223; "
        "GP-STS, IT p. 441)"
    ]


def test_manage_without_knowledge(oru: dict[str, Any]) -> None:
    el(oru, "k-proj")["seen_from"] = "p-founder"
    assert hints(oru, "p-organiser") == [
        "p-organiser: manages with no projective knowledge (seen from it or linked "
        "to it): for G.P. a system of ОРУ manages only when served by the "
        "organisation of knowledge, retrospective and projective; without it «и "
        "организация, и управление сводятся к руководству» (GP-T5 pp. 240-241)"
    ]
    rels(oru).append({"from": "k-proj", "to": "p-organiser", "kind": "refers"})
    assert hints(oru, "p-organiser") == []


def test_leads_outside_organisation(oru: dict[str, Any]) -> None:
    rels(oru).append({"from": "p-owner", "to": "post-shift", "kind": "belongs"})
    assert hints(oru, "relation p-owner->post-shift") == [
        "relation p-owner->post-shift: 'p-owner' and 'post-shift' hold the same "
        "place: руководство runs from one place to another (GP-T5 p. 242)"
    ]
    rels(oru).pop()
    drop(oru, lambda r: r["kind"] == "subordinates")
    assert hints(oru, "relation p-owner") == [
        "relation p-owner->post-shift: no line of subordination from the place of "
        "'p-owner' to that of 'post-shift': руководство is possible only within the "
        "administrative structure (GP-T5 pp. 242, 254; GP-Guide4 ¶12)"
    ]
    drop(oru, lambda r: r["kind"] == "belongs")
    assert hints(oru, "relation p-owner") == [
        "relation p-owner->post-shift: holds no place (a post, or `belongs` to one): "
        "p-owner. For G.P. «руководят не люди, а места» (GP-T5 p. 242)"
    ]


def test_representation_fit(oru: dict[str, Any]) -> None:
    rels(oru).append({"from": "p-owner", "to": "wp-dough", "kind": "represents"})
    el(oru, "p-founder")["acts_as"] = "functionary"
    assert hints(oru, "relation p-") == [
        "relation p-founder->mission: 'p-founder' acts as functionary and represents "
        "a mission: for G.P. a functionary takes no object (GP-Guide10 ¶7)",
        "relation p-owner->wp-dough: 'p-owner' acts as leader and represents a "
        "work_process, not one of post: for G.P. «руководят не люди, а места»: "
        "руководство holds the functioning of places (GP-T5 pp. 242, 244), and its "
        "subject is people's live activity and thinking, not technology (p. 223)",
    ]


def test_development_step(oru: dict[str, Any]) -> None:
    oru["elements"] = [
        e for e in oru["elements"] if e["kind"] not in ("fact", "knowledge_retro")
    ]
    oru["elements"] = [e for e in oru["elements"] if e["id"] != "ideal"]
    drop(oru, lambda r: r["kind"] == "captures" or "f-night" in r.values())
    drop(oru, lambda r: {r["from"], r["to"]} & {"ideal", "k-retro"} != set())
    oru["transitions"] = []
    del el(oru, "g-plant")["arises_from"]
    el(oru, "tr-natural").pop("modality")
    assert hints(oru, "ot") == [
        "ot: шаг развития incomplete: the ОРУ system, in the present, lacks the "
        "object's past (facts, retrospective knowledge); its ideal in the future "
        "(ideal_state); the managed system it captures (captures). For G.P. the "
        "scheme of ОРУ with the past and the future of its object «есть минимальная "
        "единица»: the upper part alone is not a management system (GP-T5 pp. 229, "
        "232, 238)"
    ]


def test_polysystem(oru: dict[str, Any]) -> None:
    drop(oru, lambda r: r["kind"] == "mechanism_of")
    assert hints(oru, "us") == [
        "us: monosystems in no relation to another (parasitic, symbiotic, "
        "mechanism_of; GP-T5 p. 208): mono-people, mono-tech"
    ]
    for e in oru["elements"]:
        if e.get("in") == ["mono-tech"]:
            del e["in"]
    oru["elements"] = [e for e in oru["elements"] if e["id"] != "mono-tech"]
    drop(oru, lambda r: "mono-tech" in r.values())
    assert hints(oru, "us") == [
        "us: 1 monosystem(s): for G.P. «реально мы имеем дело с полисистемами»: how "
        "many monosystems are there, and in what relations? (GP-T5 pp. 206, 213)"
    ]
