"""Red lines on the boards (gates ИИ1 Б and КЛ1 В): which elements are red
lines, what they are linked to, the checks of their structured value `line`
and of their `observed` values, and the hints that read them
(src/smd_engine/redline.py holds the breach rule)."""

from __future__ import annotations

from typing import Any

from smd_engine.redline import (
    after_end,
    before_start,
    breaches,
    fits,
    is_yes_no,
    repeated_dates,
    span_years,
)
from smd_engine.redline import day
from smd_engine.validate.context import Ctx, Finding, board_set, cite_findings, hint

CHANNEL = "algedonic_channel"


def is_red_line(el: dict[str, Any]) -> bool:
    """An element that stands for a red line: `red_line: true`, or an
    `algedonic_channel` with a `threshold` or a `line` (the management
    profile's carrier of a stakeholder's red line, BEER1972 Гл. 17)."""
    return el.get("red_line") is True or (
        el["kind"] == CHANNEL and bool(el.get("threshold") or el.get("line"))
    )


def linked(ctx: Ctx, el_id: str) -> list[str]:
    """The element and what it is linked to, in this order: itself, the
    elements it is `in`, its `performed_by`, the elements `in` it, those it
    performs, and the elements a relation of any kind joins to it, either way;
    each once."""
    el = ctx.by_id[el_id]
    near: list[Any] = [el_id, *el.get("in", []), el.get("performed_by")]
    for other in ctx.by_id.values():
        if el_id in other.get("in", []) or other.get("performed_by") == el_id:
            near.append(other["id"])
    for rel in ctx.record.get("relations", []):
        near.append({rel["from"]: rel["to"], rel["to"]: rel["from"]}.get(el_id))
    out: list[str] = []
    for x in near:
        if x in ctx.by_id and x not in out:
            out.append(x)
    return out


def red_lines(ctx: Ctx, el_id: str) -> list[str]:
    """The red lines an element is linked to (`linked`), itself included."""
    return [x for x in linked(ctx, el_id) if is_red_line(ctx.by_id[x])]


def _line_findings(el: dict[str, Any], record_date: Any) -> list[str]:
    """What is wrong with an element's `line`, as error messages."""
    line = el["line"]
    out = []
    if not (el.get("red_line") is True or el["kind"] == CHANNEL):
        out.append(
            "'line' is only for red lines: red_line: true or an algedonic channel"
        )
    corridor = "min" in line or "max" in line
    if corridor and is_yes_no(line):
        out.append("line is a corridor (min, max) or a yes/no (expect), not both")
    elif not corridor and not is_yes_no(line):
        out.append("line needs a corridor (min and/or max) or a yes/no (expect)")
    if "min" in line and "max" in line and line["min"] >= line["max"]:
        out.append(f"line min {line['min']:g} is not below max {line['max']:g}")
    start = line.get("since", record_date)
    if start and day(line["until"]) <= day(start):
        what = "since" if "since" in line else "the record's date"
        out.append(f"line until {line['until']} is not after {what} {start}")
    if (
        "recovery_days" in line
        and "recovery_time" in el
        and line["recovery_days"] != el["recovery_time"]
    ):
        out.append(
            f"line recovery_days {line['recovery_days']:g} differs from "
            f"recovery_time {el['recovery_time']:g}"
        )
    return out


@board_set
def check_lines(ctx: Ctx) -> list[Finding]:
    """Errors and warnings of `line` and of an element's `observed`."""
    out: list[Finding] = []
    record_date = ctx.record.get("date")
    for el in ctx.by_id.values():
        eid = el["id"]
        if "line" in el:
            out += [Finding("error", eid, m) for m in _line_findings(el, record_date)]
        if "observed" not in el:
            continue
        if "line" not in el:
            out.append(Finding("error", eid, "'observed' needs a 'line' to be read by"))
            continue
        early = before_start(el, record_date)
        if early:
            out.append(
                Finding(
                    "warning",
                    eid,
                    "observed before the line takes force, not read: "
                    + ", ".join(early),
                )
            )
        for d in repeated_dates(el):
            out.append(
                Finding("warning", eid, f"one observation per date: {d} is given twice")
            )
        kind = "yes/no" if is_yes_no(el["line"]) else "corridor"
        for n, o in enumerate(el["observed"], 1):
            if not fits(el["line"], o["value"]):
                out.append(
                    Finding(
                        "error",
                        eid,
                        f"observed {n}: value {o['value']!r} does not fit a {kind} line",
                    )
                )
            sid = str(o["source"]).split("#")[0]
            out += cite_findings([sid], eid, ctx.source_ids)
            found = (ctx.source_kinds or {}).get(sid)
            if found is not None and found != "field_artefact":
                out.append(
                    Finding(
                        "warning",
                        eid,
                        f"observed {n} rests on '{sid}', a source of kind "
                        f"'{found}', not field_artefact",
                    )
                )
    return out


@hint("red-line-without-value")
def hint_red_line_without_value(ctx: Ctx) -> list[Finding]:
    """A red line is an absolute value, a threshold or yes/no that data check
    (the case owner 26.10): an element with `red_line: true` names it in `line` (or,
    for old records, in the free-text `threshold`)."""
    return [
        Finding(
            "hint",
            el["id"],
            "red line with no value: name the corridor or the yes/no that the "
            "data check, in 'line'",
        )
        for el in ctx.by_id.values()
        if el.get("red_line") is True and not el.get("line") and not el.get("threshold")
    ]


@hint("red-line-breach")
def hint_red_line_breach(ctx: Ctx) -> list[Finding]:
    out = []
    for el in ctx.by_id.values():
        found = breaches(el, ctx.record.get("date"))
        if found:
            runs = "; ".join(
                f"{b.start} to {b.end} ({b.days} days{'' if b.closed else ', still outside'})"
                for b in found
            )
            out.append(Finding("hint", el["id"], f"red line breached: {runs}"))
    return out


@hint("red-line-expired")
def hint_red_line_expired(ctx: Ctx) -> list[Finding]:
    out = []
    for el in ctx.by_id.values():
        late = after_end(el, ctx.record.get("date"))
        if late:
            out.append(
                Finding(
                    "hint",
                    el["id"],
                    f"the line ended on {el['line']['until']}: renew or drop "
                    f"(dates after it: {', '.join(late)})",
                )
            )
    return out


@hint("red-line-outlives-pace")
def hint_red_line_outlives_pace(ctx: Ctx) -> list[Finding]:
    """A line in force longer than the `pace` of an element it is linked to:
    the term is matched to the pace of its tier (the case owner 26.10, H24)."""
    out = []
    for el in ctx.by_id.values():
        if "line" not in el:
            continue
        years = span_years(el["line"], ctx.record.get("date"))
        if years is None:
            continue
        faster = [
            f"{x} ({ctx.by_id[x]['pace']:g})"
            for x in linked(ctx, el["id"])
            if "pace" in ctx.by_id[x] and years > ctx.by_id[x]["pace"]
        ]
        if faster:
            out.append(
                Finding(
                    "hint",
                    el["id"],
                    f"the line is in force {years:.1f} years, longer than the pace "
                    f"in years of {', '.join(faster)}: match its end to that pace",
                )
            )
    return out
