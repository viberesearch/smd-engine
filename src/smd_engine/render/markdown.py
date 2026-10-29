"""Markdown digest of a board set: one line per element, for search and review."""

from __future__ import annotations

from typing import Any

from smd_engine.profile import Profile, profile_of
from smd_engine.render.graph import relation_words
from smd_engine.render.text import (
    LABELS,
    MOVE_NAMES,
    continuum_lines,
    element_parts,
    field_lines,
    value_word,
)


def _words(lang: str) -> dict[str, str]:
    """Words of the digest outside the element line: the field labels, with
    the digest's own words over them."""
    words: dict[str, str] = LABELS[lang]["fields"] | LABELS[lang]["digest"]
    return words


def _line(el: dict[str, Any], lang: str, profile: Profile) -> str:
    """One element: its kind by the singular label of the profile, its words
    and fixed values (frame state, epistemic status, move status) in the
    language (value_word); ids as recorded."""
    w = LABELS[lang]["line"]
    kind = profile.kind_label_one(el["kind"], lang)
    bits = [f"`{el['id']}` {kind}: {el['label']}"]
    if el.get("frame_state"):
        bits.append(f"({value_word('frame_state', el['frame_state'], lang)})")
    if el.get("in"):
        bits.append(f"{w['in']} " + ", ".join(f"`{i}`" for i in el["in"]))
    if el.get("fillers"):
        bits.append(f"{w['fillers']}: " + ", ".join(el["fillers"]))
    bits += field_lines(element_parts(el, lang), lang)
    if el.get("seen_from"):
        bits.append(f"{w['seen_from']} `{el['seen_from']}`")
    if el.get("epistemic"):
        bits.append(f"[{value_word('epistemic', el['epistemic'], lang)}]")
    if el.get("lineage"):
        bits.append(f"{w['lineage']}: " + ", ".join(el["lineage"]))
    if el.get("move"):
        m = el["move"]
        bits.append(
            f"{w['move']}: {MOVE_NAMES[lang][m['op']]} {w['from']} "
            f"{', '.join(m['from'])}"
            + (f" {w['via']} {m['via']}" if m.get("via") else "")
            + (
                f" ({value_word('move_status', m['status'], lang)})"
                if m.get("status")
                else ""
            )
        )
    if el.get("cites"):
        bits.append("— " + ", ".join(el["cites"]))
    return "- " + " ".join(bits)


def _board_line(board: dict[str, Any], lang: str) -> str:
    """A record board: its template, the element it unfolds, the position it
    is seen from; ids as recorded."""
    w = _words(lang)
    bits = [f"`{board['id']}` {w['board_of']} `{board['template']}`"]
    if board.get("unfolds"):
        bits.append(f"{w['unfolds']} `{board['unfolds']}`")
    if board.get("seen_from"):
        bits.append(f"{LABELS[lang]['line']['seen_from']} `{board['seen_from']}`")
    if board.get("cites"):
        bits.append("— " + ", ".join(board["cites"]))
    return " ".join(bits)


def render_markdown(data: dict[str, Any], lang: str = "ru") -> str:
    lab = LABELS[lang]
    words = _words(lang)
    out = [f"# {data['title']}", ""]
    meta = [
        f"id `{data['id']}`",
        f"{lab['cycle']} {data['cycle']}",
        value_word("record_status", data["status"], lang),
    ]
    if data.get("revises"):
        meta.append(f"{words['revises']} `{data['revises']}`")
    if data.get("date"):
        meta.append(data["date"])
    out += [" · ".join(meta), ""]
    # one section per board of the profile, or per half
    profile = profile_of(data)
    sections = [
        (b.id, b.label[lang], half)
        for b in profile.boards
        for half in (b.halves or (None,))
    ]
    made = {b["id"]: b for b in data.get("boards", [])}
    for board, name, half in sections:
        items = [
            e
            for e in data["elements"]
            if e["board"] == board and (half is None or e.get("half") == half)
        ]
        if not items and board not in made:  # a record board is always listed
            continue
        title = name + (f" — {lab[half]}" if half else "")
        out += [f"## {title}", ""]
        if board in made:  # a board the record makes of a template
            out += [_board_line(made[board], lang), ""]
        out += [_line(e, lang, profile) for e in items] + ([""] if items else [])
    tables = [e for e in data["elements"] if e.get("detail")]
    if tables:
        out += [f"## {lab['details']}", ""]
    for e in tables:
        d = e["detail"]
        out += [f"### `{e['id']}` {d.get('title', '')}".rstrip(), ""]
        out += ["| " + " | ".join(d["columns"]) + " |"]
        out += ["|" + "---|" * len(d["columns"])]
        out += ["| " + " | ".join(row) + " |" for row in d["rows"]] + [""]
    if data.get("relations"):
        out += [f"## {lab['relations']}", ""]
        # relation kinds by their words in Russian; the English digest keeps
        # the ids, as it always has
        kinds = relation_words(profile, lang) if lang == "ru" else {}
        for r in data["relations"]:
            label = f" — {r['label']}" if r.get("label") else ""
            kind = kinds.get(r["kind"], r["kind"])
            out.append(f"- `{r['from']}` → `{r['to']}` ({kind}){label}")
        out.append("")
    if data.get("transitions"):
        out += [f"## {lab['transitions']}", ""]
        for t in sorted(data["transitions"], key=lambda t: t["n"]):
            label = f" — {t['label']}" if t.get("label") else ""
            cites = f" ({', '.join(t['cites'])})" if t.get("cites") else ""
            out.append(f"{t['n']}. `{t['from']}` → `{t['to']}`{label}{cites}")
        out.append("")
    if data.get("qualifications"):
        out += [f"## {lab['qualifications']}", ""]
        for q in data["qualifications"]:
            targets = ", ".join(f"`{t}`" for t in q.get("targets", []))
            by = f" — {q['by']}" if q.get("by") else ""
            out.append(
                f"- **{q['id']}** [{lab['status'][q['status']]}] {q['text']}"
                f"{' (' + targets + ')' if targets else ''}{by}"
            )
        out.append("")
    if data.get("theses"):
        out += [f"## {lab['theses']}", ""]
        for t in data["theses"]:
            cites = f" — {', '.join(t['cites'])}" if t.get("cites") else ""
            feeds = (
                " → " + ", ".join(f"`{f}`" for f in t["feeds"])
                if t.get("feeds")
                else ""
            )
            said = ", ".join(
                (
                    value_word("voice", t["voice"], lang),
                    value_word("belt", t["belt"], lang),
                    value_word("thesis_kind", t["kind"], lang),
                )
            )
            out.append(
                f"- **{t['id']}** [{lab['thesis_status'][t['status']]}] "
                f"{said}: {t['claim']}{feeds}{cites}"
            )
        out.append("")
    if data.get("hypotheses"):
        out += [f"## {lab['hypotheses']}", ""]
        for h in data["hypotheses"]:
            bits = [
                f"- **{h['id']}** [{lab['hyp_status'][h['status']]}] {h['assumes']}"
            ]
            for key in ("action", "result", "changes"):
                if h.get(key):
                    bits.append(f"{words[key]}: {h[key]}")
            if h.get("artefacts"):
                bits.append("— " + ", ".join(h["artefacts"]))
            out.append(" ".join(bits))
        out.append("")
    if data.get("ontology"):
        out += [f"## {lab['ontology']}", ""]
        for o in data["ontology"]:
            positions = ", ".join(f"`{p}`" for p in o["valid_for"])
            line = f"- **{o['id']}** {o['object']} ({lab['valid_for']} {positions})"
            if o.get("cooperation"):
                line += f"; {words['cooperation']} `{o['cooperation']}`"
            if o.get("test"):
                line += f"; {words['test']} {o['test']}"
            out.append(line)
            for sub in o.get("subjects", []):
                out.append(f"  - `{sub['position']}`: {sub['subject']}")
            if o.get("competes"):
                out.append(f"  - {words['competes']}: {o['competes']}")
            out += [f"  - {line}" for line in continuum_lines(o, lang)]
        out.append("")
    if data.get("signoffs"):
        out += [f"## {lab['signoffs']}", ""]
        for s in data["signoffs"]:
            target = f" `{s['target']}`" if s.get("target") else ""
            note = f" — {s['note']}" if s.get("note") else ""
            function = value_word("function", s["function"], lang)
            out.append(f"- {function}{target}: {s['by']}{note}")
        out.append("")
    state = data.get("state")
    if state:
        out += [f"## {lab['state']}", ""]
        if state.get("version"):
            out.append(f"- {words['version']}: {state['version']}")
        if state.get("difficulty"):
            out.append(f"- {lab['difficulty']}: {state['difficulty']}")
        for key in ("accepted", "open"):
            for item in state.get(key, []):
                out.append(f"- {lab[key]}: {item}")
        if state.get("next_move"):
            out.append(f"- {lab['next']}: {state['next_move']}")
        out.append("")
    return "\n".join(out)
