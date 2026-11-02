"""The page script of a deal pack: the group script with the replacements below,
so the group pages stay byte for byte as they were. A replacement that finds
nothing to replace raises, so a change to `assets/task.js` cannot silently drop
a deal feature."""

from __future__ import annotations

from typing import Any

from smd_engine.render.text import esc
from smd_engine.task.web import asset_text

# (old text of assets/task.js, new text)
PATCHES = [
    (
        "', sha256: ' + q(P.sha256) + '}');",
        "', sha256: ' + q(P.sha256) + (P.annex ? ', annex: {position: ' + "
        "q(P.annex.position) + ', sha256: ' + q(P.annex.sha256) + '}' : '') + '}');",
    ),
    (
        "if (conf) { L.push('    confidence: ' + q(conf)); }",
        "if (conf) { L.push('    confidence: ' + q(conf)); }\n"
        "        var sids = checked('si:' + it.id);\n"
        "        if (sids.length) { L.push('    source_ids: ' + flow(sids)); }",
    ),
]

# applied only to a pack with a range item: the answer of a range is an object
RANGE_PATCHES = [
    (
        "    var raw = field(k).trim();\n",
        "    if (it.kind === 'range') {\n"
        "      var lo = field(k + ':min').trim().replace(',', '.'), hi = field(k + ':max').trim().replace(',', '.');\n"
        "      if (!lo || !hi || isNaN(Number(lo)) || isNaN(Number(hi))) { return null; }\n"
        "      var span = { min: Number(lo), max: Number(hi) };\n"
        "      if (field(k + ':date').trim()) { span.date = field(k + ':date').trim(); }\n"
        "      return span;\n"
        "    }\n"
        "    var raw = field(k).trim();\n",
    ),
    (
        "(Array.isArray(v) ? flow(v) : typeof v === 'number' ? String(v) : q(v))",
        "(Array.isArray(v) ? flow(v) : typeof v === 'object' ? '{min: ' + v.min + ', max: ' + v.max + "
        "', unit: ' + q(it.unit) + (v.date ? ', date: ' + q(v.date) : '') + '}' : "
        "typeof v === 'number' ? String(v) : q(v))",
    ),
]


def range_input(item: dict[str, Any], lab: dict[str, Any]) -> str:
    """The fields of a range item: from, to, the item's unit, an optional date."""
    key = f"v:{item['id']}"

    def num(part: str, label: str) -> str:
        return (
            f'<label class="f">{esc(label)}'
            f'<input type="number" step="any" data-s="{esc(key)}:{part}"></label>'
        )

    return (
        num("min", lab["range_from"])
        + num("max", lab["range_to"])
        + f'<p class="meta"><b>{esc(item["unit"])}</b></p>'
        + f'<label class="f">{esc(lab["range_date"])}'
        f'<input type="date" data-s="{esc(key)}:date"></label>'
    )


# applied only to the page of a per-position view: the replies name the view
VIEW_PATCHES = [
    (
        "'diff: ' + q(cfg.diff),",
        "'diff: ' + q(cfg.diff), 'view: ' + q(cfg.view),",
    ),
]


def deal_script(ranges: bool = False, view: bool = False) -> str:
    text = asset_text("task.js")
    patches = VIEW_PATCHES if view else PATCHES + (RANGE_PATCHES if ranges else [])
    for old, new in patches:
        if text.count(old) != 1:
            raise RuntimeError(
                f"task.js has no unique place for the deal patch {old[:30]!r}"
            )
        text = text.replace(old, new)
    return text
