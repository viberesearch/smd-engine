"""AI on the boards (gate ИИ1 Б, the case owner 31.10.2026): AI is an actor, not a
new kind of flow. A role (a kind the profile flags `role`) or a function says
how AI takes part in it with `ai`: `assists` (people do the work with AI help)
or `performs` (AI does the work); the actor itself goes in `fillers`
(docs/method/roles-and-actors.md).

A function's effective `ai` is its own `ai`, else the `ai` of the role in its
`performed_by`. The hint `ai-decision-unanswered` names a function AI
performs that is linked to a red line while no role without `ai: performs`
answers for it: a decision that cannot be passed on without people of a
certain role (the MIPT case's H64). Which elements are red lines, and what
an element is linked to, is in validate/redlines.py."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, hint
from smd_engine.validate.redlines import red_lines

# Relations by which a role answers for a function: the role above it
# (`subordinates`, role to function), the function's signal going up to it
# (`escalates`, function to role), or what the function gives back to it as
# information (`flow` with `carries: information`, function to role).
ANSWER_FROM_ROLE = ("subordinates",)
ANSWER_TO_ROLE = ("escalates",)


def effective_ai(el: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str | None:
    """`assists`, `performs` or None: the element's own `ai`; for a function
    without one, the `ai` of the role in its `performed_by`."""
    if "ai" in el:
        return str(el["ai"])
    if el["kind"] == "function" and el.get("performed_by") in by_id:
        found = by_id[el["performed_by"]].get("ai")
        return str(found) if found else None
    return None


def ai_share(data: dict[str, Any]) -> tuple[int, int, int] | None:
    """The functions AI performs, those it assists, and all functions, by the
    effective `ai`; None when no element of the record has `ai`."""
    elements = data.get("elements", [])
    if not any("ai" in e for e in elements):
        return None
    by_id = {e["id"]: e for e in elements}
    found = [effective_ai(e, by_id) for e in elements if e["kind"] == "function"]
    return found.count("performs"), found.count("assists"), len(found)


def _answers(ctx: Ctx, fn: dict[str, Any]) -> bool:
    """Whether a role without `ai: performs` (a gap, a missing role, does not
    answer) is linked to the function by `performed_by`, `subordinates` from
    it, `escalates` to it, or a `flow` of information to it."""
    roles = ctx.profile.kinds_where("role") - {"gap"}

    def human(el_id: str | None) -> bool:
        el = ctx.by_id.get(el_id or "")
        return el is not None and el["kind"] in roles and el.get("ai") != "performs"

    if human(fn.get("performed_by")):
        return True
    for rel in ctx.record.get("relations", []):
        kind = rel["kind"]
        if kind in ANSWER_FROM_ROLE and rel["to"] == fn["id"] and human(rel["from"]):
            return True
        if rel["from"] != fn["id"] or not human(rel["to"]):
            continue
        if kind in ANSWER_TO_ROLE or (
            kind == "flow" and rel.get("carries") == "information"
        ):
            return True
    return False


@hint("ai-decision-unanswered")
def hint_ai_decision_unanswered(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for fn in ctx.by_id.values():
        if fn["kind"] != "function" or effective_ai(fn, ctx.by_id) != "performs":
            continue
        lines = red_lines(ctx, fn["id"])
        if lines and not _answers(ctx, fn):
            out.append(
                Finding(
                    "hint",
                    fn["id"],
                    "AI performs this function at a red line ("
                    + ", ".join(lines)
                    + ") and no role without 'ai: performs' answers for it "
                    "(performed_by, subordinates, escalates or an information "
                    "flow back): which role decides at the line?",
                )
            )
    return out
