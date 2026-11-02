"""`diff.html`: the diff as one offline page. The answers side by side, a filter by
class, and a reply form per point that writes `replies_<member>.yaml`."""

from __future__ import annotations

from typing import Any

from smd_engine.render.text import esc
from smd_engine.task.diff import is_open
from smd_engine.task.diff_md import (
    by_label,
    class_counts,
)
from smd_engine.task.labels import LABELS, class_word, route_word
from smd_engine.task.names import Names
from smd_engine.task.web import page, table as _table

UI_KEYS = ("missing_member", "exported", "unreplied", "bad_accept")


def _answers(lab: dict[str, Any], p: dict[str, Any], nm: Names) -> str:
    rows = []
    for m, a in p["answers"].items():
        extra = [a.get(k, "") for k in ("reason", "confidence", "source", "term_note")]
        rows.append(
            [esc(nm.member(m)), esc(nm.value(p, a["value"]))] + [esc(x) for x in extra]
        )
    head = [
        lab["member"],
        lab["answer"],
        lab["reason"],
        lab["confidence"],
        lab["src"],
        lab["term_note"],
    ]
    keep = [i for i in range(len(head)) if i < 2 or any(r[i] for r in rows)]
    return _table([head[i] for i in keep], [[r[i] for i in keep] for r in rows], "ans")


def _reply(lab: dict[str, Any], p: dict[str, Any], nm: Names) -> str:
    pid = esc(p["id"])
    radios = "".join(
        f'<label class="opt" style="display:inline-block"><input type="radio" '
        f'name="rc:{pid}" data-s="rc:{pid}" value="{c}"> {esc(lab[c])}</label>'
        for c in ("accept", "keep", "discuss")
    )
    whose = "".join(
        f'<option value="{esc(m)}">{esc(nm.member(m))}</option>' for m in p["answers"]
    )
    return (
        f'<div class="bar">{radios}'
        f'<button type="button" class="link" data-clear="rc:{pid}">{esc(lab["clear"])}</button>'
        f'<select data-s="ra:{pid}" aria-label="{esc(lab["accept_whose"])}">'
        f'<option value="">{esc(lab["accept_whose"])}</option>{whose}</select></div>'
        f'<input type="text" data-s="rn:{pid}" placeholder="{esc(lab["note_field"])}">'
    )


def _point(lang: str, p: dict[str, Any], nm: Names) -> str:
    lab = LABELS[lang]
    opened = is_open(p["route"])
    model = (
        f'<span class="tag model">{esc(lab["ai_draft"])}</span>'
        if p["class_by"] == "model"
        else ""
    )
    meta = [
        f"{lab['class_by']}: {by_label(lang, p)}",
        f"{lab['route']}: {route_word(lang, p['route'])}",
    ]
    if p.get("silent"):
        meta.append(f"{lab['silent']}: {nm.members(p['silent'])}")
    if p.get("refs"):
        meta.append(f"{lab['refs']}: {nm.refs(p)}")
    if p.get("sets"):
        meta.append(f"{lab['common']}: {nm.value(p, p['sets']['common']) or '-'}")
        meta += [
            f"{lab['only_member'].format(m=nm.member(m))}: {nm.value(p, v)}"
            for m, v in p["sets"]["only_by"].items()
        ]
    for key in ("rationale", "assigned_to"):
        if p.get(key):
            shown = nm.member(p[key]) if key == "assigned_to" else p[key]
            meta.append(f"{lab[key]}: {shown}")
    short, text = nm.heading(p)
    return (
        f'<details class="pt {"open" if opened else "settled"}" data-class="{esc(p["class"])}" '
        f'id="pt-{esc(p["id"])}"{" open" if opened else ""}>'
        f"<summary><b>{esc(short)}</b> {esc(text)} "
        f'<span class="tag">{esc(class_word(lang, p))}</span>{model}</summary>'
        f'<p class="meta">{esc("; ".join(meta))}</p>{_answers(lab, p, nm)}{_reply(lab, p, nm)}</details>'
    )


def render_diff_html(diff: dict[str, Any], diff_sha: str) -> str:
    lang = diff["lang"]
    lab = LABELS[lang]
    nm = Names(lang, diff.get("labels"))
    points = diff["points"]
    counts = class_counts(points)
    summary = (
        _table(
            [lab["id"], lab["version"], lab["pack_sha"], lab["diff_proc"]],
            [
                [
                    esc(diff["pack"]["id"]),
                    esc(diff["pack"]["version"]),
                    esc(diff["pack"]["sha256"]),
                    esc(diff["procedure"]),
                ]
            ],
        )
        + f"<p class=\"meta\">{esc(lab['diff_intro'])}</p>"
        + f"<h2>{esc(lab['answers_files'])}</h2>"
        + _table(
            [lab["member"], lab["date"], lab["drafted"], "sha256"],
            [
                [
                    esc(nm.member(f["member"])),
                    esc(f["date"]),
                    esc(f["drafted_by"]),
                    esc(f["sha256"][:12]),
                ]
                for f in diff["answers_files"]
            ],
        )
        + f"<h2>{esc(lab['summary'])}</h2>"
        + _table(
            [lab["class"], lab["count"]],
            [[esc(class_word(lang, {"class": c})), str(n)] for c, n in counts.items()],
        )
        + f"<h2>{esc(lab['alpha'])}</h2>"
        + _alpha(lab, diff["alpha"])
        + f"<p class=\"meta\">{esc(lab['few'])}</p>"
    )
    if diff["transcripts"]:
        summary += f"<h2>{esc(lab['transcripts_diff'])}</h2>" + _table(
            [
                lab["member"],
                lab["transcript_path"],
                "sha256",
                lab["note"],
                lab["status"],
            ],
            [
                [
                    esc(nm.member(m)),
                    esc(t["path"]),
                    esc(t.get("sha256", "")[:12]),
                    esc(t.get("note", "")),
                    esc(t["status"]),
                ]
                for m, ts in diff["transcripts"].items()
                for t in ts
            ],
        )
    options = f'<option value="">{esc(lab["filter_all"])}</option>'
    options += f'<option value="(open)">{esc(lab["only_open"])}</option>'
    options += "".join(
        f'<option value="{esc(c)}">{esc(class_word(lang, {"class": c}))}</option>'
        for c in counts
    )
    body = f'<div class="bar"><select id="flt">{options}</select></div>' + "".join(
        _point(lang, p, nm) for p in points
    )
    members = f'<option value="">{esc(lab["choose"])}</option>' + "".join(
        f'<option value="{esc(m)}">{esc(nm.member(m))}</option>'
        for m in diff["members"]
    )
    reply = (
        f"<p>{esc(lab['reply_hint'])}</p>"
        f'<label class="f">{esc(lab["member"])}<select data-s="member">{members}</select></label>'
        f'<label class="f">{esc(lab["date"])}<input type="date" data-s="date"></label>'
        f'<p class="meta">{esc(lab["saved"])}</p>'
        f'<p><button type="button" class="primary" id="export">{esc(lab["export_replies"])}</button></p>'
        '<div id="status" role="status"></div>'
    )
    cfg = {
        "mode": "diff",
        "key": diff_sha,
        "diff": diff_sha,
        "points": [
            {"id": p["id"], "name": nm.heading(p)[0], "open": is_open(p["route"])}
            for p in points
        ],
        "ui": {k: lab[k] for k in UI_KEYS},
    }
    return page(
        f"{diff['title']}: {lab['diff']}",
        lang,
        f"{diff['pack']['id']} {diff['pack']['version']}",
        [
            ("summary", lab["summary"], summary),
            ("points", lab["points"], body),
            ("reply", lab["reply_title"], reply),
        ],
        cfg,
    )


def _alpha(lab: dict[str, Any], alpha: dict[str, Any]) -> str:
    def row(name: str, a: dict[str, Any]) -> list[str]:
        shown = "n/a" if a["alpha"] is None else f"{a['alpha']:.3f}"
        return [esc(name), str(a["units"]), shown, esc(a["reading"] or a["why_not"])]

    rows = [row(lab["all_choice"], alpha["choice_items"])]
    rows += [row(n, a) for n, a in alpha["sections"].items()]
    return _table(
        [lab["section"], lab["units"], lab["alpha_col"], lab["reading"]], rows
    )
