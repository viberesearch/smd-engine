"""Item kind `range`: an answer is `{min, max, unit, date?}`, a span of numbers in
the unit the item names. The script classes the answers of two or more members:
identical spans are an agreement; spans each inside the last (a chain) are a
refinement; spans that share a stretch but are not a chain are `compatible`;
spans with no common stretch are a conflict of subtype `value`. Nothing here is
averaged or merged: the common stretch is shown, not decided."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

KEYS = ("min", "max", "unit", "date")
Span = tuple[float, float]


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def has_range(pack: dict[str, Any]) -> bool:
    return any(i["kind"] == "range" for i in pack["items"])


def range_problem(item: dict[str, Any], value: Any) -> str:
    """Why an answer does not fit a range item, or an empty string. The unit has
    to be the item's own, so two answers are always in one unit."""
    if not isinstance(value, dict):
        return "a range item takes {min, max, unit}"
    missing = [k for k in ("min", "max", "unit") if k not in value]
    if missing:
        return f"a range needs {', '.join(missing)}"
    extra = [k for k in value if k not in KEYS]
    if extra:
        return f"a range has no {', '.join(extra)}"
    if not (_number(value["min"]) and _number(value["max"])):
        return "min and max of a range are numbers"
    if not (math.isfinite(value["min"]) and math.isfinite(value["max"])):
        return "min and max of a range are finite numbers"
    if value["min"] > value["max"]:
        return "min of a range is above its max"
    if value["unit"] != item.get("unit"):
        return (
            f"the unit of a range here is {item.get('unit')!r}, not {value['unit']!r}"
        )
    if "date" in value:
        try:
            date.fromisoformat(str(value["date"]))
        except ValueError:
            return "date of a range is a date like 2026-11-02"
    return ""


def _span(value: dict[str, Any]) -> Span:
    return float(value["min"]), float(value["max"])


def _inside(inner: Span, outer: Span) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def classify_range(
    values: dict[str, Any],
) -> tuple[str, str | None, dict[str, Any] | None]:
    """(class, subtype, sets) of the ranges of two or more members. `sets` holds
    the stretch all of them share, for a refinement and a compatible class."""
    spans = [_span(v) for v in values.values()]
    if len(set(spans)) == 1:
        return "agreement", None, None
    low = max(v["min"] for v in values.values())
    high = min(v["max"] for v in values.values())
    if low > high:
        return "conflict", "value", None
    unit = next(iter(values.values()))["unit"]
    sets = {"common": {"min": low, "max": high, "unit": unit}, "only_by": {}}
    wide_first = sorted(spans, key=lambda s: s[0] - s[1])
    chain = all(_inside(b, a) for a, b in zip(wide_first, wide_first[1:]))
    return ("refinement" if chain else "compatible"), None, sets


def _figure(x: Any) -> str:
    f = float(x)
    return str(int(f)) if f == int(f) else str(f)


def range_text(value: dict[str, Any], lang: str) -> str:
    """A range as people read it: "4 to 8 weeks", "от 4 до 8 weeks"."""
    unit = value.get("unit", "")
    lo, hi = _figure(value["min"]), _figure(value["max"])
    text = f"от {lo} до {hi} {unit}" if lang == "ru" else f"{lo} to {hi} {unit}"
    if value.get("date"):
        text += f" ({'на' if lang == 'ru' else 'as of'} {value['date']})"
    return text.strip()
