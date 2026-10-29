"""Hypotheses: links, and a result only on a field artefact."""

from __future__ import annotations

from smd_engine.validate.context import Ctx, Finding, board_set, cite_findings


@board_set
def check_hypotheses(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    data = ctx.record
    seen: set[str] = set()
    for h in data.get("hypotheses", []):
        hid = h["id"]
        if hid in seen:
            out.append(Finding("error", hid, "duplicate hypothesis id"))
        seen.add(hid)
        for ref in h.get("targets", []):
            if ref not in ctx.by_id:
                out.append(Finding("error", hid, f"target '{ref}' is not an element"))
        for k in h.get("qualifications", []):
            if k not in ctx.ks:
                out.append(Finding("error", hid, f"'{k}' is not a qualification"))
        if h["status"] in ("confirmed", "refuted"):
            if not h.get("artefacts"):
                out.append(
                    Finding(
                        "error", hid, "a result needs the field artefact it rests on"
                    )
                )
            if not h.get("result"):
                out.append(Finding("error", hid, "a result needs its text in 'result'"))
            if "resolved_in" not in h:
                out.append(Finding("error", hid, "a result needs resolved_in"))
        elif "resolved_in" in h:
            out.append(
                Finding("warning", hid, "resolved_in set but no result was recorded")
            )
        if h["status"] == "testing" and not h.get("action"):
            out.append(Finding("warning", hid, "testing, but no action is named"))
        if h.get("raised_in", 0) > data["cycle"]:
            out.append(
                Finding("error", hid, "raised in a later cycle than this record")
            )
        if h.get("resolved_in", 10**6) < h.get("raised_in", 0):
            out.append(Finding("error", hid, "resolved before it was raised"))
        out += cite_findings(h.get("artefacts", []), hid, ctx.source_ids)
        out += cite_findings(h.get("cites", []), hid, ctx.source_ids)
    return out
