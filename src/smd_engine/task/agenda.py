"""`smd task agenda`: the points for the call, from the diff and the replies.

A point goes to the call when at least one member chose discuss, or when it is
open (its route waits for the members) and a member did not reply to it; a
missing reply counts as discuss. Every other point is settled before the call.
"""

from __future__ import annotations

from typing import Any

from smd_engine.deal.views import is_value_point
from smd_engine.records import RecordError
from smd_engine.task.diff import is_open
from smd_engine.task.pairs import call_by_pair


def expected_repliers(
    point: dict[str, Any], members: list[str], positions: dict[str, str] | None = None
) -> list[str]:
    """Who must reply to an open point: everyone, except the member who raised
    a point that only they answered. A point for some positions (`audience`) is
    replied to by the members of those positions only."""
    raised = point.get("raised_by")
    audience = point.get("audience")
    return [
        m
        for m in members
        if m != raised and (audience is None or (positions or {}).get(m) in audience)
    ]


def _reply_text(reply: dict[str, Any]) -> str:
    if reply["choice"] == "accept":
        return f"accept {reply['accept_member']}"
    return str(reply["choice"])


def build_agenda(
    diff: dict[str, Any],
    diff_sha: str,
    replies: list[dict[str, Any]],
    members: list[str],
) -> dict[str, Any]:
    if diff.get("view"):
        raise RecordError(
            "the diff is a per-position view: build the agenda from the whole diff.yaml"
        )
    unknown = [m for m in members if m not in diff["members"]]
    if unknown:
        raise RecordError(f"--members: {', '.join(unknown)} not in the diff's members")
    by_member: dict[str, dict[str, Any]] = {}
    for rep in replies:
        if rep["diff"] != diff_sha:
            raise RecordError(
                f"replies of {rep['member']}: diff sha256 differs from the diff file"
            )
        if rep["member"] not in members:
            raise RecordError(f"replies of {rep['member']}: not among --members")
        if rep["member"] in by_member:
            raise RecordError(f"two replies files of {rep['member']}")
        by_member[rep["member"]] = rep["replies"]
    call: list[dict[str, Any]] = []
    settled: list[dict[str, Any]] = []
    for p in diff["points"]:
        got = {m: r[p["id"]] for m, r in by_member.items() if p["id"] in r}
        discuss = [m for m, r in got.items() if r["choice"] == "discuss"]
        open_point = is_open(p["route"])
        missing = (
            [
                m
                for m in expected_repliers(p, members, diff.get("positions"))
                if m not in got
            ]
            if open_point
            else []
        )
        base = {
            "id": p["id"],
            "kind": p["kind"],
            "class": p["class"],
            "class_by": p["class_by"],
            "route": p["route"],
        }
        for key in (
            "subtype",
            "section",
            "question",
            "term",
            "text",
            "item_kind",
            "audience",
            "after_reading",
            "claim",
            "line",
            "refs",
            "raised_by",
            "sealed",
            "committed_by",
            "changed_since_run",
            "verdict",
            "ledger_head",
        ):
            if p.get(key):
                base[key] = p[key]
        blocking = p["route"] == "blocking"
        if discuss or missing or blocking:
            why: dict[str, Any] = {}
            if blocking:
                why["blocking"] = True
            if discuss:
                why["discuss"] = discuss
            if missing:
                why["no_reply"] = missing
            entry = {**base, "why": why}
            if diff.get("positions") and (p.get("audience") or is_value_point(p)):
                # as in the views: a point for some positions or a value point
                # shows no answers and no notes to a reader of the agenda
                entry["answers_withheld"] = True
            else:
                entry["answers"] = p["answers"]
                notes = {m: r["note"] for m, r in got.items() if r.get("note")}
                if notes:
                    entry["notes"] = notes
            call.append(entry)
            continue
        entry = {**base, "how": "replies" if open_point else p["route"]}
        if got:
            entry["replies"] = {m: _reply_text(r) for m, r in got.items()}
        settled.append(entry)
    return {
        "record": "task_agenda",
        "schema_version": "0.1",
        "title": diff.get("title", diff["pack"]["id"]),
        "lang": diff["lang"],
        "pack": diff["pack"],
        "diff": diff_sha,
        "members": members,
        "replied": [m for m in members if m in by_member],
        "not_replied": [m for m in members if m not in by_member],
        "counts": {
            "points": len(diff["points"]),
            "call": len(call),
            "settled": len(settled),
        },
        **({"asking_price": diff["asking_price"]} if diff.get("asking_price") else {}),
        "call": call,
        **({"call_by_pair": call_by_pair(diff, call)} if diff.get("by_pair") else {}),
        "settled": settled,
        **({"labels": diff["labels"]} if diff.get("labels") else {}),
    }
