"""Gate КЛ1 В: the structured value of a red line (`line`), its observations,
the breach rule (redline.py), the hints red-line-breach, red-line-expired and
red-line-outlives-pace, and the words on the pages."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from smd_engine.records import load_record
from smd_engine.redline import Breach, breaches
from smd_engine.render.html import render_html
from smd_engine.render.text import element_parts, number_text
from smd_engine.status import render_status
from smd_engine.validate import validate_record

ROOT = Path(__file__).resolve().parents[1]
ORU = ROOT / "cases" / "example_ru" / "pekarni-oru-c1.board.yaml"
PEKARNI = ROOT / "cases" / "example_ru" / "pekarni-c2.board.yaml"


def el(record: dict[str, Any], eid: str) -> dict[str, Any]:
    return next(e for e in record["elements"] if e["id"] == eid)


def found(record: dict[str, Any], level: str, **kw: Any) -> list[str]:
    return [
        f"{f.ref}: {f.message}"
        for f in validate_record(record, **kw)
        if f.level == level
    ]


def obs(*pairs: tuple[Any, str]) -> list[dict[str, Any]]:
    return [{"value": v, "date": d, "source": "s3"} for v, d in pairs]


@pytest.fixture
def line(board2: dict[str, Any]) -> dict[str, Any]:
    """The example's red line rl-unsold: unsold dough at most 5 %, from
    2026-03-01 to 2027-02-28, recovery 14 days."""
    return el(board2, "rl-unsold")


def test_example_line_is_valid_and_quiet(board2: dict[str, Any]) -> None:
    assert found(board2, "error") == [] and found(board2, "warning") == []
    assert not [h for h in found(board2, "hint") if "red line" in h or "line " in h]


@pytest.mark.parametrize(
    "change",
    [
        lambda x: x["line"].pop("until"),
        lambda x: x["line"].update(years=5),  # no other keys
        lambda x: x["line"].update(until="soon"),
        lambda x: x.update(observed=[{"value": 3, "date": "2026-04-01"}]),
        lambda x: x.update(
            observed=[{"value": "3", "date": "2026-04-01", "source": "s3"}]
        ),
    ],
)
def test_schema_refuses(
    board2: dict[str, Any], line: dict[str, Any], change: Any
) -> None:
    change(line)
    assert any(
        m.startswith(("record", "rl-unsold", "elements"))
        for m in found(board2, "error")
    )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda x: x.update(expect=True), "not both"),
        (lambda x: x.pop("max"), "needs a corridor"),
        (lambda x: x.update(min=5), "min 5 is not below max 5"),
        (lambda x: x.update(until="2026-03-01"), "is not after since 2026-03-01"),
        (
            lambda x: (x.pop("since"), x.update(until="2026-01-10")),
            "is not after the record's date 2026-01-17",
        ),
    ],
)
def test_line_errors(
    board2: dict[str, Any], line: dict[str, Any], change: Any, message: str
) -> None:
    change(line["line"])
    assert any(
        m.startswith("rl-unsold") and message in m for m in found(board2, "error")
    )


def test_one_sided_and_yes_no_lines_are_valid(
    board2: dict[str, Any], line: dict[str, Any]
) -> None:
    line["line"] = {"min": 1, "until": "2027-01-01"}
    assert found(board2, "error") == []
    line["line"] = {
        "metric": "dough before four",
        "expect": True,
        "until": "2027-01-01",
    }
    assert found(board2, "error") == []


def test_line_only_on_red_lines(board2: dict[str, Any], line: dict[str, Any]) -> None:
    del line["red_line"]
    assert (
        "rl-unsold: 'line' is only for red lines: red_line: true or an algedonic channel"
        in found(board2, "error")
    )


def test_observed_needs_a_line(board2: dict[str, Any], line: dict[str, Any]) -> None:
    del line["line"]
    line["observed"] = obs((3, "2026-04-01"))
    assert "rl-unsold: 'observed' needs a 'line' to be read by" in found(
        board2, "error"
    )


@pytest.mark.parametrize(
    ("new_line", "value", "kind"),
    [
        ({"max": 5, "until": "2027-01-01"}, True, "corridor"),
        ({"metric": "m", "expect": True, "until": "2027-01-01"}, 1, "yes/no"),
    ],
)
def test_observed_type_fits_the_line(
    board2: dict[str, Any],
    line: dict[str, Any],
    new_line: dict[str, Any],
    value: Any,
    kind: str,
) -> None:
    line["line"] = new_line
    line["observed"] = obs((value, "2026-04-01"))
    assert (
        f"rl-unsold: observed 1: value {value!r} does not fit a {kind} line"
        in found(board2, "error")
    )


def test_observed_source_against_the_manifest(
    board2: dict[str, Any], line: dict[str, Any]
) -> None:
    line["observed"] = obs((3, "2026-04-01"))
    kw = {"source_ids": {"s3"}, "source_kinds": {"s3": "transcript"}}
    assert any("not field_artefact" in w for w in found(board2, "warning", **kw))
    kw = {"source_ids": {"s3"}, "source_kinds": {"s3": "field_artefact"}}
    assert found(board2, "warning", **kw) == []
    line["observed"][0]["source"] = "s99"
    assert any("s99" in m for m in found(board2, "error", source_ids={"s3"}))


@pytest.fixture
def channel() -> dict[str, Any]:
    data = copy.deepcopy(load_record(ORU))
    data["elements"].append(
        {
            "id": "ch-unsold",
            "board": "ot",
            "kind": "algedonic_channel",
            "label": "непроданное тесто",
            "seen_from": "p-organiser",
            "recovery_time": 14,
            "line": {"max": 5, "unit": "%", "until": "2027-02-28", "recovery_days": 14},
        }
    )
    data["relations"].append(
        {"from": "ch-unsold", "to": "post-director", "kind": "escalates"}
    )
    return data


def test_channel_recovery_must_agree(channel: dict[str, Any]) -> None:
    assert found(channel, "error") == []
    el(channel, "ch-unsold")["recovery_time"] = 7
    assert any("differs from recovery_time 7" in m for m in found(channel, "error"))


def test_channel_recovery_time_is_read_without_recovery_days(
    channel: dict[str, Any],
) -> None:
    ch = el(channel, "ch-unsold")
    del ch["line"]["recovery_days"]
    ch["observed"] = obs((6, "2026-04-01"), (4, "2026-04-10"))
    assert breaches(ch) == []  # 9 days, within recovery_time 14
    ch["recovery_time"] = 5
    assert breaches(ch) == [Breach("2026-04-01", "2026-04-10", 9, True)]


def test_breach_runs_with_recovery_days(line: dict[str, Any]) -> None:
    line["observed"] = obs(
        (7, "2026-05-01"),  # outside, then inside after 9 days: no breach
        (4, "2026-05-10"),
        (6, "2026-06-01"),  # outside 2026-06-01 .. 2026-06-20: 19 days, breach
        (8, "2026-06-10"),
        (3, "2026-06-20"),
        (9, "2026-07-01"),  # outside to the last observation: 20 days, breach
        (6, "2026-07-21"),
    )
    line["observed"].reverse()  # read by date, not in the order written
    assert breaches(line) == [
        Breach("2026-06-01", "2026-06-20", 19, True),
        Breach("2026-07-01", "2026-07-21", 20, False),
    ]


def test_breach_runs_without_recovery_days(line: dict[str, Any]) -> None:
    del line["line"]["recovery_days"]
    line["observed"] = obs((7, "2026-05-01"), (4, "2026-05-10"), (6, "2026-06-01"))
    assert breaches(line) == [
        Breach("2026-05-01", "2026-05-10", 9, True),
        Breach("2026-06-01", "2026-06-01", 0, False),
    ]


def test_yes_no_breach(line: dict[str, Any]) -> None:
    line["line"] = {"expect": True, "until": "2027-01-01"}
    line["observed"] = obs((True, "2026-05-01"), (False, "2026-05-02"))
    assert breaches(line) == [Breach("2026-05-02", "2026-05-02", 0, False)]


def test_breach_hint_and_status(board2: dict[str, Any], line: dict[str, Any]) -> None:
    line["observed"] = obs((6, "2026-06-01"), (3, "2026-06-20"))
    hint = next(f for f in validate_record(board2) if "breached" in f.message)
    assert hint.ref == "rl-unsold"
    assert hint.message == "red line breached: 2026-06-01 to 2026-06-20 (19 days)"
    assert hint.procedure == "procedures/field-result.md §5"
    text = render_status(board2, "ru")
    assert "## Красные линии с нарушением (1)" in text
    assert "вне линии с 01.06.2026 по 20.06.2026 (19 дней)" in text


def test_no_breach_section_without_one(board2: dict[str, Any]) -> None:
    assert "Red lines breached" not in render_status(board2, "en")


def test_expired_by_observation_or_record_date(
    board2: dict[str, Any], line: dict[str, Any]
) -> None:
    assert not [h for h in found(board2, "hint") if "ended on" in h]
    line["observed"] = obs((3, "2027-03-15"))
    assert (
        "rl-unsold: the line ended on 2027-02-28: renew or drop (dates after it: 2027-03-15)"
        in found(board2, "hint")
    )
    del line["observed"]
    board2["date"] = "2027-03-01"
    assert any("ended on 2027-02-28" in h for h in found(board2, "hint"))


def test_outlives_pace(board2: dict[str, Any], line: dict[str, Any]) -> None:
    fn = el(board2, "fn-dough")  # linked to rl-unsold by `refers`
    fn["pace"] = 0.5
    hints = [h for h in found(board2, "hint") if "pace" in h]
    assert hints == [
        "rl-unsold: the line is in force 1.0 years, longer than the pace in "
        "years of fn-dough (0.5): match its end to that pace"
    ]
    fn["pace"] = 2
    assert not [h for h in found(board2, "hint") if "pace" in h]
    # with no `since` the span starts at the record's date (2026-01-17)
    del line["line"]["since"]
    line["line"]["until"] = "2029-01-17"
    assert any("in force 3.0 years" in h for h in found(board2, "hint"))


def test_without_value_satisfied_by_line(
    line: dict[str, Any], board2: dict[str, Any]
) -> None:
    assert not [h for h in found(board2, "hint") if "no value" in h]
    del line["line"]
    assert any(
        h.startswith("rl-unsold: red line with no value") for h in found(board2, "hint")
    )


@pytest.mark.parametrize(
    ("new_line", "lang", "text"),
    [
        (
            {
                "metric": "доля ФОТ",
                "unit": "%",
                "min": 18,
                "max": 25,
                "since": "2027-01-01",
                "until": "2031-12-31",
                "recovery_days": 90,
            },
            "ru",
            "доля ФОТ от 18 до 25 %, с 01.01.2027 по 31.12.2031, восстановление 90 дней",
        ),
        (
            {"min": 2.5, "unit": "%", "until": "2031-12-31"},
            "ru",
            "не ниже 2,5 %, по 31.12.2031",
        ),
        ({"max": 5, "until": "2031-12-31"}, "en", "at most 5, until 2031-12-31"),
        (
            {
                "metric": "name kept",
                "expect": True,
                "since": "2027-01-01",
                "until": "2031-12-31",
            },
            "en",
            "name kept: yes, from 2027-01-01 to 2031-12-31",
        ),
    ],
)
def test_line_in_words(new_line: dict[str, Any], lang: str, text: str) -> None:
    item = {"id": "x", "kind": "standard", "red_line": True, "line": new_line}
    assert element_parts(item, lang) == {"red_line": text}


@pytest.mark.parametrize(
    ("new_line", "value", "lang", "text"),
    [
        (
            {"max": 5, "unit": "%", "until": "2031-12-31"},
            6,
            "ru",
            "6 % на 01.03.2027, вне коридора",
        ),
        (
            {"max": 5, "unit": "%", "until": "2031-12-31"},
            4,
            "en",
            "4 % on 2027-03-01, inside the corridor",
        ),
        (
            {"expect": True, "until": "2031-12-31"},
            False,
            "ru",
            "нет на 01.03.2027, нарушено",
        ),
        (
            {"expect": True, "until": "2031-12-31"},
            True,
            "en",
            "yes on 2027-03-01, kept",
        ),
    ],
)
def test_last_observation_in_words(
    new_line: dict[str, Any], value: Any, lang: str, text: str
) -> None:
    item = {
        "id": "x",
        "kind": "standard",
        "red_line": True,
        "line": new_line,
        "observed": obs(
            (not value if isinstance(value, bool) else 1, "2026-01-01"),
            (value, "2027-03-01"),
        ),
    }
    assert element_parts(item, lang)["observed"] == text


def test_russian_page_shows_the_example_line() -> None:
    page = render_html(load_record(PEKARNI), "ru")
    assert (
        "красная линия: доля непроданного теста от объёма ночи не выше 5 %, "
        "с 01.03.2026 по 28.02.2027, восстановление 14 дней"
    ) in page


def test_open_run_measured_to_the_record_date(line: dict[str, Any]) -> None:
    line["observed"] = obs((4, "2026-06-01"), (7, "2026-07-01"))
    # to the last observation alone the run is 0 days, within 14
    assert breaches(line) == []
    # Beer's recovery time runs to now: the record is dated a month later
    assert breaches(line, "2026-08-01") == [
        Breach("2026-07-01", "2026-08-01", 31, False)
    ]
    # an earlier record date does not shorten it; nor does the run pass `until`
    assert breaches(line, "2026-06-15") == []
    assert breaches(line, "2028-01-01") == [
        Breach("2026-07-01", "2027-02-28", 242, False)
    ]


def test_open_run_in_the_hint(board2: dict[str, Any], line: dict[str, Any]) -> None:
    board2["date"] = "2026-08-01"
    line["observed"] = obs((7, "2026-07-01"))
    assert (
        "rl-unsold: red line breached: 2026-07-01 to 2026-08-01 "
        "(31 days, still outside)" in found(board2, "hint")
    )


def test_observations_before_the_start(
    board2: dict[str, Any], line: dict[str, Any]
) -> None:
    # since 2026-03-01 lies after the record's date 2026-01-17: a line set ahead
    assert found(board2, "warning") == []
    line["observed"] = obs((9, "2026-02-01"), (4, "2026-03-15"))
    assert (
        "rl-unsold: observed before the line takes force, not read: 2026-02-01"
        in found(board2, "warning")
    )
    assert breaches(line, board2["date"]) == []
    # with no `since` the line takes force on the record's date
    del line["line"]["since"]
    line["observed"] = obs((9, "2026-01-10"))
    assert any("not read: 2026-01-10" in w for w in found(board2, "warning"))


def test_one_observation_per_date(board2: dict[str, Any], line: dict[str, Any]) -> None:
    line["observed"] = obs((4, "2026-04-01"), (6, "2026-04-01"), (3, "2026-05-01"))
    assert "rl-unsold: one observation per date: 2026-04-01 is given twice" in found(
        board2, "warning"
    )


def test_observations_after_until_not_read(
    board2: dict[str, Any], line: dict[str, Any]
) -> None:
    line["observed"] = obs((3, "2027-02-01"), (9, "2027-03-15"), (9, "2027-05-01"))
    assert breaches(line, board2["date"]) == []
    hints = found(board2, "hint")
    assert not [h for h in hints if "breached" in h]
    assert any(
        "ended on 2027-02-28" in h and "2027-03-15, 2027-05-01" in h for h in hints
    )


@pytest.mark.parametrize(
    ("n", "ru", "en"),
    [
        (1000000, "1 000 000", "1000000"),
        (2.5, "2,5", "2.5"),
        (1e-7, "0,0000001", "0.0000001"),
        (-12345.75, "-12 345,75", "-12345.75"),
        (18.0, "18", "18"),
    ],
)
def test_number_text_plain_digits(n: float, ru: str, en: str) -> None:
    assert number_text(n, "ru") == ru and number_text(n, "en") == en


def test_yes_no_line_without_metric() -> None:
    item: dict[str, Any] = {"id": "x", "kind": "standard", "red_line": True}
    item["line"] = {"expect": False, "until": "2031-12-31"}
    assert element_parts(item, "ru")["red_line"] == "ожидается: нет, по 31.12.2031"
    assert element_parts(item, "en")["red_line"] == "expected: no, until 2031-12-31"


def test_yes_no_line_needs_a_metric(
    board2: dict[str, Any], line: dict[str, Any]
) -> None:
    line["line"] = {"expect": True, "until": "2027-01-01"}
    assert any(
        "'metric' is a dependency of 'expect'" in m for m in found(board2, "error")
    )
