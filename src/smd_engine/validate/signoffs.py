"""Human sign-off points (Schukin's interface tax).

Each sign-off states its function and must change something; each state
change that a human must license has a sign-off.
"""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, board_set, is_ai

# What a sign-off licenses: the states its target may be in once signed.
SIGNOFF_EFFECT = {
    "close_k": {"closed"},
    "partly_k": {"partly"},
    "reopen_k": {"open"},
    "accept_move": {"accepted"},
    "reject_move": {"rejected"},
    "accept_thesis": {"refined"},
    "accept_result": {"confirmed", "refuted"},
    "verify_record": {"verified"},
}
# Sign-offs on one target that supersede each other: only the latest licenses a state.
SIGNOFF_FAMILY = {
    "close_k": "k",
    "partly_k": "k",
    "reopen_k": "k",
    "accept_move": "move",
    "reject_move": "move",
}


@board_set
def check_signoffs(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    data = ctx.record
    ks, hyps, theses = ctx.ks, ctx.hyps, ctx.theses
    moved = {**ctx.by_id, **theses}
    # function -> (targets it may sign, what they are called)
    pools: dict[str, tuple[dict[str, dict[str, Any]], str]] = {
        "close_k": (ks, "a qualification"),
        "partly_k": (ks, "a qualification"),
        "reopen_k": (ks, "a qualification"),
        "accept_thesis": (theses, "a thesis"),
        "accept_result": (hyps, "a hypothesis"),
    }
    signed: set[tuple[str, str | None]] = set()
    signoffs = data.get("signoffs", [])
    latest = {
        (SIGNOFF_FAMILY[s["function"]], s.get("target")): i
        for i, s in enumerate(signoffs)
        if s["function"] in SIGNOFF_FAMILY
    }
    for i, s in enumerate(signoffs):
        fn, target = s["function"], s.get("target")
        where = f"signoff {i + 1} ({fn})"
        signed.add((fn, target))
        if is_ai(s["by"]):
            out.append(Finding("error", where, "a sign-off is a human point, not AI"))
        if fn == "verify_record":
            if target is not None:
                out.append(Finding("error", where, "verify_record takes no target"))
                continue
            state = data["status"]
        elif target is None:
            out.append(Finding("error", where, "needs a target"))
            continue
        elif fn in pools:
            pool, name = pools[fn]
            if target not in pool:
                out.append(Finding("error", where, f"'{target}' is not {name}"))
                continue
            state = pool[target]["status"]
        else:
            if "move" not in moved.get(target, {}):
                out.append(Finding("error", where, f"'{target}' carries no move"))
                continue
            state = moved[target]["move"].get("status", "candidate")
        family = SIGNOFF_FAMILY.get(fn)
        superseded = family is not None and latest[(family, target)] != i
        if state not in SIGNOFF_EFFECT[fn] and not superseded:
            wanted = " or ".join(f"'{w}'" for w in sorted(SIGNOFF_EFFECT[fn]))
            out.append(
                Finding(
                    "warning",
                    where,
                    f"changes nothing: the target is '{state}', not {wanted}",
                )
            )

    for q in ks.values():
        if q["status"] == "closed" and ("close_k", q["id"]) not in signed:
            out.append(Finding("warning", q["id"], "closed without a human sign-off"))
    for item_id, item in moved.items():
        move = item.get("move", {})
        if move.get("status") != "accepted" or ("accept_move", item_id) in signed:
            continue
        if is_ai(item.get("voice")):
            out.append(
                Finding(
                    "error",
                    item_id,
                    "a move from an AI voice stays a candidate until a human accepts it",
                )
            )
        elif not item.get("cites"):
            out.append(
                Finding(
                    "warning",
                    item_id,
                    "accepted move with neither a source nor a sign-off",
                )
            )
    for t in theses.values():
        if t["status"] == "refined" and ("accept_thesis", t["id"]) not in signed:
            out.append(Finding("warning", t["id"], "refined without a group sign-off"))
    for h in hyps.values():
        if (
            h["status"] in SIGNOFF_EFFECT["accept_result"]
            and (
                "accept_result",
                h["id"],
            )
            not in signed
        ):
            out.append(Finding("warning", h["id"], "result without a human sign-off"))
    if data["status"] == "verified" and ("verify_record", None) not in signed:
        out.append(Finding("warning", "status", "verified without a sign-off"))
    return out
