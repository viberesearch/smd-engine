"""`smd status`: the core view of a board set, one page of Markdown.

What a person needs to know before reading the record: the state line, the K
still open, the hypotheses in testing and the untested ones in leverage order
(leverage.py, a proposal), the red lines their observations breach
(redline.py), the verdicts the decision rule proposes for the
hypotheses with an observed count (verdict.py), the AI-voiced items waiting for a human sign-off, the
transitions, and the counts (with the AI share of the functions when an element
has `ai`, validate/ai.py). Nothing else. Lists are cut and end in "and N more",
so the page for a large record still fits on a screen."""

from __future__ import annotations

from collections import Counter
from typing import Any

from smd_engine.leverage import leverage_order
from smd_engine.profile import profile_of
from smd_engine.redline import breaches
from smd_engine.render.text import (
    LABELS,
    ai_text,
    cut,
    date_text,
    days_text,
    rule_text,
    value_word,
)
from smd_engine.validate.ai import ai_share
from smd_engine.validate.context import is_ai
from smd_engine.verdict import is_share, of_hypothesis, verdict_line

# How many items of each list the page shows.
SHOWN = {
    "verdicts": 8,
    "breaches": 8,
    "k": 8,
    "testing": 5,
    "untested": 5,
    "transitions": 5,
    "ids": 6,
    "kinds": 8,
}
WIDTH = 100  # characters of one item's text


def _tail(words: dict[str, str], total: int, shown: int) -> list[str]:
    return [f"- {words['more'].format(n=total - shown)}"] if total > shown else []


def _state_lines(data: dict[str, Any], lang: str) -> list[str]:
    lab = LABELS[lang]
    state = data.get("state") or {}
    head = f"{lab['cycle']} {data['cycle']}"
    if state.get("version"):
        head += f" ({lab['digest']['version']} {state['version']})"
    head += f", {value_word('record_status', data['status'], lang)}"
    if data.get("revises"):
        head += f"; {lab['digest']['revises']} {data['revises']}"
    counts = [
        f"{lab[key]} {len(state[key])}"
        for key in ("accepted", "open")
        if key in state and state[key]
    ]
    lines = [f"- **{lab['state']}:** {'; '.join([head, *counts])}"]
    for key, text in (
        (lab["difficulty"].capitalize(), state.get("difficulty")),
        (lab["next"].capitalize(), state.get("next_move")),
    ):
        if text:
            lines.append(f"- **{key}:** {cut(str(text), 160)}")
    return lines


def _open_k(data: dict[str, Any], lang: str) -> list[str]:
    lab, words = LABELS[lang], LABELS[lang]["core"]
    # open first, then partly answered, each in the record's order
    ks = [
        q
        for s in ("open", "partly")
        for q in data.get("qualifications", [])
        if q["status"] == s
    ]
    out = [f"## {words['open_k']} ({len(ks)})"] if ks else []
    out += [
        f"- {q['id']} ({lab['status'][q['status']]}): {cut(q['text'], WIDTH)}"
        for q in ks[: SHOWN["k"]]
    ]
    return out + _tail(words, len(ks), SHOWN["k"])


def _testing(data: dict[str, Any], lang: str) -> list[str]:
    words = LABELS[lang]["core"]
    testing = [h for h in data.get("hypotheses", []) if h["status"] == "testing"]
    if not testing:
        return []
    out = [f"## {words['testing']} ({len(testing)})"]
    out += [
        f"- {h['id']}: {cut(h['assumes'], WIDTH)}" for h in testing[: SHOWN["testing"]]
    ]
    return out + _tail(words, len(testing), SHOWN["testing"])


def _verdicts(data: dict[str, Any], lang: str) -> list[str]:
    """The verdict the decision rule proposes for each hypothesis with `rule`
    and `observed` (verdict.py); the group signs accept_result."""
    lab, words = LABELS[lang], LABELS[lang]["core"]
    ruled = [
        h
        for h in data.get("hypotheses", [])
        if h.get("rule") and h.get("observed")
        if h["observed"]["k"] <= h["observed"]["n"]
        # a recorded result is not re-proposed; validate warns on a contradiction
        and h["status"] == "testing"
    ]
    if not ruled:
        return []
    out = [f"## {words['verdicts']} ({len(ruled)})"]
    for h in ruled[: SHOWN["verdicts"]]:
        v = of_hypothesis(h)
        said = (
            f"{verdict_line(v)}: {words['verdict'][v.outcome]}"
            if v and is_share(h["rule"])
            else words["no_share"]
        )
        status = lab["hyp_status"][h["status"]]
        out.append(f"- {h['id']} ({status}; {rule_text(h['rule'], lang)}): {said}")
    return out + _tail(words, len(ruled), SHOWN["verdicts"])


def _untested(data: dict[str, Any], lang: str) -> list[str]:
    """The untested hypotheses in leverage order (leverage.py): a proposal."""
    words = LABELS[lang]["core"]
    by_id = {h["id"]: h for h in data.get("hypotheses", [])}
    order = leverage_order(data)
    if not order:
        return []
    out = [f"## {words['untested']} ({len(order)})"]
    out += [
        f"- {x.id} ({words['reach']} {x.score}): {cut(by_id[x.id]['assumes'], WIDTH)}"
        for x in order[: SHOWN["untested"]]
    ]
    return out + _tail(words, len(order), SHOWN["untested"])


def _ids(words: dict[str, str], ids: list[str]) -> str:
    shown = ids[: SHOWN["ids"]]
    more = (
        f", {words['more'].format(n=len(ids) - len(shown))}"
        if len(ids) > len(shown)
        else ""
    )
    return f"{len(ids)}: {', '.join(shown)}{more}"


def _waiting(data: dict[str, Any], lang: str) -> list[str]:
    """AI-voiced items a human has to decide on: thesis variants, candidate
    moves, and K and H an AI drafted that are not closed or resolved."""
    words = LABELS[lang]["core"]
    groups = {
        "w_variants": [
            t["id"] for t in data.get("theses", []) if t["status"] == "ai_variant"
        ],
        "w_moves": [
            i["id"]
            for i in data["elements"] + data.get("theses", [])
            if i.get("move", {}).get("status") == "candidate"
        ],
        "w_k": [
            q["id"]
            for q in data.get("qualifications", [])
            if is_ai(q.get("voice")) and q["status"] != "closed"
        ],
        "w_h": [
            h["id"]
            for h in data.get("hypotheses", [])
            if is_ai(h.get("voice")) and h["status"] in ("untested", "testing")
        ],
    }
    lines = [f"- {words[key]} {_ids(words, ids)}" for key, ids in groups.items() if ids]
    return [f"## {words['waiting']}", *lines] if lines else []


def _breaches(data: dict[str, Any], lang: str) -> list[str]:
    """The red lines their observations breach (redline.py), each with the
    dates of its breaches."""
    words = LABELS[lang]["core"]
    found = [(e, breaches(e, data.get("date"))) for e in data["elements"]]
    found = [(e, b) for e, b in found if b]
    if not found:
        return []
    out = [f"## {words['breaches']} ({len(found)})"]
    for e, runs in found[: SHOWN["breaches"]]:
        said = "; ".join(
            words["breach"].format(
                start=date_text(b.start, lang),
                end=date_text(b.end, lang),
                days=days_text(b.days, lang)
                + ("" if b.closed else f", {words['still']}"),
            )
            for b in runs
        )
        out.append(f"- {e['id']}: {cut(e.get('short', e['label']), WIDTH)}: {said}")
    return out + _tail(words, len(found), SHOWN["breaches"])


def _transitions(data: dict[str, Any], lang: str) -> list[str]:
    lab, rows = LABELS[lang], data.get("transitions", [])
    if not rows:
        return []
    out = [f"## {lab['transitions']} ({len(rows)})"]
    for t in rows[: SHOWN["transitions"]]:
        label = f": {cut(t['label'], WIDTH)}" if t.get("label") else ""
        out.append(f"- {t['n']}: {t['from']} -> {t['to']}{label}")
    return out + _tail(lab["core"], len(rows), SHOWN["transitions"])


def _counts(data: dict[str, Any], lang: str) -> list[str]:
    lab, words = LABELS[lang], LABELS[lang]["core"]
    profile = profile_of(data)
    elements = data["elements"]
    boards = []
    for board in profile.boards:
        here = [e for e in elements if e["board"] == board.id]
        if not here:
            continue
        halves = Counter(e["half"] for e in here if e.get("half"))
        split = ", ".join(
            f"{lab[h]} {halves[h]}" for h in ("small", "big") if halves[h]
        )
        boards.append(
            f"{profile.board_label(board.id, lang)} {len(here)}"
            + (f" ({split})" if split else "")
        )
    kinds = Counter(e["kind"] for e in elements)
    ranked = sorted(kinds, key=lambda k: (-kinds[k], profile.kind_order.index(k)))
    shown = [
        f"{profile.kind_label(k, lang)} {kinds[k]}" for k in ranked[: SHOWN["kinds"]]
    ]
    if len(ranked) > SHOWN["kinds"]:
        shown.append(words["more"].format(n=len(ranked) - SHOWN["kinds"]))
    # the AI share of the functions, only when an element has `ai` (gate ИИ1 Б)
    share = ai_share(data)
    return [
        f"## {words['counts']}: {lab['elements'].lower()} {len(elements)}",
        f"- {words['boards']}: {'; '.join(boards)}",
        f"- {words['kinds']}: {'; '.join(shown)}",
        *([f"- {ai_text(share, lang)}"] if share else []),
    ]


def render_status(data: dict[str, Any], lang: str = "ru") -> str:
    """The core view of a validated board set as Markdown."""
    sections = [
        [f"# {cut(data['title'], 120)}", *_state_lines(data, lang)],
        _open_k(data, lang),
        _testing(data, lang),
        _verdicts(data, lang),
        _untested(data, lang),
        _breaches(data, lang),
        _waiting(data, lang),
        _transitions(data, lang),
        _counts(data, lang),
    ]
    return "\n\n".join("\n".join(s) for s in sections if s) + "\n"
