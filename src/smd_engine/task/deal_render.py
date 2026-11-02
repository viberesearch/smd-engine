"""The deal fields on the task pages: positions, audience, the alpha basis. Every
function returns nothing for a pack or a point without the deal fields, so a
group page is unchanged."""

from __future__ import annotations

from typing import Any

from smd_engine.render.text import line_text
from smd_engine.task.deal_items import DEAL_CHOICES
from smd_engine.task.deal_labels import DEAL_LABELS
from smd_engine.task.diff import is_open
from smd_engine.task.labels import LABELS, class_word
from smd_engine.task.names import Names


def point_open(p: dict[str, Any]) -> bool:
    """Whether a diff point waits for replies. A value point of a per-position
    view has no route, only the class `open` or `settled`."""
    return is_open(p["route"]) if "route" in p else bool(p["class"] == "open")


def _kind_word(lang: str, kind: str) -> str:
    return str(DEAL_LABELS[lang]["position_kinds"].get(kind, kind))


def member_line(pack: dict[str, Any]) -> str:
    """The member names of a pack; a deal pack adds each member's position."""
    labels = {p["id"]: p["label"] for p in pack.get("positions", [])}
    return ", ".join(
        (
            f"{m['name']} ({labels[m['position']]})"
            if m.get("position") in labels
            else m["name"]
        )
        for m in pack["members"]
    )


def positions_block(
    pack: dict[str, Any],
) -> tuple[str, list[str], list[list[str]]] | None:
    """(heading, column heads, rows) of the positions table, or None."""
    if not pack.get("positions"):
        return None
    lang = pack["lang"]
    lab = DEAL_LABELS[lang]
    rows = [[p["label"], _kind_word(lang, p["kind"])] for p in pack["positions"]]
    return lab["positions"], [lab["position"], LABELS[lang]["kind"]], rows


def point_meta(p: dict[str, Any], nm: Names, lang: str) -> list[str]:
    """Extra "label: value" lines of a diff point that carries deal fields."""
    lab = DEAL_LABELS[lang]
    out: list[str] = []
    if p.get("nature"):
        out.append(f"{lab['nature']}: {lab['natures'][p['nature']]}")
    if p.get("claim"):
        out.append(f"{lab['claim']}: {p['claim']['text']}")
    if p.get("line"):
        out.append(f"{lab['red_line']}: {line_text(p['line'], lang)}")
    if p.get("sealed"):
        out.append(f"{lab['sealed_what']}: {_sealed_text(p['sealed'], lab)}")
        out.append(f"{lab['committed_by']}: {nm.members(p['committed_by']) or '-'}")
    if p.get("changed_since_run"):
        out.append(f"{lab['changed_since_run']}: {nm.members(p['changed_since_run'])}")
    if p.get("ledger_head"):
        out.append(f"{lab['ledger']}: {p['ledger_head'][:12]}")
    if p.get("after_reading"):
        out.append(
            f"{lab['after_reading']}: {nm.heading({'id': p['after_reading'], 'kind': 'item'})[0]}"
        )
    if p.get("audience"):
        names = nm.labels.get("positions", {})
        out.append(
            f"{lab['audience']}: " + ", ".join(names.get(a, a) for a in p["audience"])
        )
    return out


def _sealed_text(sealed: dict[str, Any], lab: dict[str, Any]) -> str:
    """ "the seller's floor, EUR, stage full-map": a bound without its number."""
    parts = [lab["sealed_side"][sealed["side"]], sealed["unit"]]
    if sealed.get("stage"):
        parts.append(f"{lab['stage']} {sealed['stage']}")
    return ", ".join(parts)


def model_note(diff: dict[str, Any]) -> str:
    """One sentence on whether a model may read the answers, or an empty string
    for a diff of a pack with no `deal` block."""
    if "model_pass_allowed" not in diff:
        return ""
    lab = DEAL_LABELS[diff["lang"]]
    word = lab[
        "model_pass_allowed" if diff["model_pass_allowed"] else "model_pass_stopped"
    ]
    return f"{lab['model_pass']}: {word}"


def alpha_note(diff: dict[str, Any]) -> str:
    """One sentence on what alpha was computed on, or an empty string."""
    basis = diff["alpha"].get("basis")
    if not basis:
        return ""
    return str(DEAL_LABELS[diff["lang"]]["alpha_basis"]).format(
        n=basis["items"], m=basis["of"]
    )


def with_options(item: dict[str, Any], lang: str) -> dict[str, Any]:
    """A fact or line item with the answers it takes as `options`, so the pages
    draw it like a choice; any other item as it is."""
    if item["kind"] not in DEAL_CHOICES:
        return item
    words = DEAL_LABELS[lang]["choices"]
    return {
        **item,
        "options": [{"id": v, "label": words[v]} for v in DEAL_CHOICES[item["kind"]]],
    }


def item_facts(pack: dict[str, Any], item: dict[str, Any]) -> list[tuple[str, str]]:
    """(label, text) pairs a member reads before answering a fact, line or range item."""
    lang = pack["lang"]
    lab = DEAL_LABELS[lang]
    out: list[tuple[str, str]] = []
    claim = item.get("claim")
    if claim:
        who = {p["id"]: p["label"] for p in pack.get("positions", [])}
        who.update({m["id"]: m["name"] for m in pack["members"]})
        src = next(s for s in pack["sources"] if s["id"] == claim["source"])
        shown = src.get("note") or src["address"]
        if src.get("date"):
            shown += f" ({src['date']})"
        out += [
            (lab["claim"], claim["text"]),
            (lab["asserted_by"], who.get(claim["asserted_by"], claim["asserted_by"])),
            (lab["source"], shown),
            (lab["level"], lab["levels"][claim["level"]]),
        ]
    if item.get("stage"):
        out.append((lab["stage"], item["stage"]))
    if item.get("unit"):
        out.append((lab["unit"], item["unit"]))
    if item.get("bound"):
        out.append((lab["sealed_what"], _sealed_text(item["bound"], lab)))
        if pack.get("holder"):
            out.append((lab["holder"], pack["holder"]["name"]))
        out.append((lab["give"], lab["sealed_how"]))
    if item.get("line"):
        out += [
            (lab["red_line"], line_text(item["line"], lang)),
            (lab["if_reject"], lab["if_reject_text"]),
        ]
    return out


def sources_table(pack: dict[str, Any]) -> tuple[list[str], list[list[str]]]:
    """(column heads, rows) of the sources: id, address, note, and sha256 and
    date when a source has them."""
    lab = LABELS[pack["lang"]]
    extra = [k for k in ("sha256", "date") if any(k in s for s in pack["sources"])]
    head = [lab["id"], lab["address"], lab["note"]] + [
        DEAL_LABELS[pack["lang"]]["sha256"] if k == "sha256" else lab["date"]
        for k in extra
    ]
    rows = [
        [s["id"], s["address"], s.get("note", "")]
        + [s.get(k, "")[:12] if k == "sha256" else s.get(k, "") for k in extra]
        for s in pack["sources"]
    ]
    return head, rows


def why_lines(p: dict[str, Any], lang: str) -> list[str]:
    """Extra reasons an agenda entry is on the call."""
    return [DEAL_LABELS[lang]["blocking_why"]] if p["why"].get("blocking") else []


def has_fact(pack: dict[str, Any]) -> bool:
    """Whether the page needs the deal script for source ids."""
    return any(i["kind"] == "fact" for i in pack["items"])


def pair_title(pair: dict[str, Any], nm: Names) -> str:
    """The label of a pair, or its two members' names."""
    return str(pair.get("label") or " - ".join(nm.member(m) for m in pair["members"]))


def pair_block(
    diff: dict[str, Any], nm: Names, lang: str
) -> tuple[str, list[str], list[list[str]]] | None:
    """(heading, column heads, rows) of the pairs table of a diff, or None."""
    if not diff.get("by_pair"):
        return None
    lab = DEAL_LABELS[lang]
    rows = [
        [
            pair_title(pair, nm),
            str(pair["summary"]["points"]),
            str(pair["summary"]["open"]),
            ", ".join(
                f"{class_word(lang, {'class': c})}: {n}"
                for c, n in pair["summary"]["by_class"].items()
            ),
        ]
        for pair in diff["by_pair"]
    ]
    head = [
        lab["pair"],
        LABELS[lang]["points"],
        lab["pair_open"],
        LABELS[lang]["class"],
    ]
    return lab["by_pair"], head, rows


def view_note(
    diff: dict[str, Any], nm: Names, lang: str, key: str = "view_note"
) -> str:
    """One sentence on what a per-position view (or, with `agenda_view_note`, a
    per-position agenda) leaves out, or an empty string."""
    view = diff.get("view")
    if not view:
        return ""
    names = nm.labels.get("positions", {})
    return str(DEAL_LABELS[lang][key]).format(
        p=names.get(view["position"], view["position"])
    )
