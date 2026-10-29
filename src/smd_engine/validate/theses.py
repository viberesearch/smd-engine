"""Thesis cards: ids, links to the board, voice against status, anchoring."""

from __future__ import annotations

from smd_engine.validate.context import Ctx, Finding, board_set, cite_findings

# Voices that fit each SessionFlow status label; "refined" and "open" fit any voice.
STATUS_VOICES = {
    "voiced": {"group", "participant"},
    "assumption": {"group", "participant"},
    "proposal": {"moderator", "expert", "organisers"},
    "ai_variant": {"ai"},
}


@board_set
def check_thesis_raises(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for t in ctx.theses.values():
        for k in t.get("raises", []):
            if k not in ctx.ks:
                out.append(
                    Finding("error", t["id"], f"raises '{k}', not a qualification")
                )
    return out


@board_set
def check_theses(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    theses = ctx.record.get("theses", [])
    by_id = ctx.by_id
    ids = {t["id"] for t in theses}
    seen: set[str] = set()
    for t in theses:
        tid = t["id"]
        if tid in seen:
            out.append(Finding("error", tid, "duplicate thesis id"))
        seen.add(tid)
        for field in ("feeds", "about"):
            for ref in t.get(field, []):
                if ref not in by_id:
                    out.append(
                        Finding("error", tid, f"{field} '{ref}', not an element")
                    )
        move = t.get("move")
        if move:
            for src in move["from"]:
                if src not in by_id and src not in ids:
                    out.append(
                        Finding(
                            "error",
                            tid,
                            f"move source '{src}' is not an element or thesis",
                        )
                    )
            if tid in move["from"]:
                out.append(Finding("error", tid, "a move cannot start from its result"))
        if "scheme" in t and t["kind"] != "problem":
            out.append(Finding("error", tid, "'scheme' is only for problem theses"))
        fits = STATUS_VOICES.get(t["status"])
        if fits and t["voice"] not in fits:
            out.append(
                Finding(
                    "error",
                    tid,
                    f"status '{t['status']}' does not fit voice '{t['voice']}'",
                )
            )
        if not t.get("cites") and t["voice"] != "ai":
            out.append(Finding("warning", tid, "thesis has no source address"))
        out += cite_findings(t.get("cites", []), tid, ctx.source_ids)
    return out
