"""`smd task check`: the schema and the cross checks of a pack, its answers and
its replies. Errors stop a diff; warnings are things to look at."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from smd_engine.task.bounds import commitment_problem, optional_bound
from smd_engine.task.deal_items import DEAL_CHOICES, value_problem as deal_value_problem
from smd_engine.task.deal_check import deal_answers_findings, deal_pack_findings
from smd_engine.task.model import (
    TERM_CHECK_RANGE,
    Issue,
    member_ids,
    schema_issues,
    sha256_file,
)
from smd_engine.task.positions import in_audience, member_positions
from smd_engine.task.ranges import range_problem


def _dups(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v in seen and v not in out:
            out.append(v)
        seen.add(v)
    return out


def known_refs(pack: dict[str, Any]) -> set[str]:
    """Ids a `refs` list may name: ontology elements, sources, items, term checks."""
    return (
        {e["id"] for e in pack["ontology"]["elements"]}
        | {s["id"] for s in pack["sources"]}
        | {i["id"] for i in pack["items"]}
        | {t["id"] for t in pack["term_check"]}
    )


def _recommendation(item: dict[str, Any], where: str) -> list[Issue]:
    rec = item.get("recommendation")
    if rec is None or item["kind"] not in ("choice", "multi"):
        return []
    options = {o["id"] for o in item.get("options", [])}
    value = rec["value"]
    values = value if isinstance(value, list) else [value]
    bad = [v for v in values if v not in options]
    if bad or (item["kind"] == "choice" and isinstance(value, list)):
        return [
            Issue(
                "error",
                where,
                f"item {item['id']}: recommendation {value!r} is not "
                f"{'an option id' if item['kind'] == 'choice' else 'a list of option ids'}",
            )
        ]
    return []


def check_pack(pack: dict[str, Any], where: str) -> list[Issue]:
    issues = schema_issues(pack, "task_pack", where)
    if issues:
        return issues
    out: list[Issue] = []

    def err(msg: str) -> None:
        out.append(Issue("error", where, msg))

    members = member_ids(pack)
    for d in _dups(members):
        err(f"member id {d} is used twice")
    if pack["facilitator"] not in members:
        err(f"facilitator {pack['facilitator']} is not a member")
    ids = [i["id"] for i in pack["items"]] + [t["id"] for t in pack["term_check"]]
    for d in _dups(ids):
        err(f"id {d} is used twice among the items and the term check")
    for d in _dups([e["id"] for e in pack["ontology"]["elements"]]):
        err(f"ontology element id {d} is used twice")
    for d in _dups([s["id"] for s in pack["sources"]]):
        err(f"source id {d} is used twice")
    elements = {e["id"] for e in pack["ontology"]["elements"]}
    for r in pack["ontology"]["relations"]:
        for end in (r["from"], r["to"]):
            if end not in elements:
                err(f"relation {r['from']} -> {r['to']}: unknown element {end}")
    refs = known_refs(pack)
    for item in pack["items"]:
        for d in _dups([o["id"] for o in item.get("options", [])]):
            err(f"item {item['id']}: option id {d} is used twice")
        for ref in item.get("refs", []):
            if ref not in refs:
                err(f"item {item['id']}: ref {ref} names nothing in the pack")
        out.extend(_recommendation(item, where))
    out.extend(Issue(lv, where, msg) for lv, msg in deal_pack_findings(pack))
    low, high = TERM_CHECK_RANGE
    if not low <= len(pack["term_check"]) <= high:
        out.append(
            Issue(
                "warning",
                where,
                f"the term check has {len(pack['term_check'])} items; "
                f"the procedure asks for {low} to {high}",
            )
        )
    if pack["due"] < pack["date"]:
        out.append(Issue("warning", where, "due is before the pack's date"))
    return out


def transcript_status(entry: dict[str, Any], base: Path) -> str:
    """ok | mismatch | not_found | no_sha for one transcript entry; the path is
    relative to the answers file."""
    path = base / entry["path"]
    if not path.is_file():
        return "not_found"
    if "sha256" not in entry:
        return "no_sha"
    return "ok" if sha256_file(path) == entry["sha256"] else "mismatch"


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def value_problem(item: dict[str, Any], value: Any) -> str:
    """Why an answer value does not fit the item's kind, or an empty string."""
    kind = item["kind"]
    if kind in DEAL_CHOICES:
        return deal_value_problem(kind, value)
    if kind == "range":
        return range_problem(item, value)
    if kind == "bound":
        return commitment_problem(value)
    options = {o["id"] for o in item.get("options", [])}
    if kind == "choice":
        if not isinstance(value, str):
            return "a choice takes one option id"
        return "" if value in options else f"{value!r} is not an option"
    if kind == "multi":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            return "a multi takes a list of option ids"
        bad = [v for v in value if v not in options]
        return f"{bad} are not options" if bad else ""
    if kind == "number":
        return "" if _number(value) else "a number item takes a number"
    if kind == "text":
        return "" if isinstance(value, str) and value.strip() else "text is empty"
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        return f"a {kind} item takes a list of strings"
    return ""


def check_answers(
    pack: dict[str, Any],
    pack_sha: str,
    ans: dict[str, Any],
    where: str,
    base: Path,
) -> list[Issue]:
    issues = schema_issues(ans, "task_answers", where)
    if issues:
        return issues
    out: list[Issue] = []

    def add(level: str, msg: str) -> None:
        out.append(Issue(level, where, msg))

    if ans["pack"]["id"] != pack["id"]:
        add("error", f"pack id {ans['pack']['id']} is not {pack['id']}")
    if ans["pack"]["version"] != pack["version"]:
        add("error", f"pack version {ans['pack']['version']} is not {pack['version']}")
    if ans["pack"]["sha256"] != pack_sha:
        add(
            "error",
            "pack sha256 differs from the pack file: the answers are for another text",
        )
    if ans["member"] not in member_ids(pack):
        add("error", f"member {ans['member']} is not a member of the pack")
    items = {i["id"]: i for i in pack["items"]}
    for item_id, answer in ans["answers"].items():
        if item_id not in items:
            add("error", f"answers: {item_id} is not an item of the pack")
            continue
        problem = value_problem(items[item_id], answer["value"])
        if problem:
            add("error", f"answers.{item_id}: {problem}")
    terms = {t["id"] for t in pack["term_check"]}
    for tid in ans["term_check"]:
        if tid not in terms:
            add("error", f"term_check: {tid} is not a term check item")
    out.extend(Issue(lv, where, msg) for lv, msg in deal_answers_findings(pack, ans))
    position = member_positions(pack).get(ans["member"])
    for item in pack["items"]:
        if (
            item.get("required", True)
            and not optional_bound(item)
            and in_audience(item, position)
            and item["id"] not in ans["answers"]
        ):
            add("warning", f"required item {item['id']} has no answer")
    for tid in sorted(terms - set(ans["term_check"])):
        add("warning", f"term check {tid} has no answer")
    refs = known_refs(pack)
    for n, point in enumerate(ans.get("added", []), start=1):
        for ref in point.get("refs", []):
            if ref not in refs:
                add("warning", f"added point {n}: ref {ref} names nothing in the pack")
    for entry in ans.get("transcripts", []):
        status = transcript_status(entry, base)
        if status == "mismatch":
            add("error", f"transcript {entry['path']}: sha256 differs from the file")
        elif status == "not_found":
            add(
                "warning",
                f"transcript {entry['path']}: file not found, sha256 not checked",
            )
        elif status == "no_sha":
            add("warning", f"transcript {entry['path']}: no sha256 recorded")
    return out


def check_replies(
    members: list[str],
    rep: dict[str, Any],
    where: str,
    diff: dict[str, Any] | None = None,
    diff_sha: str | None = None,
    view_sha: str | None = None,
) -> list[Issue]:
    """`diff_sha` is the sha256 of the whole diff.yaml. When `diff` is a
    per-position view, `view_sha` is that of the view file and a reply that names
    another view is an error."""
    issues = schema_issues(rep, "task_replies", where)
    if issues:
        return issues
    out: list[Issue] = []

    def add(level: str, msg: str) -> None:
        out.append(Issue(level, where, msg))

    if rep["member"] not in members:
        add("error", f"member {rep['member']} is not a member of the pack")
    points = {p["id"]: p for p in diff["points"]} if diff else {}
    if diff_sha is not None and rep["diff"] != diff_sha:
        add(
            "error",
            "diff sha256 differs from the diff file: the replies are for another diff",
        )
    if view_sha is not None and rep.get("view", view_sha) != view_sha:
        add(
            "error",
            "view sha256 differs from the view file: the replies are for another view",
        )
    for pid, reply in rep["replies"].items():
        if diff and pid not in points:
            add("error", f"replies: {pid} is not a point of the diff")
        point = points.get(pid, {})
        if reply["choice"] == "accept" and point.get("route") == "blocking":
            add("error", f"replies.{pid}: a rejected red line cannot be accepted")
            continue
        if reply["choice"] == "accept" and point.get("class") == "sealed":
            add("error", f"replies.{pid}: a sealed point takes keep or discuss only")
            continue
        other = reply.get("accept_member")
        if other is None:
            continue
        if other not in (diff["members"] if diff else members):
            add("error", f"replies.{pid}: accept_member {other} is not a member")
        elif other == rep["member"]:
            add("error", f"replies.{pid}: a member cannot accept their own answer")
        elif pid in points and other not in points[pid]["answers"]:
            add("error", f"replies.{pid}: {other} gave no answer to accept")
    return out
