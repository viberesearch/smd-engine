"""The typed standard of hypotheses and the decision rule (method review of
31.10, gates М1 В and Ф В): schema, Wilson interval, verdict, hints."""

from __future__ import annotations

from typing import Any

import pytest

from smd_engine.render.html import render_html
from smd_engine.render.markdown import render_markdown
from smd_engine.render.graph import graph_model
from smd_engine.status import render_status
from smd_engine.validate import validate_record
from smd_engine.verdict import _sides, propose, wilson

RULE = {"metric": "доля 55+", "op": "<", "threshold": 0.2, "n_min": 30}
BASED = RULE | {"basis": "b"}


def found(data: dict[str, Any], level: str, ref: str) -> list[str]:
    return [
        f.message for f in validate_record(data) if f.level == level and f.ref == ref
    ]


def h2(board2: dict[str, Any]) -> dict[str, Any]:
    h: dict[str, Any] = board2["hypotheses"][1]
    assert h["id"] == "H2" and h["status"] == "testing" and h["raised_in"] == 2
    return h


# Schema


def test_schema_accepts_type_rule_and_observed(board2: dict[str, Any]) -> None:
    h2(board2).update(
        type="estimate",
        rule=RULE | {"basis": "the entry segment changes below 20%"},
        observed={"k": 12, "n": 40, "artefact": "s4"},
    )
    assert not [f for f in validate_record(board2) if f.level == "error"]


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "belief"},
        {"rule": {"metric": "share", "op": "<"}},
        {"rule": RULE | {"op": "!="}},
        {"rule": RULE | {"op": "=="}},
        {"rule": RULE | {"n_min": 0}},
        {"rule": RULE | {"basis": ""}},
        {"rule": RULE | {"why": "x"}},
        {"observed": {"k": 1, "n": 0, "artefact": "s4"}},
        {"observed": {"k": -1, "n": 3, "artefact": "s4"}},
        {"observed": {"k": 1, "n": 3}},
        {"observed": {"k": 1.5, "n": 3, "artefact": "s4"}},
    ],
)
def test_schema_refuses(board2: dict[str, Any], fields: dict[str, Any]) -> None:
    h2(board2).update(fields)
    assert any(
        f.level == "error" and f.ref.startswith("hypotheses/1")
        for f in validate_record(board2)
    )


def test_k_above_n_is_an_error(board2: dict[str, Any]) -> None:
    h2(board2).update(rule=RULE, observed={"k": 5, "n": 4, "artefact": "s4"})
    assert found(board2, "error", "H2") == ["observed k=5 exceeds n=4"]


def test_observed_artefact_is_a_field_artefact(board2: dict[str, Any]) -> None:
    kinds = {"s4": "field_artefact", "s2": "team_doc"}
    h2(board2)["observed"] = {"k": 1, "n": 4, "artefact": "s2#p=3"}

    def warned(kinds: dict[str, str] | None) -> list[str]:
        findings = validate_record(board2, set(kinds or {}) or None, source_kinds=kinds)
        return [f.message for f in findings if f.level == "warning" and f.ref == "H2"]

    assert warned(kinds) == [
        "observed counts 's2', a source of kind 'team_doc', not field_artefact"
    ]
    assert warned(None) == []
    h2(board2)["observed"]["artefact"] = "s4"
    assert warned(kinds) == []


def test_observed_artefact_must_be_a_source(board2: dict[str, Any]) -> None:
    h2(board2)["observed"] = {"k": 1, "n": 4, "artefact": "nowhere"}
    findings = validate_record(board2, source_ids={"s4"})
    assert "cites unknown source 'nowhere'" in [f.message for f in findings]


# Wilson interval


@pytest.mark.parametrize(
    ("k", "n", "low", "high"),
    [
        # Newcombe (1998), Wilson score method; recomputed by hand from the formula
        (81, 263, 0.2553, 0.3662),
        (15, 148, 0.0624, 0.1605),
        (0, 20, 0.0, 0.1611),
        (1, 29, 0.0061, 0.1718),
        (10, 10, 0.7225, 1.0),
    ],
)
def test_wilson_against_hand_values(k: int, n: int, low: float, high: float) -> None:
    got = wilson(k, n)
    assert got == pytest.approx((low, high), abs=5e-5)


def test_wilson_refuses_impossible_counts() -> None:
    for k, n in ((3, 2), (-1, 2), (0, 0)):
        with pytest.raises(ValueError):
            wilson(k, n)


# Verdict


@pytest.mark.parametrize(
    ("rule", "k", "n", "outcome"),
    [
        (RULE, 3, 10, "too_few"),  # n below n_min
        (RULE, 2, 100, "refuted"),  # 0.006-0.07, all below 0.2
        (RULE, 40, 100, "confirmed"),  # 0.31-0.50, all at or above 0.2
        (RULE, 12, 40, "inconclusive"),  # 0.18-0.45 straddles 0.2
        ({"metric": "s", "op": ">", "threshold": 0.5}, 9, 10, "refuted"),
        ({"metric": "s", "op": ">=", "threshold": 0.5}, 1, 10, "confirmed"),
        ({"metric": "s", "op": "<=", "threshold": 0.5}, 1, 10, "refuted"),
    ],
)
def test_verdict_branches(rule: dict[str, Any], k: int, n: int, outcome: str) -> None:
    v = propose(rule, {"k": k, "n": n, "artefact": "s4"})
    assert v is not None and v.outcome == outcome


@pytest.mark.parametrize(
    ("op", "low", "high", "sides"),
    [
        # (the whole interval refutes, the whole interval holds); t = 0.2
        ("<", 0.2, 0.4, (False, True)),  # low == t: no share below t
        ("<", 0.1, 0.2, (False, False)),  # high == t: t itself is not below t
        ("<=", 0.1, 0.2, (True, False)),  # high == t: all at or below t
        ("<=", 0.2, 0.4, (False, False)),  # low == t: t itself refutes
        (">", 0.2, 0.4, (False, False)),
        (">", 0.1, 0.2, (False, True)),
        (">=", 0.2, 0.4, (True, False)),
        (">=", 0.1, 0.2, (False, False)),
    ],
)
def test_exact_boundaries(
    op: str, low: float, high: float, sides: tuple[bool, bool]
) -> None:
    assert _sides(op, 0.2, low, high) == sides


@pytest.mark.parametrize("threshold", [0, 1, 0.0, 1.0, 20, -0.1])
def test_no_verdict_when_the_threshold_is_not_a_share(threshold: float) -> None:
    rule = {"metric": "cost", "op": "<", "threshold": threshold}
    assert propose(rule, {"k": 1, "n": 2, "artefact": "s4"}) is None


def test_verdict_hint_and_contradiction(board2: dict[str, Any]) -> None:
    h = h2(board2)
    h.update(rule=BASED, observed={"k": 12, "n": 40, "artefact": "s4"})
    assert found(board2, "hint", "H2") == [
        "proposed by the rule (доля 55+ < 0.2, n >= 30): 12/40 = 0.30, "
        "Wilson 95% 0.18-0.45: inconclusive, stays testing; "
        "the group signs accept_result"
    ]
    assert not found(board2, "warning", "H2")
    # confirmed while the whole interval is on the refuting side
    h1 = board2["hypotheses"][0]
    h1.update(rule=RULE, observed={"k": 2, "n": 100, "artefact": "s4"})
    assert found(board2, "warning", "H1") == [
        "recorded confirmed, but by the rule (доля 55+ < 0.2, n >= 30) "
        "2/100 = 0.02, Wilson 95% 0.01-0.07 proposes refuted"
    ]
    h1["observed"] = {"k": 40, "n": 100, "artefact": "s4"}
    assert not found(board2, "warning", "H1")


def test_verdict_hint_without_a_share_or_rule(board2: dict[str, Any]) -> None:
    h = h2(board2)
    h["observed"] = {"k": 1, "n": 4, "artefact": "s4"}
    assert found(board2, "hint", "H2") == ["observed, but no rule to read it by"]
    h["rule"] = {"metric": "cost", "op": ">", "threshold": 20, "basis": "b"}
    assert found(board2, "hint", "H2") == [
        "no proposal: the threshold 20 is not a share (strictly between 0 and 1)"
    ]
    h["rule"] = RULE | {"threshold": 0, "basis": "b"}
    assert found(board2, "hint", "H2")[0].startswith("no proposal: the threshold 0 ")


def test_verdict_only_for_untested_or_testing(board2: dict[str, Any]) -> None:
    h1 = board2["hypotheses"][0]
    assert h1["status"] == "confirmed"
    h1.update(rule=BASED, observed={"k": 12, "n": 40, "artefact": "s4"})
    assert found(board2, "hint", "H1") == []
    assert "Verdicts" not in render_status(board2, "en")
    h1["status"] = "testing"
    del h1["resolved_in"]
    assert found(board2, "hint", "H1")[0].startswith("proposed by the rule")
    assert "- H1 (testing; " in render_status(board2, "en")


# Hints


def test_type_hint_only_in_a_cycle_with_typed_hypotheses(
    board2: dict[str, Any],
) -> None:
    def typed_hints() -> list[str]:
        return [
            f.ref
            for f in validate_record(board2)
            if f.level == "hint" and f.message.startswith("no type")
        ]

    assert typed_hints() == []  # no typed hypothesis: old records are left alone
    board2["hypotheses"].append(
        {"id": "H3", "assumes": "x", "status": "untested", "raised_in": 2}
        | {"type": "design"}
    )
    # H2 is of the same cycle; H1 (cycle 1) is not nagged
    assert typed_hints() == ["H2"]
    h2(board2)["type"] = "product"
    assert typed_hints() == []


def test_claim_without_rule(board2: dict[str, Any]) -> None:
    h = h2(board2)
    h["type"] = "claim"
    assert not [m for m in found(board2, "hint", "H2") if "decision rule" in m]
    del h["revise_if"]
    assert found(board2, "hint", "H2") == [
        "a claim with no decision rule: write `rule` (or at least `revise_if`) "
        "before the field"
    ]  # and not also revise-if
    h["rule"] = RULE | {"basis": "b"}
    assert found(board2, "hint", "H2") == []


def test_revise_if_hint_takes_a_rule_and_skips_untested_types(
    board2: dict[str, Any],
) -> None:
    h = h2(board2)
    del h["revise_if"]
    message = "no result is named that would make us revise the assumption"
    assert found(board2, "hint", "H2") == [message]
    h["rule"] = RULE | {"basis": "b"}
    assert found(board2, "hint", "H2") == []
    del h["rule"]
    h["type"] = "probe"
    assert message not in found(board2, "hint", "H2")


def test_rule_without_basis(board2: dict[str, Any]) -> None:
    h = h2(board2)
    h["rule"] = RULE
    assert found(board2, "hint", "H2") == [
        "the threshold 0.2 has no basis: say what decision it changes or where "
        "it comes from"
    ]
    h["rule"] = RULE | {"basis": "the entry segment changes below 20%"}
    assert found(board2, "hint", "H2") == []


def test_estimate_without_n_min(board2: dict[str, Any]) -> None:
    h = h2(board2)
    h.update(type="estimate", rule={k: v for k, v in RULE.items() if k != "n_min"})
    h["rule"]["basis"] = "b"
    message = "an estimate with a rule but no n_min: how many cases is it read on?"
    assert found(board2, "hint", "H2") == [message]
    h["type"] = "claim"
    assert found(board2, "hint", "H2") == []
    h.update(type="estimate", rule=RULE | {"basis": "b"})
    assert found(board2, "hint", "H2") == []


@pytest.mark.parametrize(
    ("type_", "status", "fires"),
    [
        ("probe", "confirmed", True),
        ("probe", "refuted", True),
        ("probe", "testing", False),
        ("core", "testing", True),
        ("design", "confirmed", True),
        ("design", "untested", False),
        ("claim", "confirmed", False),
    ],
)
def test_type_status(
    board2: dict[str, Any], type_: str, status: str, fires: bool
) -> None:
    h1 = board2["hypotheses"][0]  # has a result, an artefact and a sign-off
    h1.update(type=type_, status=status, rule=RULE | {"basis": "b"})
    if status not in ("confirmed", "refuted"):
        del h1["resolved_in"]
    hints = [m for m in found(board2, "hint", "H1") if f"a {type_} is" in m]
    assert bool(hints) is fires


def test_hints_name_the_procedure(board2: dict[str, Any]) -> None:
    h2(board2).update(
        type="estimate", rule={"metric": "s", "op": "<", "threshold": 0.2}
    )
    pointed = {
        f.procedure
        for f in validate_record(board2)
        if f.ref == "H2" and f.level == "hint"
    }
    assert pointed == {"procedures/field-result.md §0.2"}


# Renderers and smd status


def test_renderers_and_status_show_type_rule_and_verdict(
    board2: dict[str, Any],
) -> None:
    h2(board2).update(
        type="estimate",
        rule=RULE | {"basis": "решение о сегменте"},
        observed={"k": 12, "n": 40, "artefact": "s4"},
    )
    md = render_markdown(board2, "ru")
    assert "тип гипотезы: оценка" in md
    assert "правило решения: доля 55+ < 0.2, n >= 30 (основание порога: " in md
    assert "наблюдено: 12/40 (s4)" in md
    assert "type: estimate" in render_html(board2, "en")
    nodes = {n["id"]: n for n in graph_model(board2, "en")["nodes"]}
    assert nodes["H2"]["extra"]["type"] == "estimate"
    status = render_status(board2, "en")
    assert (
        "## Verdicts by the decision rule (a proposal; the group signs) (1)" in status
    )
    assert (
        "- H2 (testing; доля 55+ < 0.2, n >= 30 (threshold basis: решение о "
        "сегменте)): 12/40 = 0.30, Wilson 95% 0.18-0.45: inconclusive, stays testing"
    ) in status
    assert "не решено, остаётся в проверке" in render_status(board2, "ru")
