"""Red lines read from observations (gate КЛ1 В, the case owner 31.10.2026).

A red line is an absolute value a stakeholder set and data check (the case owner
26.10): a corridor (`line.min` and/or `line.max`) or a yes/no (`line.expect`).
It is in force from `line.since` (else the record's `date`) to `line.until`.
Observations `{value, date, source}` sit on the same element, in `observed`.

The breach rule is deterministic: the observations are sorted by date; a value
is outside when it is below `min`, above `max`, or differs from `expect`; a
run of consecutive outside values spans from its first date to the date of
the next inside value; a run with none after it spans to the record's `date`
when that is later than the last observation (else to the last observation),
and not past `until`; the run is a breach when its span in days is longer
than the recovery time (`line.recovery_days`, else the channel's
`recovery_time`), and any run is one when there is no recovery time. Only the
observations from the line's start (`since`, else the record's `date`) to
`until` are read."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class Breach:
    start: str  # ISO date of the first outside value
    end: str  # ISO date of the next inside value; for an open run, see breaches
    days: int
    closed: bool  # an inside value followed the run


def day(text: Any) -> dt.date:
    return dt.date.fromisoformat(str(text)[:10])


def is_yes_no(line: dict[str, Any]) -> bool:
    return "expect" in line


def fits(line: dict[str, Any], value: Any) -> bool:
    """Whether an observed value has the type the line reads: a boolean for a
    yes/no line, a number (not a boolean) for a corridor."""
    if is_yes_no(line):
        return isinstance(value, bool)
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def outside(line: dict[str, Any], value: Any) -> bool:
    """A value of the right type that the line does not allow."""
    if not fits(line, value):
        return False
    if is_yes_no(line):
        return bool(value is not line["expect"])
    return bool(
        ("min" in line and value < line["min"])
        or ("max" in line and value > line["max"])
    )


def recovery(el: dict[str, Any]) -> float | None:
    """Days a breach may last before it counts: `line.recovery_days`, else the
    algedonic channel's `recovery_time`; None when neither is set."""
    found = el.get("line", {}).get("recovery_days", el.get("recovery_time"))
    return float(found) if found is not None else None


def ordered(el: dict[str, Any]) -> list[dict[str, Any]]:
    """The element's observations of a fitting type, by date (stable)."""
    line = el.get("line", {})
    return sorted(
        (o for o in el.get("observed", []) if fits(line, o["value"])),
        key=lambda o: day(o["date"]),
    )


def read(el: dict[str, Any], record_date: Any = None) -> list[dict[str, Any]]:
    """The observations the breach rule reads: `ordered`, from the day the
    line takes force (`since`, else the record's `date`) to `until`."""
    line = el.get("line", {})
    start = start_of(line, record_date)
    end = day(line["until"]) if "until" in line else None
    return [
        o
        for o in ordered(el)
        if (start is None or day(o["date"]) >= start)
        and (end is None or day(o["date"]) <= end)
    ]


def before_start(el: dict[str, Any], record_date: Any) -> list[str]:
    """Dates of observations before the line takes force: not read."""
    start = start_of(el.get("line", {}), record_date)
    if start is None:
        return []
    return [str(o["date"]) for o in ordered(el) if day(o["date"]) < start]


def repeated_dates(el: dict[str, Any]) -> list[str]:
    """Dates that carry more than one observation, each once, in order."""
    seen: set[str] = set()
    out: list[str] = []
    for o in el.get("observed", []):
        d = str(o["date"])
        if d in seen and d not in out:
            out.append(d)
        seen.add(d)
    return out


def breaches(el: dict[str, Any], record_date: Any = None) -> list[Breach]:
    """The breaches of an element's line by its observations (module rule). A
    run still outside at the last observation is measured to the record's
    `date` when that is later (Beer's recovery time runs to now), but not
    past `until`."""
    line = el.get("line")
    if not line:
        return []
    obs = read(el, record_date)
    limit = recovery(el)
    runs: list[tuple[str, str, bool]] = []
    start: str | None = None
    for o in obs:
        if outside(line, o["value"]):
            start = start or str(o["date"])
        elif start is not None:
            runs.append((start, str(o["date"]), True))
            start = None
    if start is not None:
        end = day(obs[-1]["date"])
        if record_date:
            end = max(end, day(record_date))
        if "until" in line:
            end = min(end, day(line["until"]))
        runs.append((start, end.isoformat(), False))
    out = []
    for first, last, closed in runs:
        days = (day(last) - day(first)).days
        if limit is None or days > limit:
            out.append(Breach(first, last, days, closed))
    return out


def start_of(line: dict[str, Any], record_date: Any) -> dt.date | None:
    """The day the line takes force: `since`, else the record's `date`."""
    found = line.get("since", record_date)
    return day(found) if found else None


def span_years(line: dict[str, Any], record_date: Any) -> float | None:
    """Years the line is in force, `until` minus its start; None without one."""
    start = start_of(line, record_date)
    if start is None or "until" not in line:
        return None
    return (day(line["until"]) - start).days / DAYS_PER_YEAR


def after_end(el: dict[str, Any], record_date: Any) -> list[str]:
    """The dates past the line's `until`: the record's own `date`, then the
    observations, each once."""
    line = el.get("line", {})
    if "until" not in line:
        return []
    end = day(line["until"])
    dates = ([str(record_date)] if record_date else []) + [
        str(o["date"]) for o in el.get("observed", [])
    ]
    out: list[str] = []
    for d in dates:
        if day(d) > end and d not in out:
            out.append(d)
    return out


def last_observed(el: dict[str, Any]) -> dict[str, Any] | None:
    obs = ordered(el)
    return obs[-1] if obs else None
