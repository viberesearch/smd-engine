"""`diff.md` and `agenda.md`: the diff and the agenda as Markdown."""

from __future__ import annotations

from typing import Any

from smd_engine.task.asking import diff_line
from smd_engine.task.deal_render import (
    alpha_note,
    model_note,
    pair_block,
    point_meta,
    point_open,
    view_note,
    why_lines,
)
from smd_engine.task.deal_labels import DEAL_LABELS
from smd_engine.task.labels import LABELS, class_word, route_word
from smd_engine.task.names import Names
from smd_engine.task.pack_md import mm, table


def show(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    return str(value)


def class_counts(points: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in points:
        counts[p["class"]] = counts.get(p["class"], 0) + 1
    return counts


def by_label(lang: str, p: dict[str, Any]) -> str:
    lab = LABELS[lang]
    if p["class_by"] == "model":
        return f"{lab['model']} ({lab['ai_draft']})"
    return str(lab.get(p["class_by"], p["class_by"]))


def _by(lab: dict[str, Any], lang: str, p: dict[str, Any]) -> str:
    """The note on who decided the class; none for a value point of a view, which
    shows no class of its own."""
    return f" ({lab['class_by']}: {by_label(lang, p)})" if "class_by" in p else ""


def how_word(lang: str, how: str) -> str:
    if how == "replies":
        return str(LABELS[lang]["by_replies"])
    return route_word(lang, how)


def point_title(p: dict[str, Any]) -> str:
    return str(p.get("question") or p.get("text") or p.get("term") or "")


def _alpha_rows(lab: dict[str, Any], alpha: dict[str, Any]) -> list[list[Any]]:
    def row(name: str, a: dict[str, Any]) -> list[Any]:
        shown = "n/a" if a["alpha"] is None else f"{a['alpha']:.3f}"
        return [name, a["units"], shown, a["reading"] or a["why_not"]]

    rows = [row(lab["all_choice"], alpha["choice_items"])]
    rows += [row(name, a) for name, a in alpha["sections"].items()]
    return rows


def _groups(
    points: list[dict[str, Any]], lab: dict[str, Any]
) -> list[tuple[str, list[dict[str, Any]]]]:
    groups: list[tuple[str, list[dict[str, Any]]]] = [
        (lab["term_points"], [p for p in points if p["kind"] == "term_check"])
    ]
    items = [p for p in points if p["kind"] == "item"]
    for section in dict.fromkeys(p["section"] for p in items):
        groups.append((section, [p for p in items if p["section"] == section]))
    groups.append((lab["added_points"], [p for p in points if p["kind"] == "added"]))
    return [(name, ps) for name, ps in groups if ps]


def answers_table(lab: dict[str, Any], p: dict[str, Any], nm: Names) -> list[str]:
    if p["class"] == "sealed":  # no answers: the commitments stay in their files
        return []
    rows = [
        [
            nm.member(m),
            nm.value(p, a["value"]),
            a.get("reason", ""),
            a.get("confidence", ""),
            a.get("source", ""),
            a.get("term_note", ""),
            nm.sources(a),
        ]
        for m, a in p["answers"].items()
    ]
    head = [
        lab["member"],
        lab["answer"],
        lab["reason"],
        lab["confidence"],
        lab["src"],
        lab["term_note"],
        DEAL_LABELS[nm.lang]["source_ids"],
    ]
    # empty columns are dropped
    keep = [i for i in range(len(head)) if i < 2 or any(r[i] for r in rows)]
    return table([head[i] for i in keep], [[r[i] for i in keep] for r in rows])


def render_diff_md(diff: dict[str, Any]) -> str:
    lang = diff["lang"]
    lab = LABELS[lang]
    nm = Names(lang, diff.get("labels"))
    points = diff["points"]
    counts = class_counts(points)
    out = [f"# {diff['title']}: {lab['diff']}", "", f"_{lab['diff_intro']}_", ""]
    if note := view_note(diff, nm, lang):
        out += [f"**{note}**", ""]
    out += table(
        [lab["id"], lab["version"], lab["pack_sha"], lab["diff_proc"], lab["members"]],
        [
            [
                diff["pack"]["id"],
                diff["pack"]["version"],
                diff["pack"]["sha256"],
                diff["procedure"],
                nm.members(diff["members"]),
            ]
        ],
    )
    out += [f"## {lab['answers_files']}", ""]
    out += table(
        [lab["member"], lab["date"], lab["drafted"], "sha256"],
        [
            [nm.member(f["member"]), f["date"], f["drafted_by"], f["sha256"][:12]]
            for f in diff["answers_files"]
        ],
    )
    out += [f"## {lab['summary']}", "", "```mermaid", "pie showData"]
    out += [
        f'  "{mm(class_word(lang, {"class": c}))}" : {n}' for c, n in counts.items()
    ]
    out += ["```", ""]
    out += table(
        [lab["class"], lab["count"]],
        [[class_word(lang, {"class": c}), n] for c, n in counts.items()],
    )
    out += [
        f"{lab['points']}: {len(points)}; {lab['open_points']}: {sum(1 for p in points if point_open(p))}.",
        "",
    ]
    if block := pair_block(diff, nm, lang):
        out += [f"## {block[0]}", ""] + table(block[1], block[2])
    out += [f"## {lab['alpha']}", ""]
    out += table(
        [lab["section"], lab["units"], lab["alpha_col"], lab["reading"]],
        _alpha_rows(lab, diff["alpha"]),
    )
    out += [lab["few"], ""]
    if alpha_note(diff):
        out += [alpha_note(diff), ""]
    if model_note(diff):
        out += [model_note(diff), ""]
    if diff_line(diff):
        out += [diff_line(diff), ""]
    if diff["transcripts"]:
        out += [f"## {lab['transcripts_diff']}", ""]
        rows = [
            [
                nm.member(m),
                t["path"],
                t.get("sha256", "")[:12],
                t.get("note", ""),
                t["status"],
            ]
            for m, ts in diff["transcripts"].items()
            for t in ts
        ]
        out += table(
            [
                lab["member"],
                lab["transcript_path"],
                "sha256",
                lab["note"],
                lab["status"],
            ],
            rows,
        )
    out += [f"## {lab['points']}", ""]
    for name, group in _groups(points, lab):
        out += [f"### {name}", ""]
        for p in group:
            out += [f"#### {nm.title(p)}", "", f"<!-- id: {p['id']} -->", ""]
            out.append(
                f"- {lab['class']}: **{class_word(lang, p)}**{_by(lab, lang, p)}"
            )
            if "route" in p:
                out.append(f"- {lab['route']}: {route_word(lang, p['route'])}")
            if p.get("silent"):
                out.append(f"- {lab['silent']}: {nm.members(p['silent'])}")
            out += [f"- {line}" for line in point_meta(p, nm, lang)]
            if p.get("refs"):
                out.append(f"- {lab['refs']}: {nm.refs(p)}")
            if p.get("sets"):
                out.append(
                    f"- {lab['common']}: {nm.value(p, p['sets']['common']) or '-'}"
                )
                out += [
                    f"- {lab['only_member'].format(m=nm.member(m))}: {nm.value(p, v)}"
                    for m, v in p["sets"]["only_by"].items()
                ]
            for key in ("rationale", "assigned_to"):
                if p.get(key):
                    shown = nm.member(p[key]) if key == "assigned_to" else p[key]
                    out.append(f"- {lab[key]}: {shown}")
            out += [""] + answers_table(lab, p, nm)
    return "\n".join(out).rstrip() + "\n"


def render_agenda_md(agenda: dict[str, Any]) -> str:
    lang = agenda["lang"]
    lab = LABELS[lang]
    nm = Names(lang, agenda.get("labels"))
    out = [f"# {lab['agenda']}: {agenda['title']}", ""]
    if diff_line(agenda):
        out += [diff_line(agenda), ""]
    out += [
        f"- {lab['pack_sha']}: {agenda['pack']['sha256'][:12]}; diff sha256: {agenda['diff'][:12]}",
        f"- {lab['replied']}: {nm.members(agenda['replied']) or lab['none']}",
        f"- {lab['not_replied']}: {nm.members(agenda['not_replied']) or lab['none']}",
        f"- {lab['points']}: {agenda['counts']['points']}; {lab['call_points']}: "
        f"{agenda['counts']['call']}; {lab['settled_points']}: {agenda['counts']['settled']}",
        "",
        f"## {lab['call_points']}",
        "",
    ]
    if not agenda["call"]:
        out += [lab["nothing_call"], ""]
    for n, p in enumerate(agenda["call"], start=1):
        out += [f"### {n}. {nm.title(p)}", "", f"<!-- id: {p['id']} -->", ""]
        out.append(
            f"- {lab['class']}: **{class_word(lang, p)}** ({lab['class_by']}: {by_label(lang, p)})"
        )
        out.append(f"- {lab['route']}: {route_word(lang, p['route'])}")
        why = p["why"]
        if why.get("discuss"):
            out.append(
                f"- {lab['why_agenda']}: {lab['discuss_by']} {nm.members(why['discuss'])}"
            )
        if why.get("no_reply"):
            out.append(
                f"- {lab['why_agenda']}: {lab['no_reply_by']} {nm.members(why['no_reply'])}"
            )
        out += [f"- {lab['why_agenda']}: {w}" for w in why_lines(p, lang)]
        out += [f"- {line}" for line in point_meta(p, nm, lang)]
        for m, note in p.get("notes", {}).items():
            out.append(f"- {lab['note_field']} {nm.member(m)}: {note}")
        out += [""]
        if p.get("answers_withheld"):
            out += [DEAL_LABELS[lang]["answers_withheld"], ""]
            continue
        rows = [
            [nm.member(m), nm.value(p, a["value"]), a.get("reason", "")]
            for m, a in p["answers"].items()
        ]
        out += table([lab["member"], lab["answer"], lab["reason"]], rows)
    out += [f"## {lab['settled_points']}", ""]
    rows = [
        [
            nm.title(p),
            class_word(lang, p),
            how_word(lang, p["how"]),
            "; ".join(
                f"{nm.member(m)}: {nm.reply(r)}"
                for m, r in p.get("replies", {}).items()
            ),
        ]
        for p in agenda["settled"]
    ]
    out += table(
        [lab["points"], lab["class"], lab["how_settled"], lab["replies"]],
        rows,
    )
    return "\n".join(out).rstrip() + "\n"
