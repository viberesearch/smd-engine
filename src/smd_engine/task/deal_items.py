"""Deal rules over the items of a pack that the diff applies: which choice items
the alpha is computed on."""

from __future__ import annotations

from typing import Any

from smd_engine.task.positions import is_deal
from smd_engine.task.ranges import classify_range

# the answers of the deal kinds, in the order the pages show them
DEAL_CHOICES = {
    "fact": ("holds", "does_not_hold", "cannot_say"),
    "line": ("accept", "reject"),
}
# natures whose answers are expected to differ between the positions
OPEN_NATURES = ("value", "position")


def alpha_items(
    pack: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """(the choice items alpha is computed on, the basis block of the diff).
    Alpha treats the members as interchangeable raters, so it reads the shared
    core only: no item for some positions, none of nature value or position.
    The basis is None for a pack where nothing is left out and that has no
    positions, so a group diff stays as it was."""
    choice = [i for i in pack["items"] if i["kind"] == "choice"]
    used = [
        i for i in choice if "audience" not in i and i.get("nature") not in OPEN_NATURES
    ]
    if len(used) == len(choice) and not is_deal(pack):
        return used, None
    return used, {"scope": "core", "items": len(used), "of": len(choice)}


def value_problem(kind: str, value: Any) -> str:
    """Why an answer does not fit a fact or line item, or an empty string."""
    allowed = DEAL_CHOICES[kind]
    if isinstance(value, str) and value in allowed:
        return ""
    return f"a {kind} item takes one of {', '.join(allowed)}"


def classify_deal(
    kind: str, values: dict[str, Any]
) -> tuple[str, str | None, dict[str, Any] | None] | None:
    """(class, subtype, sets) of the answers to a fact, line or range item, or
    None for another kind. A fact conflict is a `fact` conflict: the claim names a
    source that can settle it. One rejection makes a line `line_rejected`."""
    if kind == "range":
        return classify_range(values)
    if kind == "line":
        return (
            ("line_rejected" if "reject" in values.values() else "agreement"),
            None,
            None,
        )
    if kind == "fact":
        same = len(set(values.values())) == 1
        return ("agreement", None, None) if same else ("conflict", "fact", None)
    return None


def point_extra(item: dict[str, Any]) -> dict[str, Any]:
    """The deal fields of an item that its diff point carries."""
    extra: dict[str, Any] = {}
    for key in ("nature", "fit_of", "claim", "line", "unit"):
        if key in item:
            extra[key] = item[key]
    return extra


def apply_after_reading(points: list[dict[str, Any]]) -> None:
    """A fit point whose reading point is a conflict cannot be read yet: it gets
    `after_reading` (the reading point's id) and goes to the call, whatever its
    own class. Members who agree that the business fits while they read it
    differently have not agreed on anything yet."""
    by_id = {p["id"]: p for p in points}
    for p in points:
        reading = by_id.get(p.get("fit_of", ""))
        if reading and reading["class"] == "conflict":
            p["after_reading"] = reading["id"]
            p["route"] = "call"
