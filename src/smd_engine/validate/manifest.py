"""Source manifests: ids, locators, clean-room decisions."""

from __future__ import annotations

from smd_engine.validate.context import Ctx, Finding


def check_manifest(ctx: Ctx) -> list[Finding]:
    if ctx.record["record"] != "source_manifest":
        return []
    out: list[Finding] = []
    seen: set[str] = set()
    for src in ctx.record["sources"]:
        if src["id"] in seen:
            out.append(Finding("error", src["id"], "duplicate source id"))
        seen.add(src["id"])
        if not src.get("file") and not src.get("url"):
            out.append(Finding("warning", src["id"], "neither file nor url given"))
        if "clean_room" not in src:
            out.append(Finding("warning", src["id"], "clean_room not decided"))
        if src.get("personal_data") and src.get("clean_room") == "allow":
            out.append(
                Finding(
                    "hint",
                    src["id"],
                    "personal data: pass to a clean room "
                    "only with names replaced by positions",
                )
            )
    return out
