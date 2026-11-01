"""Engine robustness rules R1-R6 (docs/method/robustness-rules.md): domain and
sample, fragility and unknown cases, bounded numeric outputs, rivals, the
surprise log and the red-line hint on every profile."""

from __future__ import annotations

import copy
import math
from typing import Any

import pytest

from smd_engine.agree import alpha_nominal
from smd_engine.render.sessionflow import render_sessionflow
from smd_engine.status import render_status
from smd_engine.validate import validate_record
from smd_engine.verdict import detail_text, fragility, propose, wilson

RULE = {"metric": "доля 55+", "op": "<", "threshold": 0.30, "basis": "b"}
DOMAIN = {"revenue_bn": [0.5, 2.5]}


def found(data: dict[str, Any], level: str, ref: str) -> list[str]:
    return [
        f.message for f in validate_record(data) if f.level == level and f.ref == ref
    ]


def h2(board2: dict[str, Any]) -> dict[str, Any]:
    h: dict[str, Any] = board2["hypotheses"][1]
    return h


# R4: fragility and unknown cases


def test_the_g1_case_flips_in_four_and_has_manski_bounds() -> None:
    obs = {"k": 122, "n": 340, "unknown": 91, "artefact": "b1"}
    v = propose(RULE, obs)
    assert v is not None and v.outcome == "confirmed" and v.flips == 4
    assert (round(v.low, 4), round(v.high, 4)) == (0.3097, 0.4111)
    assert round(wilson(118, 340)[0], 4) == 0.2984  # 4 recodings: inconclusive
    none, every = v.none_counted, v.all_counted
    assert none is not None and every is not None
    assert (none.k, none.n, none.outcome) == (122, 431, "inconclusive")
    assert (round(none.share, 3), round(none.low, 4), round(none.high, 4)) == (
        0.283,
        0.2426,
        0.3274,
    )
    assert (every.k, every.n, every.outcome) == (213, 431, "confirmed")
    assert "recoding 4 of 340" in detail_text(v)
    assert "122/431 = 0.28, Wilson 95% 0.24-0.33, inconclusive" in detail_text(v)
    assert "перекодировка 4 из 340" in detail_text(v, "ru")


def test_fragility_is_none_when_no_recoding_flips_or_n_is_too_small() -> None:
    assert fragility(RULE, 0, 1) is None  # k = n = 1 cannot go past 0 or 1
    assert fragility(RULE | {"n_min": 50}, 12, 40) is None  # too_few stays so
    assert fragility(RULE, 12, 40) == 6  # 12/40 straddles 0.30; 6/40 refutes


def test_unknown_cases_show_in_status_and_sessionflow(board2: dict[str, Any]) -> None:
    h = h2(board2)
    h.update(rule=RULE, observed={"k": 122, "n": 340, "unknown": 91, "artefact": "s4"})
    assert "122/431 = 0.28" in render_status(board2, "en")
    assert "у 91 исход неизвестен" in render_status(board2, "ru")
    assert "перекодировка 4 из 340" in render_sessionflow(board2)
    assert "if none of them is in k" in found(board2, "hint", "H2")[0]


# R1: domain and sample


def test_sample_outside_the_domain_has_no_reading() -> None:
    rule = RULE | {"domain": DOMAIN}
    obs = {"k": 12, "n": 40, "artefact": "s4", "sample": {"revenue_bn": [2.0, 3.1]}}
    v = propose(rule, obs)
    assert v is not None and v.outcome == "outside_domain" and v.flips is None
    assert "sample revenue_bn 2-3.1 is outside the domain 0.5-2.5" in detail_text(v)


def test_sample_inside_the_domain_says_which_part_it_covers() -> None:
    rule = RULE | {"domain": DOMAIN}
    obs = {"k": 12, "n": 40, "artefact": "s4", "sample": {"revenue_bn": [1.0, 2.0]}}
    v = propose(rule, obs)
    assert v is not None and v.outcome == "inconclusive"
    assert "the sample covers revenue_bn 1-2 of the domain 0.5-2.5" in detail_text(v)
    whole = propose(rule, obs | {"sample": {"revenue_bn": [0.5, 2.5]}})
    assert whole is not None and "covers" not in detail_text(whole)


def test_domain_checks_and_hint(board2: dict[str, Any]) -> None:
    h = h2(board2)
    h.update(
        rule=RULE | {"domain": DOMAIN}, observed={"k": 12, "n": 40, "artefact": "s4"}
    )
    assert any(
        "give the ranges the field covered (revenue_bn)" in m
        for m in found(board2, "hint", "H2")
    )
    h["observed"]["sample"] = {"revenue_bn": [3.0, 4.0], "age": [1, 2]}
    assert found(board2, "warning", "H2") == [
        "sample names age, which the rule's domain does not"
    ]
    assert any(
        "outside the rule's domain, no proposal" in m
        for m in found(board2, "hint", "H2")
    )
    h["status"] = "confirmed"
    assert any("leaves the rule's domain" in m for m in found(board2, "warning", "H2"))
    h["observed"]["sample"] = {"revenue_bn": [3.0, 1.0]}
    assert "sample 'revenue_bn': min 3 is above max 1" in found(board2, "error", "H2")


def test_domain_sample_names_what_the_sample_omits(board2: dict[str, Any]) -> None:
    h = h2(board2)
    domain = {"revenue_bn": [0.5, 2.5], "age": [20, 60]}
    h.update(rule=RULE | {"domain": domain})
    h["observed"] = {"k": 12, "n": 40, "artefact": "s4", "sample": {"age": [25, 50]}}
    [hint] = [m for m in found(board2, "hint", "H2") if "the sample omits" in m]
    assert "omits revenue_bn:" in hint and "age" not in hint
    h["observed"]["sample"]["revenue_bn"] = [1.0, 2.0]
    assert not [m for m in found(board2, "hint", "H2") if "sample" in m.split(":")[0]]


# R3: bounded numeric outputs


@pytest.mark.parametrize(("k", "n"), [(0, 1), (1, 1), (0, 5), (5, 5), (0, 10**6)])
def test_wilson_stays_finite_at_the_boundaries(k: int, n: int) -> None:
    low, high = wilson(k, n)
    assert math.isfinite(low) and math.isfinite(high) and 0 <= low <= high <= 1


def test_alpha_is_a_status_where_the_denominator_would_be_zero() -> None:
    for units in ([], [["a"]], [["a", "a"], ["a", "a"]], [["a", None], ["b", None]]):
        got = alpha_nominal(units)
        assert got.alpha is None and got.why_not
    full = alpha_nominal([["a", "b"], ["a", "b"]])
    assert full.alpha is not None and math.isfinite(full.alpha)


# R5 and R6: rivals and surprise


def rival_pair(board2: dict[str, Any]) -> None:
    h1, h = board2["hypotheses"][0], h2(board2)
    h.update(rule=RULE, status="testing", rivals=["H1"])
    h["observed"] = {"k": 2, "n": 100, "artefact": "s4"}
    h1.update(
        status="testing",
        rule=RULE | {"op": "<", "threshold": 0.20},
    )
    h1.pop("resolved_in", None)


def test_rivals_are_hypotheses(board2: dict[str, Any]) -> None:
    h2(board2)["rivals"] = ["H2", "H9"]
    assert found(board2, "error", "H2") == [
        "a hypothesis is not its own rival",
        "rival 'H9' is not a hypothesis",
    ]


def test_surprise_when_no_rival_expects_the_result(board2: dict[str, Any]) -> None:
    rival_pair(board2)
    hint = [m for m in found(board2, "hint", "H2") if "outside the interval" in m]
    assert len(hint) == 1 and "rivals H1" in hint[0] and "escaped: [H2, H1]" in hint[0]
    assert "a signal with date" in hint[0]
    # a rival that the result does not refute: no surprise
    board2["hypotheses"][0]["rule"] = RULE | {"op": ">"}
    assert not [m for m in found(board2, "hint", "H2") if "outside the interval" in m]


@pytest.mark.parametrize("status", ["untested", "confirmed", "refuted"])
def test_surprise_only_for_a_hypothesis_in_testing(
    board2: dict[str, Any], status: str
) -> None:
    rival_pair(board2)
    h2(board2)["status"] = status
    assert not [m for m in found(board2, "hint", "H2") if "outside the interval" in m]


def test_surprise_is_logged_by_a_note_with_escaped(board2: dict[str, Any]) -> None:
    rival_pair(board2)
    note = {
        "id": "n-surprise",
        "board": "s",
        "half": "big",
        "kind": "signal",
        "label": "2 of 100",
    }
    note["seen_from"] = "p-owner"
    note |= {"escaped": ["H2", "H1"], "date": "2026-11-02"}
    board2["elements"].append(note)
    assert not [m for m in found(board2, "hint", "H2") if "outside the interval" in m]
    assert found(board2, "error", "n-surprise") == []
    note["escaped"] = ["H2", "H7"]
    del note["date"]
    assert found(board2, "error", "n-surprise") == [
        "'escaped' needs the 'date' of the surprise",
        "escaped 'H7' is not a hypothesis",
    ]


def test_escaped_and_date_go_together_on_a_signal_or_note(
    board2: dict[str, Any],
) -> None:
    fn = next(e for e in board2["elements"] if e["id"] == "fn-dough")
    fn.update(escaped=["H1"], date="2026-11-02")
    assert "'escaped' is only for signal or note" in found(board2, "error", "fn-dough")
    del fn["escaped"]
    assert "'date' is only for a surprise: it needs 'escaped'" in found(
        board2, "error", "fn-dough"
    )


# R6: the red line needs a recovery time and an address, on every profile


def test_red_line_without_recovery_or_address_on_every_profile(
    board2: dict[str, Any],
) -> None:
    quiet = copy.deepcopy(board2)
    assert not [m for m in found(quiet, "hint", "rl-unsold") if "escalation" in m]
    rl = next(e for e in board2["elements"] if e["id"] == "rl-unsold")
    del rl["line"]["recovery_days"]
    board2["relations"] = [
        r
        for r in board2["relations"]
        if r["from"] != "rl-unsold" or r["kind"] != "flow"
    ]
    [msg] = found(board2, "hint", "rl-unsold")[:1]
    assert msg.startswith(
        "a red line with a line and no recovery time (recovery_time or "
        "line.recovery_days) and no escalation address (a flow of information to "
        "a post, position or place for others)"
    )
    rl.pop("line")
    rl["red_line"] = True
    assert any(
        m.startswith("a red line with no value and")
        for m in found(board2, "hint", "rl-unsold")
    )
