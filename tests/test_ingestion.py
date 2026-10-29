from __future__ import annotations

from typing import Any

from smd_engine.render.markdown import render_markdown
from smd_engine.sources import source_ids
from smd_engine.validate import validate_record


def levels(findings: list[Any], level: str) -> list[str]:
    return [f"{f.ref}: {f.message}" for f in findings if f.level == level]


def thesis(board: dict[str, Any], tid: str) -> dict[str, Any]:
    return next(t for t in board["theses"] if t["id"] == tid)


def test_cycle_two_example_is_clean(
    board2: dict[str, Any], manifest: dict[str, Any]
) -> None:
    findings = validate_record(board2, source_ids(manifest))
    assert levels(findings, "error") == []
    assert levels(findings, "warning") == []


def test_thesis_needs_belt_and_kind(board2: dict[str, Any]) -> None:
    del thesis(board2, "T1")["belt"]
    errors = levels(validate_record(board2), "error")
    assert any("'belt' is a required property" in e for e in errors)


def test_reflected_from(board2: dict[str, Any]) -> None:
    board2["reflected_from"] = "f-new"
    assert any(
        "must be a position" in e for e in levels(validate_record(board2), "error")
    )
    del board2["reflected_from"]
    warnings = levels(validate_record(board2), "warning")
    assert any("reflexive position" in w for w in warnings)


def test_status_must_fit_voice(board2: dict[str, Any]) -> None:
    thesis(board2, "T3")["status"] = "voiced"
    thesis(board2, "T1")["status"] = "ai_variant"
    errors = levels(validate_record(board2), "error")
    assert any("T3: status 'voiced' does not fit voice 'ai'" in e for e in errors)
    assert any(
        "T1: status 'ai_variant' does not fit voice 'group'" in e for e in errors
    )


def test_thesis_references(board2: dict[str, Any]) -> None:
    thesis(board2, "T1")["feeds"] = ["nowhere"]
    thesis(board2, "T3")["move"]["from"] = ["T3", "ghost"]
    board2["theses"].append(dict(thesis(board2, "T5")))
    errors = levels(validate_record(board2), "error")
    assert any("feeds 'nowhere'" in e for e in errors)
    assert any("cannot start from its result" in e for e in errors)
    assert any("'ghost' is not an element or thesis" in e for e in errors)
    assert any("duplicate thesis id" in e for e in errors)


def test_thesis_without_source_address(board2: dict[str, Any]) -> None:
    del thesis(board2, "T1")["cites"]
    warnings = levels(validate_record(board2), "warning")
    assert any("T1: thesis has no source address" in w for w in warnings)


def test_accepted_moves_need_a_human(board2: dict[str, Any]) -> None:
    board2["signoffs"] = [s for s in board2["signoffs"] if s["target"] != "m-coop"]
    del thesis(board2, "T2")["cites"]
    findings = validate_record(board2)
    assert any(
        "m-coop: a move from an AI voice" in e for e in levels(findings, "error")
    )
    assert any(
        "T2: accepted move with neither" in w for w in levels(findings, "warning")
    )


def test_state_changes_without_signoff(board2: dict[str, Any]) -> None:
    board2["signoffs"] = []
    board2["status"] = "verified"
    board2["checked_by"] = "methodologist"
    warnings = levels(validate_record(board2), "warning")
    assert any("K2: closed without a human sign-off" in w for w in warnings)
    assert any("T4: refined without a group sign-off" in w for w in warnings)
    assert any("verified without a sign-off" in w for w in warnings)


def test_signoff_must_be_human_and_well_aimed(board2: dict[str, Any]) -> None:
    board2["signoffs"] = [
        {"function": "close_k", "target": "K2", "by": "ИИ"},
        {"function": "accept_thesis", "target": "K1", "by": "group"},
        {"function": "accept_move", "target": "f-new", "by": "group"},
        {"function": "close_k", "by": "group"},
        {"function": "verify_record", "target": "K1", "by": "group"},
    ]
    errors = levels(validate_record(board2), "error")
    assert any("human point, not AI" in e for e in errors)
    assert any("'K1' is not a thesis" in e for e in errors)
    assert any("'f-new' carries no move" in e for e in errors)
    assert any("needs a target" in e for e in errors)
    assert any("verify_record takes no target" in e for e in errors)


def test_signoff_that_changes_nothing(board2: dict[str, Any]) -> None:
    board2["signoffs"].append({"function": "close_k", "target": "K1", "by": "group"})
    board2["signoffs"].append(
        {"function": "accept_move", "target": "T3", "by": "group"}
    )
    warnings = levels(validate_record(board2), "warning")
    assert any(
        "(close_k): changes nothing: the target is 'open'" in w for w in warnings
    )
    assert any("is 'candidate', not 'accepted'" in w for w in warnings)


def test_ingestion_hints(board2: dict[str, Any]) -> None:
    hints = levels(validate_record(board2), "hint")
    assert "theses: AI variants awaiting the group: T3" in hints
    assert "moves: candidates awaiting a decision: T3" in hints


def test_markdown_lists_theses_with_sessionflow_labels(board2: dict[str, Any]) -> None:
    md = render_markdown(board2, "ru")
    assert "**T3** [Вариант формулировки от ИИ]" in md
    assert "## Подписи" in md and "закрыть квалификацию `K2`: group" in md


def hyp(board: dict[str, Any], hid: str) -> dict[str, Any]:
    return next(h for h in board["hypotheses"] if h["id"] == hid)


def test_hypothesis_result_rests_on_a_field_artefact(board2: dict[str, Any]) -> None:
    h1 = hyp(board2, "H1")
    del h1["artefacts"], h1["result"], h1["resolved_in"]
    hyp(board2, "H2")["targets"] = ["ghost"]
    hyp(board2, "H2")["qualifications"] = ["K9"]
    errors = levels(validate_record(board2), "error")
    assert any("H1: a result needs the field artefact" in e for e in errors)
    assert any("H1: a result needs its text" in e for e in errors)
    assert any("H1: a result needs resolved_in" in e for e in errors)
    assert any("H2: target 'ghost'" in e for e in errors)
    assert any("H2: 'K9' is not a qualification" in e for e in errors)


def test_hypothesis_warnings(board2: dict[str, Any]) -> None:
    del hyp(board2, "H2")["action"]
    board2["signoffs"] = [s for s in board2["signoffs"] if s["target"] != "H1"]
    board2["signoffs"].append({"function": "accept_result", "target": "H2", "by": "x"})
    warnings = levels(validate_record(board2), "warning")
    assert any("H2: testing, but no action" in w for w in warnings)
    assert any("H1: result without a human sign-off" in w for w in warnings)
    assert any("not 'confirmed' or 'refuted'" in w for w in warnings)


def test_scheme_blocks(board2: dict[str, Any]) -> None:
    board2["elements"][1]["of"] = "means"
    gap = next(e for e in board2["elements"] if e["id"] == "gap-risk")
    del gap["of"], thesis(board2, "T3")["of"]
    findings = validate_record(board2)
    assert any("'of' is only for gaps" in e for e in levels(findings, "error"))
    hints = levels(findings, "hint")
    assert any("gap-risk: gap names no scheme block" in h for h in hints)
    assert any("T3: a problem is tied to a block" in h for h in hints)


def test_cycle_hints(board2: dict[str, Any], board: dict[str, Any]) -> None:
    del board2["state"]["difficulty"]
    hints = levels(validate_record(board2, previous=board), "hint")
    assert any("what failed in the previous one" in h for h in hints)
    assert not any("without a new scheme" in h for h in hints)
    same = dict(board2, elements=board["elements"])
    hints = levels(validate_record(same, previous=board), "hint")
    assert any("reflection without a new scheme" in h for h in hints)


def test_belt_degeneration_hints(board2: dict[str, Any]) -> None:
    for t in board2["theses"]:
        t["belt"] = "mk"
    assert any("play with words" in h for h in levels(validate_record(board2), "hint"))
    for t in board2["theses"]:
        t["belt"] = "m"
    assert any("cut off" in h for h in levels(validate_record(board2), "hint"))


def test_html_lists_theses_hypotheses_signoffs(board2: dict[str, Any]) -> None:
    from smd_engine.render.html import render_html

    html = render_html(board2, "ru")
    for title in ("Тезисы", "Гипотезы", "Подписи"):
        assert f"<h2>{title}</h2>" in html
    assert "Уточнено группой после записи" in html and "подтверждено" in html


def test_ontology_rules(board2: dict[str, Any]) -> None:
    o1 = board2["ontology"][0]
    o1["valid_for"].append("f-new")
    o1["cooperation"] = "f-new"
    o1["test"] = "H9"
    o1["subjects"].append({"position": "p-reflect", "subject": "x"})
    findings = validate_record(board2)
    errors = levels(findings, "error")
    assert any("valid_for 'f-new' is not a position" in e for e in errors)
    assert any("'f-new' is not a cooperation element" in e for e in errors)
    assert any("test 'H9' is not a hypothesis" in e for e in errors)
    assert any("outside valid_for" in w for w in levels(findings, "warning"))


def test_ontology_hints(board2: dict[str, Any]) -> None:
    o1 = board2["ontology"][0]
    del o1["test"], o1["cooperation"]
    hints = levels(validate_record(board2), "hint")
    assert any("realizability, not truth" in h for h in hints)
    assert any("construction of their cooperation" in h for h in hints)


def test_subject_object_talk_on_object_board(board2: dict[str, Any]) -> None:
    fn = next(e for e in board2["elements"] if e["id"] == "fn-logistics")
    fn["label"] = "Мы должны развозить тесто ночью"
    board2["relations"].append({"from": "f-new", "to": "f-old", "kind": "represents"})
    warnings = levels(validate_record(board2), "warning")
    assert any("fn-logistics: subject-object talk" in w for w in warnings)
    assert any("represents goes from a position" in w for w in warnings)


def test_reject_move_and_ai_drafts(board2: dict[str, Any]) -> None:
    board2["signoffs"].append(
        {"function": "reject_move", "target": "T3", "by": "group"}
    )
    board2["qualifications"][0]["voice"] = "AI"
    board2["hypotheses"][1]["voice"] = "ai"
    findings = validate_record(board2)
    assert any(
        "is 'candidate', not 'rejected'" in w for w in levels(findings, "warning")
    )
    assert "ai-drafts: K and H drafted by AI, for a human to keep or drop: K1, H2" in (
        levels(findings, "hint")
    )
    thesis(board2, "T3")["move"]["status"] = "rejected"
    assert not any("rejected" in w for w in levels(validate_record(board2), "warning"))


def test_thesis_about_and_ontology_aspects(board2: dict[str, Any]) -> None:
    thesis(board2, "T1")["about"] = ["f-new", "ghost"]
    board2["ontology"][0]["aspects"] = {
        "activity": "dough for members",
        "carrier": "the plant",
    }
    errors = levels(validate_record(board2), "error")
    assert errors == ["T1: about 'ghost', not an element"]
