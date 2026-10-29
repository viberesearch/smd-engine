"""Schema and structure checks: elements, relations, transitions,
qualifications and the record-level fields of a board set."""

from __future__ import annotations

import re
from typing import Any

from smd_engine.render.text import SCREEN_CHARS
from smd_engine.validate.context import Ctx, Finding, board_set, cite_findings

# The kind tables are profile data (profiles/*.yaml): the board each kind
# normally lives on (`home`; Girenko, day 4 slides: what lies on which board),
# the kinds that need a position they are seen from (`needs_position`: "nothing
# on the boards without a position"), containers, and roles (`role`: actors that
# can occupy a role go in `fillers`).
# Kinds are named by profile attributes where one carries the meaning (a kind
# drawn as a `frame`, a board flagged `object`) and by id where the method
# names the kind itself (position, place_for_others, function, gap): every
# profile defines those (profile.REQUIRED_KINDS).
# Subject-object talk: legitimate where the roles are (the org-activity
# board), false on a board flagged `object` (GP-SMD).
SUBJECT_OBJECT = re.compile(
    r"\b(мы должны|нам нужно|нам надо|наша задача|мы будем|we must|we need to|our task)\b",
    re.IGNORECASE,
)
# Fields of gates Ш9-Ш10 and the kind that takes them, by id: `position` as
# everywhere, `goal` as the kind of the hint goal-without-breakdown
# (profile.HINT_KINDS). `stance` goes to the kinds a profile flags `stance`,
# `vsm_system` to those it flags `vsm`.
KIND_FIELDS = {
    "acts_as": ("position", "positions"),
    "arises_from": ("goal", "goals"),
    "goal_source": ("goal", "goals"),
    "assigned_by": ("goal", "goals"),
    # Beer layer of management-four-boards (gate Бир3 В): the kind the hint
    # line-without-recovery registers (validate/management.py)
    "threshold": ("algedonic_channel", "algedonic channels"),
    "recovery_time": ("algedonic_channel", "algedonic channels"),
}
# What a goal may arise from: a breakdown on the board or in the talk
# (GP-Guide11 ¶43): a gap, a kind flagged `factual`, or such a thesis.
BREAKDOWN_THESES = ("difficulty", "problem")


def _ref_ok(ctx: Ctx, out: list[Finding], ref: str, where: str, what: str) -> bool:
    if ref not in ctx.by_id:
        out.append(Finding("error", where, f"{what} '{ref}' is not an element"))
        return False
    return True


@board_set
def check_elements(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    seen: set[str] = set()
    for el in ctx.record["elements"]:
        if el["id"] in seen:
            out.append(Finding("error", el["id"], "duplicate element id"))
        seen.add(el["id"])
    for el in ctx.record["elements"]:
        _element_findings(ctx, el, out)
    out += _containment_cycles(ctx.by_id)
    return out


def _element_findings(ctx: Ctx, el: dict[str, Any], out: list[Finding]) -> None:
    by_id = ctx.by_id
    profile = ctx.profile
    eid = el["id"]
    kind = el["kind"]
    board = profile.board(el["board"])
    if board.halves and "half" not in el:
        name = board.label["en"].lower()
        out.append(Finding("error", eid, f"an element on the {name} needs 'half'"))
    if not board.halves and "half" in el:
        halved = [b.label["en"].lower() for b in profile.boards if b.halves]
        where = (
            "the " + " or the ".join(halved)
            if halved
            else f"a board with halves, and profile '{profile.id}' has none"
        )
        out.append(Finding("error", eid, f"'half' is only for {where}"))
    elif "half" in el and el["half"] not in board.halves:
        out.append(
            Finding("error", eid, f"board '{board.id}' has no half '{el['half']}'")
        )
    roles = profile.kinds_where("role")
    framed = profile.kinds_shaped("frame")
    if "frame_state" in el and kind not in framed:
        out.append(Finding("error", eid, "'frame_state' is only for frames"))
    for field in ("of", "scheme"):
        if field in el and kind != "gap":
            out.append(Finding("error", eid, f"'{field}' is only for gaps"))
    for field, (only, name) in KIND_FIELDS.items():
        if field in el and kind != only:
            out.append(Finding("error", eid, f"'{field}' is only for {name}"))
    stance = profile.kinds_where("stance")
    if "stance" in el and kind not in stance:
        out.append(
            Finding(
                "error",
                eid,
                "'stance' is only for positions: " + ", ".join(sorted(stance)),
            )
        )
    vsm = profile.kinds_where("vsm")
    if "vsm_system" in el and kind not in vsm:
        out.append(
            Finding(
                "error",
                eid,
                "'vsm_system' is only for "
                + (
                    "kinds: " + ", ".join(sorted(vsm))
                    if vsm
                    else f"kinds a profile flags vsm, and profile '{profile.id}' has none"
                ),
            )
        )
    if "nature" in el and not board.object:
        objects = [b.label["en"].lower() for b in profile.boards if b.object]
        where = (
            "the " + " or the ".join(objects)
            if objects
            else f"an object board, and profile '{profile.id}' has none"
        )
        out.append(Finding("error", eid, f"'nature' is only for {where}"))
    _goal_findings(ctx, el, out)
    if "fillers" in el and kind not in roles:
        out.append(
            Finding(
                "error",
                eid,
                "'fillers' is only for roles: " + ", ".join(sorted(roles)),
            )
        )
    if "detail" in el:
        width = len(el["detail"]["columns"])
        for n, row in enumerate(el["detail"]["rows"], 1):
            if len(row) != width:
                out.append(
                    Finding(
                        "error",
                        eid,
                        f"detail row {n} has {len(row)} cells, not {width}",
                    )
                )
    if "performed_by" in el:
        if kind != "function":
            out.append(Finding("error", eid, "'performed_by' is only for functions"))
        elif _ref_ok(ctx, out, el["performed_by"], eid, "performed_by") and by_id[
            el["performed_by"]
        ]["kind"] not in ("position", "place_for_others"):
            out.append(
                Finding(
                    "error",
                    eid,
                    "performed_by must be a position or a place for others",
                )
            )
    if board.object and SUBJECT_OBJECT.search(el["label"]):
        homes = " or ".join(f"'{b}'" for b in profile.subject_boards)
        name = board.label["en"].lower()
        out.append(
            Finding(
                "warning",
                eid,
                "subject-object talk ('we must', 'our task') "
                + (
                    f"belongs on {homes}, not on the {name}"
                    if homes
                    else f"is not for the {name}"
                ),
            )
        )
    screen = el.get("short", el["label"])
    if len(" ".join(screen.split())) > SCREEN_CHARS:
        what = "short" if "short" in el else "label"
        out.append(
            Finding(
                "warning",
                eid,
                f"{what} is cut on the screen after {SCREEN_CHARS} characters; "
                + ("shorten it" if "short" in el else "add 'short'"),
            )
        )
    home = profile.kind(kind).home
    # on a record's board the template's kinds are its own (checked with the
    # profile's boards); elsewhere a kind is warned off its home
    if home and not board.template and el["board"] != home:
        where = (
            f"a board of template '{home}'"
            if profile.template(home)
            else f"board '{home}'"
        )
        out.append(Finding("warning", eid, f"{kind} usually lies on {where}"))
    if "seen_from" in el:
        if _ref_ok(ctx, out, el["seen_from"], eid, "seen_from"):
            if by_id[el["seen_from"]]["kind"] != "position":
                out.append(Finding("error", eid, "seen_from must be a position"))
    elif profile.kind(kind).needs_position:
        out.append(Finding("warning", eid, "no position it is seen from"))
    containers = profile.kinds_where("container")
    for container in el.get("in", []):
        if _ref_ok(ctx, out, container, eid, "container"):
            if kind in framed and by_id[container]["kind"] in framed:
                out.append(
                    Finding("warning", eid, "a frame inside a frame is drawn beside it")
                )
            if by_id[container]["kind"] not in containers:
                out.append(
                    Finding(
                        "warning",
                        eid,
                        f"container '{container}' is a {by_id[container]['kind']}",
                    )
                )
    move = el.get("move")
    if move:
        for src in move["from"]:
            _ref_ok(ctx, out, src, eid, "move source")
        if eid in move["from"]:
            out.append(Finding("error", eid, "a move cannot start from its result"))
    out += cite_findings(el.get("cites", []), eid, ctx.source_ids)


@board_set
def check_record_boards(ctx: Ctx) -> list[Finding]:
    """The boards a record makes of its profile's templates: an id apart from
    the element ids, the position it is seen from (`seen_from`; a warning
    when the template asks for one and it is missing), what it unfolds (of
    a kind among the template's `unfolds`, when it lists any)."""
    out: list[Finding] = []
    for raw in ctx.record.get("boards", []):
        where = f"board {raw['id']}"
        if raw["id"] in ctx.by_id:
            out.append(Finding("error", where, "board id is also an element id"))
        template = ctx.profile.template(raw["template"])
        if "seen_from" in raw:
            if _ref_ok(ctx, out, raw["seen_from"], where, "seen_from"):
                if ctx.by_id[raw["seen_from"]]["kind"] != "position":
                    out.append(Finding("error", where, "seen_from must be a position"))
        elif template and template.needs_position:
            out.append(Finding("warning", where, "no position it is seen from"))
        if "unfolds" in raw and _ref_ok(ctx, out, raw["unfolds"], where, "unfolds"):
            kind = ctx.by_id[raw["unfolds"]]["kind"]
            if template and template.unfolds and kind not in template.unfolds:
                out.append(
                    Finding(
                        "error",
                        where,
                        f"unfolds '{raw['unfolds']}', a {kind}; a board of template "
                        f"'{template.id}' unfolds {', '.join(template.unfolds)}",
                    )
                )
        out += cite_findings(raw.get("cites", []), where, ctx.source_ids)
    return out


def _goal_findings(ctx: Ctx, el: dict[str, Any], out: list[Finding]) -> None:
    """The links of a goal: what it arises from, who assigned it (gate Ш9)."""
    eid = el["id"]
    for ref in el.get("arises_from", []):
        if ref in ctx.theses:
            thesis = ctx.theses[ref]
            ok = thesis["kind"] in BREAKDOWN_THESES or thesis.get("modality") == "fact"
        elif ref in ctx.by_id:
            source = ctx.by_id[ref]
            ok = (
                source["kind"] == "gap"
                or source["kind"] in ctx.profile.kinds_where("factual")
                or source.get("modality") == "fact"
            )
        else:
            out.append(
                Finding(
                    "error", eid, f"arises_from '{ref}' is not an element or thesis"
                )
            )
            continue
        if not ok:
            out.append(
                Finding(
                    "error",
                    eid,
                    f"arises_from '{ref}': a gap, a fact, or a difficulty, "
                    "problem or factual thesis",
                )
            )
    if "assigned_by" in el and _ref_ok(ctx, out, el["assigned_by"], eid, "assigned_by"):
        if ctx.by_id[el["assigned_by"]]["kind"] not in ("position", "place_for_others"):
            out.append(
                Finding(
                    "error",
                    eid,
                    "assigned_by must be a position or a place for others",
                )
            )


def _containment_cycles(by_id: dict[str, dict[str, Any]]) -> list[Finding]:
    out: list[Finding] = []
    for start in by_id:
        seen: set[str] = set()
        stack = list(by_id[start].get("in", []))
        while stack:
            cur = stack.pop()
            if cur == start:
                out.append(Finding("error", start, "containment cycle through 'in'"))
                break
            if cur in seen or cur not in by_id:
                continue
            seen.add(cur)
            stack.extend(by_id[cur].get("in", []))
    return out


@board_set
def check_relations(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    by_id = ctx.by_id
    for rel in ctx.record.get("relations", []):
        where = f"relation {rel['from']}->{rel['to']}"
        ok = _ref_ok(ctx, out, rel["from"], where, "from") & _ref_ok(
            ctx, out, rel["to"], where, "to"
        )
        if ok and rel["kind"] == "shift":
            if {by_id[rel["from"]]["kind"], by_id[rel["to"]]["kind"]} != {"position"}:
                out.append(Finding("warning", where, "a shift links two positions"))
        if ok and rel["kind"] == "represents":
            if by_id[rel["from"]]["kind"] != "position":
                out.append(Finding("warning", where, "represents goes from a position"))
        out += cite_findings(rel.get("cites", []), where, ctx.source_ids)
    return out


@board_set
def check_transitions(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    by_id = ctx.by_id
    transitions = ctx.record.get("transitions", [])
    numbers = [t["n"] for t in transitions]
    if sorted(numbers) != list(range(1, len(numbers) + 1)):
        out.append(
            Finding("error", "transitions", f"numbers must run 1..n, got {numbers}")
        )
    for tr in transitions:
        where = f"transition {tr['n']}"
        if _ref_ok(ctx, out, tr["from"], where, "from") & _ref_ok(
            ctx, out, tr["to"], where, "to"
        ):
            if by_id[tr["from"]]["board"] == by_id[tr["to"]]["board"] and (
                by_id[tr["from"]].get("half") == by_id[tr["to"]].get("half")
            ):
                out.append(
                    Finding(
                        "warning",
                        where,
                        "a transition moves between boards; "
                        "within one board use a relation",
                    )
                )
        out += cite_findings(tr.get("cites", []), where, ctx.source_ids)
    return out


@board_set
def check_qualifications(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    data = ctx.record
    seen_k: set[str] = set()
    for q in data.get("qualifications", []):
        if q["id"] in seen_k:
            out.append(Finding("error", q["id"], "duplicate qualification id"))
        seen_k.add(q["id"])
        for t in q.get("targets", []):
            _ref_ok(ctx, out, t, q["id"], "target")
        if q["status"] == "closed" and "closed_in" not in q:
            out.append(
                Finding("error", q["id"], "closed qualification needs closed_in")
            )
        if "closed_in" in q and q["status"] != "closed":
            out.append(
                Finding("warning", q["id"], "closed_in set but status is not closed")
            )
        if q.get("closed_in", 10**6) < q.get("raised_in", 0):
            out.append(Finding("error", q["id"], "closed before it was raised"))
        if q.get("raised_in", 0) > data["cycle"]:
            out.append(
                Finding("error", q["id"], "raised in a later cycle than this record")
            )
        out += cite_findings(q.get("cites", []), q["id"], ctx.source_ids)
    return out


@board_set
def check_record_level(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    data = ctx.record
    if data.get("revises") == data["id"]:
        out.append(Finding("error", "revises", "a record cannot revise itself"))
    if data["cycle"] == 1 and "revises" in data:
        out.append(Finding("warning", "revises", "cycle 1 normally revises nothing"))
    if data["status"] == "verified" and not data.get("checked_by"):
        out.append(Finding("error", "status", "verified needs checked_by"))
    for sid in data.get("sources", []):
        if ctx.source_ids is not None and sid not in ctx.source_ids:
            out.append(Finding("error", "sources", f"unknown source '{sid}'"))

    if "reflected_from" in data:
        if _ref_ok(ctx, out, data["reflected_from"], "reflected_from", "position"):
            reflexive = ctx.by_id[data["reflected_from"]]
            if reflexive["kind"] != "position":
                out.append(
                    Finding(
                        "error", "reflected_from", "reflected_from must be a position"
                    )
                )
            elif reflexive.get("stance") == "inside":
                out.append(
                    Finding(
                        "warning",
                        "reflected_from",
                        f"'{reflexive['id']}' has stance inside: the reflexive exit "
                        "is made from outside the place one acts in (GP-Guide11 ¶35)",
                    )
                )
    elif "revises" in data:
        out.append(
            Finding(
                "warning",
                "reflected_from",
                "a new cycle names the reflexive position it was made from",
            )
        )
    return out
