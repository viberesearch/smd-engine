from __future__ import annotations

from typing import Any

import pytest

from smd_engine import validate
from smd_engine.sources import source_ids
from smd_engine.validate import Check, Ctx, Finding, validate_record


def levels(findings: list[Any], level: str) -> list[str]:
    return [f"{f.ref}: {f.message}" for f in findings if f.level == level]


def test_example_is_clean(board: dict[str, Any], manifest: dict[str, Any]) -> None:
    findings = validate_record(board, source_ids(manifest))
    assert levels(findings, "error") == []
    assert levels(findings, "warning") == []


def test_schema_error_stops_semantic_checks(board: dict[str, Any]) -> None:
    board["elements"][0]["board"] = "xx"
    findings = validate_record(board)
    assert findings and all(f.level == "error" for f in findings)


def test_dangling_references(board: dict[str, Any]) -> None:
    board["elements"][7]["in"] = ["missing-frame"]
    board["transitions"][0]["to"] = "nowhere"
    board["qualifications"][0]["targets"] = ["ghost"]
    errors = levels(validate_record(board), "error")
    assert any("missing-frame" in e for e in errors)
    assert any("nowhere" in e for e in errors)
    assert any("ghost" in e for e in errors)


def test_seen_from_must_be_a_position(board: dict[str, Any]) -> None:
    board["elements"][5]["seen_from"] = "s-small"
    assert any(
        "must be a position" in e for e in levels(validate_record(board), "error")
    )


def test_half_rules(board: dict[str, Any]) -> None:
    small = next(e for e in board["elements"] if e["id"] == "s-small")
    del small["half"]
    board["elements"][1]["half"] = "small"
    errors = levels(validate_record(board), "error")
    assert any("needs 'half'" in e for e in errors)
    assert any("only for the situation board" in e for e in errors)


def test_transition_numbering_and_same_board(board: dict[str, Any]) -> None:
    board["transitions"][2]["n"] = 5
    errors = levels(validate_record(board), "error")
    assert any("1..n" in e for e in errors)
    board["transitions"][2]["n"] = 3
    board["transitions"][2]["to"] = "s-big-signal"
    warnings = levels(validate_record(board), "warning")
    assert any("within one board" in w for w in warnings)


def test_containment_cycle(board: dict[str, Any]) -> None:
    frame = next(e for e in board["elements"] if e["id"] == "f-new")
    frame["in"] = ["fn-dough"]
    fn = next(e for e in board["elements"] if e["id"] == "fn-dough")
    fn["kind"] = "other"
    errors = levels(validate_record(board), "error")
    assert any("cycle" in e for e in errors)


def test_qualification_rules(board: dict[str, Any]) -> None:
    board["qualifications"][0]["status"] = "closed"
    board["qualifications"][1]["raised_in"] = 4
    errors = levels(validate_record(board), "error")
    assert any("needs closed_in" in e for e in errors)
    assert any("later cycle" in e for e in errors)


def test_unknown_citation(board: dict[str, Any], manifest: dict[str, Any]) -> None:
    board["elements"][5]["cites"] = ["nosuch#t=00:01:00"]
    errors = levels(validate_record(board, source_ids(manifest)), "error")
    assert any("nosuch" in e for e in errors)


def test_move_rules(board: dict[str, Any]) -> None:
    model = next(e for e in board["elements"] if e["id"] == "m-coop")
    model["move"]["from"] = ["m-coop", "absent"]
    errors = levels(validate_record(board), "error")
    assert any("cannot start from its result" in e for e in errors)
    assert any("absent" in e for e in errors)


def test_missing_position_and_home_board_warnings(board: dict[str, Any]) -> None:
    model = next(e for e in board["elements"] if e["id"] == "m-coop")
    del model["seen_from"]
    model["board"] = "od"
    warnings = levels(validate_record(board), "warning")
    assert any("no position" in w for w in warnings)
    assert any("usually lies on board 'oo'" in w for w in warnings)


def test_method_hints(board: dict[str, Any]) -> None:
    board["elements"] = [
        e
        for e in board["elements"]
        if not (e["kind"] == "function" or e.get("half") == "small")
    ]
    board["elements"] = [e for e in board["elements"] if e["kind"] != "entry"]
    board["transitions"] = []
    hints = levels(validate_record(board), "hint")
    assert any("no functional plan" in h for h in hints)
    assert any("small situation not laid out" in h for h in hints)
    assert any("no entry" in h for h in hints)
    assert any("candidates awaiting" in h for h in hints)


def test_verified_needs_checker(board: dict[str, Any]) -> None:
    board["status"] = "verified"
    assert any("checked_by" in e for e in levels(validate_record(board), "error"))


def test_manifest_checks(manifest: dict[str, Any]) -> None:
    manifest["sources"].append(dict(manifest["sources"][0]))
    del manifest["sources"][1]["clean_room"]
    manifest["sources"][0]["personal_data"] = True
    findings = validate_record(manifest)
    assert any("duplicate" in e for e in levels(findings, "error"))
    assert any("clean_room not decided" in w for w in levels(findings, "warning"))
    assert any("personal data" in h for h in levels(findings, "hint"))


def test_date_format_and_unquoted_dates(board: dict[str, Any]) -> None:
    board["date"] = "2026-13-45"
    assert any("date" in e for e in levels(validate_record(board), "error"))


def test_unquoted_yaml_date_is_read_as_text(tmp_path: Any) -> None:
    from smd_engine.records import load_record

    path = tmp_path / "x.board.yaml"
    path.write_text(
        "record: board_set\nschema_version: '0.3'\nid: x\ntitle: t\ncycle: 1\n"
        "status: draft\ndate: 2026-10-25\n"
        "elements: [{id: a, board: od, kind: position, label: p}]\n"
    )
    data = load_record(path)
    assert data["date"] == "2026-10-25"
    assert levels(validate_record(data), "error") == []


def test_closed_in_without_closed_status(board: dict[str, Any]) -> None:
    board["qualifications"][0]["closed_in"] = 1
    assert any("not closed" in w for w in levels(validate_record(board), "warning"))


def test_functions_without_performer_hint(board2: dict[str, Any]) -> None:
    fn = next(e for e in board2["elements"] if e["id"] == "fn-dough")
    del fn["performed_by"]
    hints = levels(validate_record(board2), "hint")
    assert any("1 of 2 functions" in h for h in hints)
    assert levels(validate_record(board2), "warning") == []


def test_performed_by_rules(board2: dict[str, Any]) -> None:
    fn = next(e for e in board2["elements"] if e["id"] == "fn-dough")
    fn["performed_by"] = "f-new"
    board2["elements"][1]["performed_by"] = "p-owner"
    board2["theses"][0]["raises"] = ["K9"]
    errors = levels(validate_record(board2), "error")
    assert any("performed_by must be a position" in e for e in errors)
    assert any("'performed_by' is only for functions" in e for e in errors)
    assert any("raises 'K9'" in e for e in errors)


def test_vision_and_decision_log(
    board: dict[str, Any], manifest: dict[str, Any]
) -> None:
    board["elements"].append(
        {
            "id": "vis-1",
            "board": "s",
            "half": "big",
            "kind": "vision",
            "label": "an outside author's orienting picture",
            "seen_from": "p-organiser",
        }
    )
    assert [f for f in validate_record(board) if f.level != "hint"] == []
    manifest["sources"].append(
        {
            "id": "dec1",
            "title": "owner's written decisions",
            "kind": "decision_log",
            "origin": "team",
            "file": "decisions.md",
            "clean_room": "deny",
        }
    )
    assert [f for f in validate_record(manifest) if f.level == "error"] == []


def test_fillers_only_on_roles_and_detail_rows_match(board: dict[str, Any]) -> None:
    place = next(e for e in board["elements"] if e["kind"] == "place_for_others")
    frame = next(e for e in board["elements"] if e["kind"] == "frame")
    place["fillers"] = ["state", "region"]
    place["detail"] = {"columns": ["level", "stakeholder"], "rows": [["1", "owner"]]}
    assert levels(validate_record(board), "error") == []
    frame["fillers"] = ["bank"]
    place["detail"]["rows"].append(["2"])
    errors = levels(validate_record(board), "error")
    assert any(frame["id"] in e and "only for roles" in e for e in errors)
    assert any("detail row 2 has 1 cells, not 2" in e for e in errors)


def test_registry_runs_every_check_once(
    board: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def counting(check: Check) -> Check:
        def run(ctx: Ctx) -> list[Finding]:
            calls.append(check.__name__)
            return check(ctx)

        return run

    registry = list(validate.REGISTRY)
    expected = validate_record(board)
    monkeypatch.setattr(validate, "REGISTRY", [counting(c) for c in registry])
    assert validate_record(board) == expected
    assert sorted(calls) == sorted(c.__name__ for c in registry)


def test_old_schema_version_is_one_error(board: dict[str, Any]) -> None:
    board["schema_version"] = "0.2"
    board["elements"][0]["board"] = "xx"
    assert [str(f) for f in validate_record(board)] == [
        "error: schema_version: schema 0.2: run smd migrate"
    ]


TAXONOMIES = {"tier": {"t1", "t2"}, "region": {"south"}}


def test_tags_are_checked_against_taxonomies(board2: dict[str, Any]) -> None:
    owner = next(e for e in board2["elements"] if e["id"] == "p-owner")
    owner["tags"] = {"tier": ["t1"], "region": ["south"]}
    board2["theses"][0]["tags"] = {"tier": ["t9"]}
    board2["hypotheses"][0]["tags"] = {"sector": ["food"]}
    board2["ontology"][0]["tags"] = {"tier": ["t2"]}
    assert any(
        "no taxonomy file" in w for w in levels(validate_record(board2), "warning")
    )
    errors = levels(validate_record(board2, taxonomies=TAXONOMIES), "error")
    assert errors == [
        "T1: tags: 't9' is not a value of taxonomy 'tier'",
        "H1: tags: unknown taxonomy 'sector'",
    ]


def test_detail_column_bound_to_a_taxonomy(board: dict[str, Any]) -> None:
    place = next(e for e in board["elements"] if e["kind"] == "place_for_others")
    place["detail"] = {
        "columns": ["tier", "stakeholder"],
        "rows": [["t1; t2", "owner"], ["t3", "bank"], ["", "mill"]],
        "keys": {"tier": "tier"},
    }
    errors = levels(validate_record(board, taxonomies=TAXONOMIES), "error")
    pid = place["id"]
    assert errors == [f"{pid}: detail 'tier': 't3' is not a value of taxonomy 'tier'"]
    place["detail"]["keys"] = {"level": "tier"}
    errors = levels(validate_record(board, taxonomies=TAXONOMIES), "error")
    assert errors == [f"{pid}: detail key 'level' is not a column"]


def test_route_and_scheme_fields(board2: dict[str, Any]) -> None:
    gap = next(e for e in board2["elements"] if e["kind"] == "gap")
    gap.update(route="triz", scheme="gp-pp-activity")
    problem = next(t for t in board2["theses"] if t["kind"] == "problem")
    problem.update(route="smd", scheme="gp-pp-activity")
    assert levels(validate_record(board2), "error") == []
    board2["elements"][1]["scheme"] = "gp-pp-activity"
    board2["theses"][0]["scheme"] = "gp-pp-activity"
    errors = levels(validate_record(board2), "error")
    assert errors == [
        f"{board2['elements'][1]['id']}: 'scheme' is only for gaps",
        "T1: 'scheme' is only for problem theses",
    ]
    gap["route"] = "other"
    assert levels(validate_record(board2), "error")


def test_run_stamp_v2_fields(board: dict[str, Any]) -> None:
    sha = "b" * 64
    board["run"] = {
        "procedure": "theses-to-board",
        "pack_sha256": sha,
        "inputs": {"s1": sha, "s2": sha},
        "temperature": 0,
        "sample": 3,
    }
    assert levels(validate_record(board), "error") == []
    for field, bad in (
        ("pack_sha256", "abc"),
        ("inputs", {"s1": 5}),
        ("inputs", ["s1"]),
        ("temperature", "warm"),
        ("sample", 1.5),
        ("sample", "2"),
    ):
        wrong = {**board, "run": {**board["run"], field: bad}}
        assert levels(validate_record(wrong), "error"), (field, bad)
