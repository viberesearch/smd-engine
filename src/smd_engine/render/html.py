"""Self-contained HTML page: the SVG screen plus tables of qualifications, theses,
hypotheses, sign-offs and elements."""

from __future__ import annotations

from typing import Any

from smd_engine.profile import profile_of
from smd_engine.render.svg import render_svg
from smd_engine.render.text import (
    LABELS,
    board_text,
    continuum_lines,
    element_lines,
    esc,
    pace_text,
    value_word,
)

CSS = """
:root{--bg:#fff;--ink:#1d1d1f;--muted:#5b5b60;--line:#e3e3e8;--navy:#12235a}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 "IBM Plex Sans",Helvetica,Arial,sans-serif}
main{max-width:1640px;margin:0 auto;padding:24px 16px 48px}
svg{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:8px}
h2{font-size:18px;margin:28px 0 8px;color:var(--navy)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600}
code{font-size:13px;color:var(--muted)}
"""


def _head(cols: list[str]) -> str:
    return "".join(f"<th>{esc(c)}</th>" for c in cols)


def _fillers(el: dict[str, Any], lab: dict[str, Any]) -> str:
    if not el.get("fillers"):
        return ""
    return f"<br><small>{esc(lab['fillers'])}: {esc(', '.join(el['fillers']))}</small>"


def _pace(el: dict[str, Any], lang: str) -> str:
    text = pace_text(el, lang)
    return f"<br><small>{esc(text)}</small>" if text else ""


def _fields(el: dict[str, Any], lang: str) -> str:
    """Beer's systems of a post or position, threshold and recovery time of an
    algedonic channel, the place a position takes and its stance."""
    shown = element_lines(el, lang)
    return f"<br><small>{esc('; '.join(shown))}</small>" if shown else ""


def _continuum(o: dict[str, Any], lang: str) -> str:
    """Lives in, tempos, horizon and covers of an ontology record."""
    shown = continuum_lines(o, lang)
    return f"<br><small>{esc('; '.join(shown))}</small>" if shown else ""


def _table(title: str, cols: list[str], rows: list[list[str]]) -> str:
    """A titled table; cells are already escaped. Empty when there are no rows."""
    if not rows:
        return ""
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<h2>{esc(title)}</h2><table><tr>{_head(cols)}</tr>{body}</table>"


def render_html(
    data: dict[str, Any], lang: str = "ru", screen: dict[str, Any] | None = None
) -> str:
    """The page; `screen` draws a different view of the record (the lighter
    screen) above the full tables."""
    lab = LABELS[lang]
    profile = profile_of(data)
    rows_k = "".join(
        f"<tr><td><b>{esc(q['id'])}</b></td><td>{esc(lab['status'][q['status']])}</td>"
        f"<td>{esc(q['text'])}</td><td>{esc(q.get('by', ''))}</td>"
        f"<td><code>{esc(', '.join(q.get('cites', [])))}</code></td></tr>"
        for q in data.get("qualifications", [])
    )
    rows_e = "".join(
        f"<tr><td><code>{esc(e['id'])}</code></td>"
        f"<td>{esc(board_text(profile, e, lang))}</td>"
        f"<td>{esc(profile.kind_label_one(e['kind'], lang))}</td>"
        f"<td>{esc(e['label'])}{_fillers(e, lab)}{_pace(e, lang)}"
        f"{_fields(e, lang)}</td>"
        f"<td><code>{esc(', '.join(e.get('cites', [])))}</code></td></tr>"
        for e in data["elements"]
    )
    details = "".join(
        _table(
            f"{e['id']} {e['detail'].get('title', '')}".strip(),
            e["detail"]["columns"],
            [[esc(c) for c in row] for row in e["detail"]["rows"]],
        )
        for e in data["elements"]
        if e.get("detail")
    )
    k_table = (
        f"<h2>{esc(lab['qualifications'])}</h2><table><tr>{_head(lab['columns'])}</tr>"
        f"{rows_k}</table>"
        if rows_k
        else ""
    )
    theses = _table(
        lab["theses"],
        lab["th_columns"],
        [
            [
                f"<b>{esc(t['id'])}</b> {esc(t['claim'])}",
                f"<code>{esc(', '.join(t.get('cites', [])))}</code>",
                esc(value_word("voice", t["voice"], lang)),
                esc(lab["thesis_status"][t["status"]]),
            ]
            for t in data.get("theses", [])
        ],
    )
    hypotheses = _table(
        lab["hypotheses"],
        lab["h_columns"],
        [
            [
                f"<b>{esc(h['id'])}</b>",
                esc(lab["hyp_status"][h["status"]]),
                esc(h["assumes"]),
                esc(h.get("action", "")),
                esc(h.get("result", "")),
            ]
            for h in data.get("hypotheses", [])
        ],
    )
    ontology = _table(
        lab["ontology"],
        lab["o_columns"],
        [
            [
                f"<b>{esc(o['id'])}</b>",
                esc(o["object"]) + _continuum(o, lang),
                f"<code>{esc(', '.join(o['valid_for']))}</code>",
                f"<code>{esc(o.get('cooperation', ''))}</code>",
                esc(o.get("test", "")),
            ]
            for o in data.get("ontology", [])
        ],
    )
    signoffs = _table(
        lab["signoffs"],
        lab["s_columns"],
        [
            [
                esc(value_word("function", s["function"], lang)),
                f"<code>{esc(s.get('target', ''))}</code>",
                esc(s["by"]),
                esc(s.get("note", "")),
            ]
            for s in data.get("signoffs", [])
        ],
    )
    return (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(data['title'])}</title><style>{CSS}</style></head><body><main>"
        f"{render_svg(screen or data, lang)}{k_table}{theses}{hypotheses}{ontology}{signoffs}"
        f"<h2>{esc(lab['elements'])}</h2><table><tr>{_head(lab['el_columns'])}</tr>"
        f"{rows_e}</table>{details}</main></body></html>\n"
    )
