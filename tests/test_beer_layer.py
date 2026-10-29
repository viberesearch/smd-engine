"""Gate Бир3 В: the Beer layer of `management-four-boards` (BEER1972), its
fields, kind, relations and hints (validate/management.py), and its example."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from smd_engine import profile as profile_module
from smd_engine.profile import ProfileError, load_profile, profiles_dir
from smd_engine.records import load_record
from smd_engine.render.graph import graph_model
from smd_engine.validate import validate_record

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "example_ru" / "pekarnya-holding-c1.board.yaml"
BEER_HINTS = (
    "single-node-metasystem",
    "line-without-recovery",
    "absorbed-into-system-1",
    "no-model-of-whole",
    "model-of-whole-one-filler",
)


@pytest.fixture
def case() -> dict[str, Any]:
    return copy.deepcopy(load_record(CASE))


def found(record: dict[str, Any], level: str, start: str = "") -> list[str]:
    return [
        f"{f.ref}: {f.message}"
        for f in validate_record(record)
        if f.level == level and f.ref.startswith(start)
    ]


def el(record: dict[str, Any], eid: str) -> dict[str, Any]:
    return next(e for e in record["elements"] if e["id"] == eid)


def classic() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(
        (profiles_dir() / "classic-two-boards.yaml").read_text(encoding="utf-8")
    )
    return data


def test_example_gives_each_beer_hint_once(case: dict[str, Any]) -> None:
    assert [f.level for f in validate_record(case)] == ["hint"] * 6
    hints = found(case, "hint")
    assert [h.split(":")[0] for h in hints] == [
        "gap-model",
        "post-owner",
        "ch-orders",
        "post-holding",
        "post-holding",
        "m-bakery",
    ]
    assert hints[4].startswith(
        "post-holding: 'post-holding' fills system 4, but neither it nor a position "
        "or post of its place uses a model of the whole (on the boards: m-bakery)"
    )
    assert hints[5].startswith(
        "m-bakery: the model of the whole 'm-bakery' is held by «владелец» alone "
        "(used by post-owner): it leaves with the person at transfer"
    )
    assert hints[1].startswith(
        "post-owner: «владелец» alone fills systems 3, 4 and 5 (post-owner): the "
        "metasystem is one person, and the transfer will remove it with the person"
    )
    assert hints[3].startswith(
        "post-holding: 'post-holding' fills system 5 and captures systems 4 and 5 "
        "of post-owner: the business becomes part of the buyer's system 1"
    )
    profile = load_profile("management-four-boards")
    assert set(BEER_HINTS) <= set(profile.hints)
    assert profile.kinds_where("vsm") == {"position", "post"}


def test_vsm_system_is_a_list_of_systems_on_posts_and_positions(
    case: dict[str, Any],
) -> None:
    el(case, "p-owner")["vsm_system"] = [5]
    assert found(case, "error") == []
    for bad, message in (
        ([0], "vsm_system/0: 0 is less than the minimum of 1"),
        ([6], "vsm_system/0: 6 is greater than the maximum of 5"),
        ([3, 3], "vsm_system: [3, 3] has non-unique elements"),
        (5, "vsm_system: 5 is not of type 'array'"),
        ([], "vsm_system: [] should be non-empty"),
    ):
        el(case, "post-owner")["vsm_system"] = bad
        assert any(message in e for e in found(case, "error")), bad
    el(case, "post-owner")["vsm_system"] = [3, 4, 5]
    el(case, "mono-bakery")["vsm_system"] = [1]
    assert found(case, "error") == [
        "mono-bakery: 'vsm_system' is only for kinds: position, post"
    ]
    other = copy.deepcopy(
        load_record(ROOT / "cases" / "example_ru" / "pekarni-c1.board.yaml")
    )
    position = next(e for e in other["elements"] if e["kind"] == "position")
    position["vsm_system"] = [5]
    assert found(other, "error") == [
        f"{position['id']}: 'vsm_system' is only for kinds a profile flags vsm, and "
        "profile 'program-three-boards' has none"
    ]


def test_algedonic_channel_takes_threshold_and_recovery_time(
    case: dict[str, Any],
) -> None:
    assert found(case, "warning") == []
    el(case, "ch-flour")["recovery_time"] = 0
    el(case, "ch-orders")["threshold"] = ""
    errors = found(case, "error")
    assert any(
        "recovery_time: 0 is less than or equal to the minimum of 0" in e
        for e in errors
    )
    assert any("threshold: '' should be non-empty" in e for e in errors)
    el(case, "ch-flour")["recovery_time"] = 0.5
    el(case, "ch-orders")["threshold"] = "задержка больше 1 дня"
    el(case, "ideal")["threshold"] = "5 утра"
    el(case, "post-owner")["recovery_time"] = 3
    assert found(case, "error") == [
        "ideal: 'threshold' is only for algedonic channels",
        "post-owner: 'recovery_time' is only for algedonic channels",
    ]
    other = copy.deepcopy(
        load_record(ROOT / "cases" / "example_ru" / "pekarni-c1.board.yaml")
    )
    other["elements"].append(
        {"id": "ch", "board": "oo", "kind": "algedonic_channel", "label": "x"}
    )
    assert found(other, "error") == [
        "ch: unknown kind 'algedonic_channel' in profile 'program-three-boards'"
    ]


def test_escalates_and_filters_are_labelled_relations(case: dict[str, Any]) -> None:
    edges = graph_model(case, "ru")["edge_kinds"]
    assert edges["escalates"] == "сигнал наверх"
    assert edges["filters"] == "фильтрует"
    assert graph_model(case, "en")["edge_kinds"]["filters"] == "filters"
    other = copy.deepcopy(
        load_record(ROOT / "cases" / "example_ru" / "pekarni-c1.board.yaml")
    )
    a, b = other["elements"][0]["id"], other["elements"][1]["id"]
    other["relations"].append({"from": a, "to": b, "kind": "escalates"})
    assert found(other, "error") == [
        f"relation {a}->{b}: unknown relation kind 'escalates' in profile "
        "'program-three-boards'"
    ]


def test_single_node_metasystem(case: dict[str, Any]) -> None:
    owner = el(case, "post-owner")
    owner["fillers"] = ["владелец", "управляющий", "главный технолог"]
    assert found(case, "hint", "post-owner") == []  # a multinode (Гл. 14)
    owner["fillers"] = ["владелец"]
    owner["vsm_system"] = [3, 4]
    assert found(case, "hint", "post-owner") == []
    # the owner's position, with no fillers, is the filler of its post
    el(case, "p-owner")["vsm_system"] = [5]
    assert found(case, "hint", "p-owner") == [
        "p-owner: «владелец» alone fills systems 3, 4 and 5 (p-owner, post-owner): "
        "the metasystem is one person, and the transfer will remove it with the "
        "person. For Beer the model of the firm is kept in system 4: «Если бы такой "
        "модели не было, то высшее руководство не имело бы представления о том, "
        "какой фирмой оно управляет» (BEER1972 Гл. 13)"
    ]
    # a post with no fillers is filled by the one position that belongs to it
    del owner["fillers"]
    assert [h.split(":")[1] for h in found(case, "hint", "p-owner")] == [
        " 'p-owner' alone fills systems 3, 4 and 5 (p-owner, post-owner)"
    ]
    case["relations"].append({"from": "p-map", "to": "post-owner", "kind": "belongs"})
    assert found(case, "hint", "p-owner") == []


def test_line_without_recovery(case: dict[str, Any]) -> None:
    assert found(case, "hint", "ch-orders")[0].startswith(
        "ch-orders: a red line with a threshold and no recovery time (recovery_time) "
        "and no escalation address (escalates to a post, position or place for "
        "others): for Beer a unit that cannot restore its index «в приемлемое время» "
        "sends the signal up"
    )
    el(case, "ch-orders")["recovery_time"] = 1
    case["relations"].append(
        {"from": "ch-orders", "to": "f-owner", "kind": "escalates"}
    )
    assert found(case, "hint", "ch-orders")[0].startswith(
        "ch-orders: a red line with a threshold and no escalation address"
    )
    case["relations"][-1]["to"] = "place-heir"
    assert found(case, "hint", "ch-orders") == []
    del el(case, "ch-flour")["recovery_time"]
    assert found(case, "hint", "ch-flour")[0].startswith(
        "ch-flour: a red line with a threshold and no recovery time (recovery_time):"
    )
    del el(case, "ch-flour")["threshold"]
    assert found(case, "hint", "ch-flour") == []


def test_absorbed_into_system_1(case: dict[str, Any]) -> None:
    # the holding uses a model of the whole, so no-model-of-whole gives no hint
    case["relations"].append({"from": "post-holding", "to": "m-bakery", "kind": "uses"})
    el(case, "post-holding")["vsm_system"] = [4]
    assert found(case, "hint", "post-holding") == []
    el(case, "post-holding")["vsm_system"] = [5]
    el(case, "post-owner")["vsm_system"] = [3, 5]
    assert found(case, "hint", "post-holding") == []
    # the target's 4 and 5 on two places, each captured
    case["elements"].append(
        {
            "id": "post-dev",
            "board": "ap",
            "kind": "post",
            "label": "развитие",
            "vsm_system": [4],
        }
    )
    case["relations"].append(
        {"from": "post-holding", "to": "post-dev", "kind": "captures"}
    )
    assert found(case, "hint", "post-holding")[0].startswith(
        "post-holding: 'post-holding' fills system 5 and captures systems 4 and 5 of "
        "post-owner, post-dev:"
    )
    assert (
        "«через несколько лет исчезает совсем» (BEER1972 Гл. 15)"
        in found(case, "hint", "post-holding")[0]
    )


def test_profile_refuses_beer_hints_without_their_kinds_and_flags() -> None:
    data = classic()
    data["hints"].append("line-without-recovery")
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(copy.deepcopy(data), "classic-two-boards")
    assert str(exc.value) == (
        "classic-two-boards: missing kinds the engine names: "
        "['algedonic_channel', 'post']"
    )
    for kid in ("algedonic_channel", "post"):
        data["kinds"].append(dict(data["kinds"][-1], id=kid, home="oo"))
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(copy.deepcopy(data), "classic-two-boards")
    assert str(exc.value) == (
        "classic-two-boards: missing relation kinds the hints name: ['escalates']"
    )
    data = classic()
    data["kinds"][0]["vsm"] = "yes"
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(data, "classic-two-boards")
    assert str(exc.value).endswith("vsm must be true or false")


def test_beer_hints_read_vsm_system_only_on_kinds_flagged_vsm(
    case: dict[str, Any],
) -> None:
    el(case, "post-owner")["vsm_system"] = [3]
    mono = next(e for e in case["elements"] if e["kind"] == "monosystem")
    mono["vsm_system"] = [3, 4, 5]
    assert found(case, "error", mono["id"])  # the structure check refuses it
    assert found(case, "hint", mono["id"]) == []
    assert found(case, "hint", "post-owner") == []
    el(case, "post-owner")["vsm_system"] = [3, 4, 5]
    case["relations"].append(
        {"from": mono["id"], "to": "post-owner", "kind": "captures"}
    )
    assert found(case, "hint", mono["id"]) == []


def test_absorbed_into_system_1_names_a_captured_place_once(
    case: dict[str, Any],
) -> None:
    case["relations"].append(
        {"from": "post-holding", "to": "post-owner", "kind": "captures"}
    )
    assert found(case, "hint", "post-holding")[0].startswith(
        "post-holding: 'post-holding' fills system 5 and captures systems 4 and 5 "
        "of post-owner: the business"
    )


def test_profile_refuses_beer_hints_without_a_kind_flagged_vsm() -> None:
    data = yaml.safe_load(
        (profiles_dir() / "management-four-boards.yaml").read_text(encoding="utf-8")
    )
    for k in data["kinds"]:
        k.pop("vsm", None)
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(copy.deepcopy(data), "management-four-boards")
    assert str(exc.value) == (
        "management-four-boards: the hints ['absorbed-into-system-1', "
        "'no-model-of-whole', 'single-node-metasystem'] read vsm_system and need a "
        "kind flagged vsm"
    )
    data["hints"] = [h for h in data["hints"] if h not in profile_module.VSM_HINTS]
    assert profile_module._parse(data, "management-four-boards").hints


def test_of_whole_is_a_flag_of_models(case: dict[str, Any]) -> None:
    assert load_profile("management-four-boards").kinds_where("of_whole") == {"model"}
    el(case, "post-owner")["of_whole"] = True
    assert found(case, "error") == ["post-owner: 'of_whole' is only for kinds: model"]
    el(case, "post-owner").pop("of_whole")
    el(case, "m-bakery")["of_whole"] = "yes"
    assert any(
        "of_whole: 'yes' is not of type 'boolean'" in e for e in found(case, "error")
    )
    other = copy.deepcopy(
        load_record(ROOT / "cases" / "example_ru" / "pekarni-c1.board.yaml")
    )
    el(other, "m-coop")["of_whole"] = True
    assert found(other, "error") == [
        "m-coop: 'of_whole' is only for kinds a profile flags of_whole, and profile "
        "'program-three-boards' has none"
    ]


def test_no_model_of_whole(case: dict[str, Any]) -> None:
    el(case, "m-bakery")["of_whole"] = False  # a model, but not of the whole
    assert [h[:60] for h in found(case, "hint", "post-")][1:] == [
        "post-holding: 'post-holding' fills system 5 and captures sys",
        "post-owner: 'post-owner' fills system 4, but no model of the",
        "post-holding: 'post-holding' fills system 4, but no model of",
    ]
    el(case, "m-bakery")["of_whole"] = True
    assert len(found(case, "hint", "post-holding")) == 2
    # a position that belongs to the post holds it for the post, and the post
    # for a position that belongs to it
    case["relations"].append({"from": "p-holding", "to": "m-bakery", "kind": "uses"})
    assert len(found(case, "hint", "post-holding")) == 1
    el(case, "p-owner")["vsm_system"] = [4]
    assert not any("system 4, but" in h for h in found(case, "hint", "p-owner"))
    # another position of the same post holds it through that post
    case["elements"].append(
        {
            "id": "p-h2",
            "board": "od",
            "kind": "position",
            "label": "x",
            "vsm_system": [4],
        }
    )
    case["relations"].append({"from": "p-h2", "to": "post-holding", "kind": "belongs"})
    assert not any("system 4, but" in h for h in found(case, "hint", "p-h2"))
    el(case, "p-map")["vsm_system"] = [4]
    assert found(case, "hint", "p-map")[0].startswith(
        "p-map: 'p-map' fills system 4, but neither it nor"
    )
    assert (
        "«тем не менее общая модель должна быть у фирмы."
        in found(case, "hint", "p-map")[0]
    )


def test_model_of_whole_one_filler(case: dict[str, Any]) -> None:
    uses = {"from": "p-owner", "to": "m-bakery", "kind": "uses"}
    case["relations"].append(uses)  # the owner's position: the same filler
    assert found(case, "hint", "m-bakery")[0].startswith(
        "m-bakery: the model of the whole 'm-bakery' is held by «владелец» alone "
        "(used by post-owner, p-owner):"
    )
    # the owner's reflexive position is the same person, an heir's is not
    case["elements"].append(
        {
            "id": "p-refl",
            "board": "od",
            "kind": "reflexive_position",
            "label": "x",
            "fillers": ["владелец"],
        }
    )
    case["relations"].append({"from": "p-refl", "to": "m-bakery", "kind": "uses"})
    assert (
        "(used by post-owner, p-owner, p-refl):" in found(case, "hint", "m-bakery")[0]
    )
    el(case, "p-refl")["fillers"] = ["наследник"]
    assert found(case, "hint", "m-bakery") == []
    case["relations"].pop()
    uses["from"] = "post-shift"  # a second person
    assert found(case, "hint", "m-bakery") == []
    uses["from"] = "grp-bakers"  # a group is more than one
    assert found(case, "hint", "m-bakery") == []
    case["relations"].remove(uses)
    el(case, "post-owner")["fillers"] = ["владелец", "управляющий"]  # a multinode
    assert found(case, "hint", "m-bakery") == []
    del el(case, "post-owner")["fillers"]  # no filler named: no person to name
    assert found(case, "hint", "m-bakery") == []
    case["relations"] = [r for r in case["relations"] if r["kind"] != "uses"]
    assert found(case, "hint", "m-bakery") == []  # held by nobody


def test_written_model_of_whole_does_not_leave_with_its_holder(
    case: dict[str, Any],
) -> None:
    """Gate Г5б Б: a model of the whole written down and kept apart from the
    people stays when its one holder leaves; the other hints still read it."""
    assert len(found(case, "hint", "m-bakery")) == 1
    el(case, "m-bakery")["written"] = True
    assert found(case, "error") == []
    assert found(case, "hint", "m-bakery") == []
    assert len(found(case, "hint", "post-holding")) == 2  # no-model-of-whole stays
    el(case, "m-bakery")["written"] = False
    assert len(found(case, "hint", "m-bakery")) == 1


def test_written_model_of_whole_still_needs_a_keeper(case: dict[str, Any]) -> None:
    """Gate Г7г А: a written model of the whole that nobody `uses` does not
    satisfy `no-model-of-whole`; the places filling system 4 still get it."""
    el(case, "m-bakery")["written"] = True
    case["relations"] = [
        r for r in case["relations"] if (r["kind"], r["to"]) != ("uses", "m-bakery")
    ]
    hints = [h for h in found(case, "hint") if "fills system 4, but" in h]
    assert [h.split(":")[0] for h in hints] == ["post-owner", "post-holding"]
    assert found(case, "hint", "m-bakery") == []
    el(case, "post-owner")["written"] = True
    assert found(case, "error") == ["post-owner: 'written' is only for kinds: model"]
    el(case, "post-owner").pop("written")
    el(case, "m-bakery")["written"] = "yes"
    assert any(
        "written: 'yes' is not of type 'boolean'" in e for e in found(case, "error")
    )
    other = copy.deepcopy(
        load_record(ROOT / "cases" / "example_ru" / "pekarni-c1.board.yaml")
    )
    el(other, "m-coop")["written"] = True
    assert found(other, "error") == [
        "m-coop: 'written' is only for kinds a profile flags of_whole, and profile "
        "'program-three-boards' has none"
    ]


def test_profile_refuses_model_of_whole_hints_without_the_flag() -> None:
    data = yaml.safe_load(
        (profiles_dir() / "management-four-boards.yaml").read_text(encoding="utf-8")
    )
    for k in data["kinds"]:
        k.pop("of_whole", None)
    with pytest.raises(ProfileError) as exc:
        profile_module._parse(copy.deepcopy(data), "management-four-boards")
    assert str(exc.value) == (
        "management-four-boards: the hints ['model-of-whole-one-filler', "
        "'no-model-of-whole'] read of_whole and need a kind flagged of_whole"
    )
    data["hints"] = [h for h in data["hints"] if h not in profile_module.OF_WHOLE_HINTS]
    assert profile_module._parse(data, "management-four-boards").hints


def test_written_without_of_whole_is_read_by_nothing(case: dict[str, Any]) -> None:
    el(case, "m-bakery")["of_whole"] = False
    el(case, "m-bakery")["written"] = True
    assert found(case, "error") == []
    assert found(case, "hint", "m-bakery") == []
