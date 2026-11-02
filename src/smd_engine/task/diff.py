"""`smd task diff`: the members' answers side by side, with the classes a script
can decide and the routes by class.

Structured kinds are classed here, the same way for anyone who re-runs it:
agreement (same value), refinement (one set holds another, multi and ids),
conflict (different values). Text, term-check items and the subtype of a conflict
(term, position, fact, value) are left to the model, which follows
`procedures/task-diff.md` and writes its result into `diff.yaml` with
`class_by: model`. Nothing here averages or merges answers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smd_engine.agree import FEW_UNITS, Alpha, alpha_nominal, reading
from smd_engine.records import RecordError
from smd_engine.task.check import check_answers, transcript_status
from smd_engine.task.deal_items import (
    alpha_items,
    apply_after_reading,
    classify_deal,
    point_extra,
)
from smd_engine.task.bounds import bound_point, deal_fields
from smd_engine.task.names import labels_block
from smd_engine.task.pairs import build_by_pair
from smd_engine.task.model import (
    Issue,
    load_task,
    member_ids,
    sha256_file,
)
from smd_engine.task.positions import audience_members, is_deal, member_positions

# class -> the default route (procedures/task-diff.md, docs/task-packs.md)
# A conflict takes its route from the subtype (CONFLICT_ROUTES).
ROUTES = {
    "agreement": "accept",
    "refinement": "accept_unless_objected",
    "only_one": "mark_each",
    "compatible_steps": "accept",
    "compatible": "accept_unless_objected",
    "to_read": "call",
    "unanswered": "call",
    "line_rejected": "blocking",
}
CONFLICT_ROUTES = {
    "term": "call",
    "position": "record_positions",
    "fact": "check",
    "value": "call",
    "step": "call",
    None: "call",
}
SUBTYPES = ("term", "position", "fact", "value", "step")
# Routes that wait for a reply from the members (step 4): the others are
# settled by the class unless a member marks the point "discuss".
OPEN_ROUTES = ("call", "mark_each")


def route_for(cls: str, subtype: str | None = None) -> str:
    if cls == "conflict":
        return CONFLICT_ROUTES[subtype]
    return ROUTES[cls]


def is_open(route: str) -> bool:
    return route in OPEN_ROUTES


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _scalar(value: Any) -> Any:
    """A choice or a number as a comparable value: 3 and 3.0 are the same."""
    return float(value) if isinstance(value, (int, float)) else value


def _members_set(value: list[str]) -> dict[str, str]:
    """normalised text -> the text as written (the first one)"""
    out: dict[str, str] = {}
    for v in value:
        out.setdefault(_norm(v), v)
    return out


def classify_structured(
    kind: str, values: dict[str, Any]
) -> tuple[str, str | None, dict[str, Any] | None]:
    """(class, subtype, sets) of the values of two or more members."""
    deal = classify_deal(kind, values)
    if deal:
        return deal
    if kind in ("choice", "number"):
        same = len({_scalar(v) for v in values.values()}) == 1
        return ("agreement" if same else "conflict"), None, None
    given = {m: _members_set(v) for m, v in values.items()}
    sets = {m: frozenset(g) for m, g in given.items()}
    if len(set(sets.values())) == 1:
        return "agreement", None, None
    common = frozenset.intersection(*sets.values())
    text = {k: v for g in given.values() for k, v in g.items()}
    detail = {
        "common": sorted(text[k] for k in common),
        "only_by": {
            m: sorted(text[k] for k in s - common)
            for m, s in sets.items()
            if s - common
        },
    }
    if kind == "steps":
        return "conflict", "step", detail
    ordered = sorted(sets.values(), key=len)
    if all(a <= b for a, b in zip(ordered, ordered[1:])):
        return "refinement", None, detail
    return "conflict", None, detail


def _alpha_dict(a: Alpha) -> dict[str, Any]:
    text = reading(a.alpha)
    if a.alpha is not None and a.pairable_units < FEW_UNITS:
        text += ", few units"
    return {
        "units": a.units,
        "pairable_units": a.pairable_units,
        "pairable_values": a.pairable_values,
        "alpha": None if a.alpha is None else round(a.alpha, 3),
        "reading": text,
        "why_not": a.why_not,
    }


def alphas(
    pack: dict[str, Any], given: dict[str, dict[str, dict[str, Any]]]
) -> dict[str, Any]:
    """Krippendorff's alpha over the choice items, and per section; the members
    are the raters, and a member who gave no answer to an item is a gap. In a
    deal pack only the shared core counts (deal_items.alpha_items)."""
    members = member_ids(pack)
    choice, basis = alpha_items(pack)

    def rows(items: list[dict[str, Any]]) -> list[list[Any]]:
        return [
            [given.get(i["id"], {}).get(m, {}).get("value") for m in members]
            for i in items
        ]

    sections: dict[str, Any] = {}
    for name in dict.fromkeys(i["section"] for i in choice):
        sections[name] = _alpha_dict(
            alpha_nominal(rows([i for i in choice if i["section"] == name]))
        )
    return {
        "choice_items": _alpha_dict(alpha_nominal(rows(choice))),
        "sections": sections,
        **({"basis": basis} if basis else {}),
    }


def _answer(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        k: entry[k]
        for k in ("value", "reason", "source", "source_ids", "confidence", "term_note")
        if k in entry
    }


def _point(
    pid: str,
    kind: str,
    extra: dict[str, Any],
    answers: dict[str, dict[str, Any]],
    members: list[str],
    item_kind: str | None,
) -> dict[str, Any]:
    point: dict[str, Any] = {"id": pid, "kind": kind, **extra, "answers": answers}
    silent = [m for m in members if m not in answers]
    if silent:
        point["silent"] = silent
    sets = None
    if not answers:
        cls, by, subtype = "unanswered", "script", None
    elif item_kind == "line" and "reject" in [a["value"] for a in answers.values()]:
        cls, by, subtype = "line_rejected", "script", None
    elif len(answers) == 1:
        cls, by, subtype = "only_one", "script", None
        point["raised_by"] = next(iter(answers))
    elif item_kind is None or item_kind == "text":
        cls, by, subtype = "to_read", "model", None
    else:
        cls, subtype, sets = classify_structured(
            item_kind, {m: a["value"] for m, a in answers.items()}
        )
        by = "script"
    point["class"] = cls
    point["class_by"] = by
    if cls == "conflict":
        point["subtype"] = subtype  # null until the model reads the answers
    if sets:
        point["sets"] = sets
    point["route"] = route_for(cls, subtype)
    return point


def load_answers(
    pack: dict[str, Any], pack_sha: str, paths: list[Path]
) -> list[tuple[Path, str, dict[str, Any]]]:
    """The answers files, refused when one is for another text of the pack, or
    invalid, or a second file of the same member."""
    loaded: list[tuple[Path, str, dict[str, Any]]] = []
    seen: dict[str, Path] = {}
    for path in paths:
        ans = load_task(path, "task_answers")
        issues: list[Issue] = [
            i
            for i in check_answers(pack, pack_sha, ans, str(path), path.parent)
            if i.level == "error"
        ]
        if issues:
            raise RecordError(f"{path}: {issues[0].message}")
        if ans["member"] in seen:
            raise RecordError(
                f"{path}: {ans['member']} already answered in {seen[ans['member']]}"
            )
        seen[ans["member"]] = path
        loaded.append((path, sha256_file(path), ans))
    members = member_ids(pack)
    loaded.sort(key=lambda t: members.index(t[2]["member"]))
    return loaded


def build_diff(
    pack: dict[str, Any],
    pack_sha: str,
    loaded: list[tuple[Path, str, dict[str, Any]]],
    ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    members = member_ids(pack)
    by_member = {a["member"]: a for _, _, a in loaded}
    given: dict[str, dict[str, dict[str, Any]]] = {}
    for item in pack["items"]:
        given[item["id"]] = {
            m: _answer(a["answers"][item["id"]])
            for m, a in by_member.items()
            if item["id"] in a["answers"]
        }
    points: list[dict[str, Any]] = []
    for t in pack["term_check"]:
        answers = {
            m: {"value": a["term_check"][t["id"]]}
            for m, a in by_member.items()
            if a["term_check"].get(t["id"], "").strip()
        }
        extra = {"section": None, "term": t["term"], "question": t["question"]}
        points.append(_point(t["id"], "term_check", extra, answers, members, None))
    for item in pack["items"]:
        if item["kind"] == "bound":  # sealed: who committed, never an answer
            points.append(bound_point(pack, item, given, ledger))
            continue
        extra = {
            "section": item["section"],
            "question": item["question"],
            "item_kind": item["kind"],
            **point_extra(item),
        }
        if item.get("refs") and item["kind"] != "ids":
            extra["refs"] = item["refs"]
        who = members
        if "audience" in item:
            extra["audience"] = item["audience"]
            who = audience_members(pack, item)
        points.append(
            _point(item["id"], "item", extra, given[item["id"]], who, item["kind"])
        )
    apply_after_reading(points)
    for m, a in by_member.items():
        for n, added in enumerate(a.get("added", []), start=1):
            point = _point(
                f"add-{m}-{n}",
                "added",
                {
                    "section": None,
                    "text": added["text"],
                    **({"refs": added["refs"]} if added.get("refs") else {}),
                },
                {m: {"value": added["text"]}},
                members,
                None,
            )
            points.append(point)
    transcripts: dict[str, list[dict[str, Any]]] = {}
    for path, _, a in loaded:
        if a.get("transcripts"):
            transcripts[a["member"]] = [
                {**t, "status": transcript_status(t, path.parent)}
                for t in a["transcripts"]
            ]
    by_class: dict[str, int] = {}
    for p in points:
        by_class[p["class"]] = by_class.get(p["class"], 0) + 1
    return {
        "record": "task_diff",
        "schema_version": "0.1",
        "title": pack.get("title", pack["id"]),
        "pack": {"id": pack["id"], "version": pack["version"], "sha256": pack_sha},
        "lang": pack["lang"],
        "procedure": pack["diff"]["procedure"],
        "members": members,
        "answered_by": [a["member"] for _, _, a in loaded],
        "answers_files": [
            {
                "member": a["member"],
                "sha256": sha,
                "date": a["date"],
                "drafted_by": a["drafted_by"],
            }
            for _, sha, a in loaded
        ],
        **({"positions": member_positions(pack)} if is_deal(pack) else {}),
        **deal_fields(pack),
        **(
            {
                "by_pair": build_by_pair(
                    pack, points, _point, lambda e: is_open(e["route"])
                )
            }
            if pack.get("pairs")
            else {}
        ),
        "transcripts": transcripts,
        "labels": labels_block(pack),
        "alpha": alphas(pack, given),
        "summary": {
            "points": len(points),
            "open": sum(1 for p in points if is_open(p["route"])),
            "by_class": by_class,
        },
        "points": points,
    }
