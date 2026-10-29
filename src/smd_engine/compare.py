"""Element-by-element comparison of two board sets, and a merge proposal.

Two authors (or two runs) describe the same object. Each element of one set is
matched to the closest element of the same kind in the other set, by label.
A pair is classified after the module negotiator of doi:10.5281/zenodo.21653102:
- agreement: the same element, worded alike;
- refinement: the same element, worded differently or more narrowly;
- conflict: one id or one label, typed or placed incompatibly;
- only_a / only_b: present in one set, with no counterpart.

Matching by wording is a heuristic. The report is material for a qualification
pass, not a verdict; the merge it proposes is a draft cycle the group decides on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from smd_engine.profile import ProfileError, profile_of
from smd_engine.render.text import CONTINUUM, continuum_parts

MATCH = 0.55  # below this, two labels are not the same element
SAME = 0.85  # at or above this, two labels say the same thing
# Groups of kinds matched against each other are profile data (`compare_groups`).


@dataclass(frozen=True)
class Pair:
    kind: str  # agreement | refinement | conflict | only_a | only_b
    group: str
    a: str | None
    b: str | None
    score: float
    note: str = ""


def _norm(label: str) -> str:
    text = re.sub(r"[«»\"'“”()?:;,.!—–-]+", " ", label.lower())
    return " ".join(text.split())


def _stems(text: str) -> set[str]:
    """Crude stems for inflected languages: words cut to five letters, and figures."""
    return {w[:5] for w in re.findall(r"\w+", text) if len(w) >= 4 or w.isdigit()}


def similarity(x: str, y: str) -> float:
    """Similarity of two labels in [0, 1].

    The larger of the character ratio and the stem overlap; containment counts
    as a narrowing. Stem overlap catches the same content reworded or inflected.
    """
    nx, ny = _norm(x), _norm(y)
    if not nx or not ny:
        return 0.0
    if nx == ny:
        return 1.0
    ratio = SequenceMatcher(None, nx, ny).ratio()
    shorter, longer = sorted((nx, ny), key=len)
    if len(shorter) >= 6 and shorter in longer:
        ratio = max(ratio, MATCH + 0.1)
    sx, sy = _stems(nx), _stems(ny)
    if min(len(sx), len(sy)) >= 2:
        overlap = len(sx & sy) / min(len(sx), len(sy))
        ratio = max(ratio, 0.8 * overlap)
    return ratio


Groups = dict[str, tuple[str, ...]]


def groups_of(a: dict[str, Any], b: dict[str, Any]) -> Groups:
    """The groups of kinds of the profile both records follow."""
    pa, pb = profile_of(a), profile_of(b)
    if pa.id != pb.id:
        raise ProfileError(
            f"compare takes two records of one profile: {a['id']} follows {pa.id}, "
            f"{b['id']} follows {pb.id}"
        )
    return pb.compare_groups


def _group(kind: str, groups: Groups) -> str:
    for name, kinds in groups.items():
        if kind in kinds:
            return name
    return "other"


def compare(a: dict[str, Any], b: dict[str, Any]) -> list[Pair]:
    """Classify every element of a and b; each element appears in one pair."""
    groups = groups_of(a, b)
    skip = set(profile_of(b).compare_skip)
    a_els = [e for e in a["elements"] if e["kind"] not in skip]
    b_els = [e for e in b["elements"] if e["kind"] not in skip]
    candidates: list[tuple[float, int, int]] = []
    for i, ea in enumerate(a_els):
        for j, eb in enumerate(b_els):
            if _group(ea["kind"], groups) != _group(eb["kind"], groups):
                continue
            score = similarity(ea["label"], eb["label"])
            if ea["id"] == eb["id"]:
                score = max(score, MATCH)  # a shared id is a claim of identity
            if score >= MATCH:
                candidates.append((score, i, j))
    pairs: list[Pair] = []
    used_a: set[int] = set()
    used_b: set[int] = set()
    for score, i, j in sorted(candidates, reverse=True):
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        ea, eb = a_els[i], b_els[j]
        pairs.append(_classify(ea, eb, score, groups))
    for i, ea in enumerate(a_els):
        if i not in used_a:
            pairs.append(
                Pair("only_a", _group(ea["kind"], groups), ea["id"], None, 0.0)
            )
    for j, eb in enumerate(b_els):
        if j not in used_b:
            pairs.append(
                Pair("only_b", _group(eb["kind"], groups), None, eb["id"], 0.0)
            )
    return pairs


def _classify(
    ea: dict[str, Any], eb: dict[str, Any], score: float, groups: Groups
) -> Pair:
    group = _group(ea["kind"], groups)
    clash = []
    if ea["kind"] != eb["kind"]:
        clash.append(f"kind {ea['kind']} / {eb['kind']}")
    if ea["board"] != eb["board"] or ea.get("half") != eb.get("half"):
        clash.append("board " + _where(ea) + " / " + _where(eb))
    if ea.get("frame_state") != eb.get("frame_state"):
        clash.append(f"frame {ea.get('frame_state')} / {eb.get('frame_state')}")
    if clash:
        return Pair("conflict", group, ea["id"], eb["id"], score, "; ".join(clash))
    kind = "agreement" if score >= SAME else "refinement"
    return Pair(kind, group, ea["id"], eb["id"], score)


def _where(el: dict[str, Any]) -> str:
    return str(el["board"]) + (f"/{el['half']}" if el.get("half") else "")


def _match_texts(
    qa: list[dict[str, Any]], qb: list[dict[str, Any]], key: str
) -> list[tuple[str | None, str | None, float]]:
    """Match items by the wording of `key`; unmatched ones keep None on the other side."""
    scored = sorted(
        (
            (similarity(x[key], y[key]), i, j)
            for i, x in enumerate(qa)
            for j, y in enumerate(qb)
        ),
        reverse=True,
    )
    out: list[tuple[str | None, str | None, float]] = []
    ua: set[int] = set()
    ub: set[int] = set()
    for score, i, j in scored:
        if score < MATCH or i in ua or j in ub:
            continue
        ua.add(i)
        ub.add(j)
        out.append((qa[i]["id"], qb[j]["id"], score))
    out += [(q["id"], None, 0.0) for i, q in enumerate(qa) if i not in ua]
    out += [(None, q["id"], 0.0) for j, q in enumerate(qb) if j not in ub]
    return out


def compare_qualifications(
    a: dict[str, Any], b: dict[str, Any]
) -> list[tuple[str | None, str | None, float]]:
    """Match K items by text; unmatched ones keep None on the other side."""
    return _match_texts(
        a.get("qualifications", []), b.get("qualifications", []), "text"
    )


def compare_hypotheses(
    a: dict[str, Any], b: dict[str, Any]
) -> list[tuple[str | None, str | None, float]]:
    """Match H items by what they assume; unmatched ones keep None on the other side."""
    return _match_texts(a.get("hypotheses", []), b.get("hypotheses", []), "assumes")


def compare_boards(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """The boards the records make of their profile's templates, matched by id:
    one line each, in both or in one, with a changed template or label and the
    elements on it in A and in B. Empty when neither record has such boards."""
    in_a = {x["id"]: x for x in a.get("boards", [])}
    in_b = {x["id"]: x for x in b.get("boards", [])}

    def count(record: dict[str, Any], bid: str) -> int:
        return sum(1 for e in record["elements"] if e["board"] == bid)

    out = []
    for bid in [*in_a, *(i for i in in_b if i not in in_a)]:
        x, y = in_a.get(bid), in_b.get(bid)
        side = "both" if x and y else "only A" if x else "only B"
        label = (y or x or {})["label"]
        line = (
            f"- {side} `{bid}` {label} (elements: A {count(a, bid)}, B {count(b, bid)})"
        )
        if x and y:
            for field in ("template", "label", "unfolds", "seen_from"):
                if x.get(field) != y.get(field):
                    line += f"; {field} {x.get(field)} / {y.get(field)}"
        out.append(line)
    return out


def compare_continuum(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Ontology records matched by id, with `lives_in`, `tempos`, `horizon`
    and `covers` in A and in B: one line each for a record that has any of
    them on either side. Empty when no ontology record of either has them."""
    in_a = {o["id"]: o for o in a.get("ontology", [])}
    in_b = {o["id"]: o for o in b.get("ontology", [])}
    out = []
    for oid in [*in_a, *(i for i in in_b if i not in in_a)]:
        x, y = in_a.get(oid), in_b.get(oid)
        px, py = continuum_parts(x or {}), continuum_parts(y or {})
        if not (px or py):
            continue
        side = "both" if x and y else "only A" if x else "only B"
        line = f"- {side} `{oid}` {(y or x or {})['object']}"
        for key in CONTINUUM:
            if x and y and (key in px or key in py):
                line += f"; {key} {px.get(key, '-')} / {py.get(key, '-')}"
            elif key in px or key in py:
                line += f"; {key} {px.get(key) or py.get(key)}"
        out.append(line)
    return out


def lenses(record: dict[str, Any]) -> set[str]:
    """Lenses a board set used, read from elements, theses, hypotheses, ontology."""
    items = (
        record["elements"]
        + record.get("theses", [])
        + record.get("hypotheses", [])
        + record.get("ontology", [])
    )
    return {str(i["lens"]) for i in items if i.get("lens")}


def report(a: dict[str, Any], b: dict[str, Any]) -> str:
    """Markdown report of the comparison, grouped as positions, frames, ..."""
    pairs = compare(a, b)
    label_a = {e["id"]: e["label"] for e in a["elements"]}
    label_b = {e["id"]: e["label"] for e in b["elements"]}
    counts: dict[str, int] = {}
    for p in pairs:
        counts[p.kind] = counts.get(p.kind, 0) + 1
    out = [
        f"# Comparison: `{a['id']}` (A) and `{b['id']}` (B)",
        "",
        " · ".join(
            f"{k} {counts.get(k, 0)}"
            for k in ("agreement", "refinement", "conflict", "only_a", "only_b")
        ),
        "",
        "Matching is by wording within a group of kinds; check each line.",
        "",
    ]
    for group in [*groups_of(a, b), "other"]:
        rows = [p for p in pairs if p.group == group]
        if not rows:
            continue
        out += [
            f"## {group}",
            "",
            "| | A | B | score | note |",
            "|---|---|---|---|---|",
        ]
        for p in sorted(rows, key=lambda p: (p.kind, -p.score)):
            cell_a = f"`{p.a}` {label_a[p.a]}" if p.a else ""
            cell_b = f"`{p.b}` {label_b[p.b]}" if p.b else ""
            out.append(f"| {p.kind} | {cell_a} | {cell_b} | {p.score:.2f} | {p.note} |")
        out.append("")
    boards = compare_boards(a, b)
    if boards:
        out += ["## boards", ""] + boards + [""]
    continuum = compare_continuum(a, b)
    if continuum:
        out += ["## ontology: continuum", ""] + continuum + [""]
    lenses_a, lenses_b = lenses(a), lenses(b)
    if lenses_a | lenses_b:
        out += [
            "## lenses",
            "",
            "- both: " + (", ".join(sorted(lenses_a & lenses_b)) or "-"),
            "- only A: " + (", ".join(sorted(lenses_a - lenses_b)) or "-"),
            "- only B: " + (", ".join(sorted(lenses_b - lenses_a)) or "-"),
            "",
        ]
    ks = compare_qualifications(a, b)
    if ks:
        out += ["## qualifications", ""]
        for ka, kb, score in ks:
            out.append(f"- A {ka or '-'} / B {kb or '-'} ({score:.2f})")
        out.append("")
    return "\n".join(out)


def merge(a: dict[str, Any], b: dict[str, Any], new_id: str) -> dict[str, Any]:
    """Propose a merge as a new cycle on top of b.

    Elements only in a are imported with a lineage tag and `epistemic: hypothesis`;
    each conflict becomes an open K. Matched elements keep b's version.
    """
    pairs = compare(a, b)
    a_by_id = {e["id"]: e for e in a["elements"]}
    b_ids = {e["id"] for e in b["elements"]}
    rename = {p.a: p.b for p in pairs if p.a and p.b}
    imported: list[dict[str, Any]] = []
    for p in pairs:
        if p.kind != "only_a" or p.a is None:
            continue
        new = p.a if p.a not in b_ids else f"a-{p.a}"
        rename[p.a] = new
    kinds = {e["id"]: e["kind"] for e in b["elements"]}
    kinds.update(
        {rename[p.a]: a_by_id[p.a]["kind"] for p in pairs if p.kind == "only_a" and p.a}
    )
    for p in pairs:
        if p.kind != "only_a" or p.a is None:
            continue
        el = dict(a_by_id[p.a])
        el["id"] = rename[p.a]
        el["epistemic"] = "hypothesis"
        el["lineage"] = sorted(set(el.get("lineage", [])) | {f"from-{a['id']}"[:60]})
        el.pop("geom", None)
        for field, allowed in (
            ("seen_from", ("position",)),
            ("assigned_by", ("position", "place_for_others")),
            ("performed_by", ("position", "place_for_others")),
        ):
            if field in el:
                target = rename.get(el[field])
                if target and kinds.get(target) in allowed:
                    el[field] = target
                else:
                    del el[field]
        # Element links only; a's thesis ids say nothing in b.
        for field in ("in", "arises_from"):
            if field in el:
                el[field] = [rename[c] for c in el[field] if c in rename]
                if not el[field]:
                    del el[field]
        el.pop("move", None)
        imported.append(el)
    ks = list(b.get("qualifications", []))
    n = max((int(q["id"][1:]) for q in ks), default=0)
    for p in pairs:
        if p.kind != "conflict":
            continue
        n += 1
        ks.append(
            {
                "id": f"K{n}",
                "targets": [p.b],
                "text": f"conflict with {a['id']}:{p.a}: {p.note}",
                "by": "compare",
                "status": "open",
                "raised_in": b["cycle"] + 1,
                "note": "options: lock (keep B), fork (keep both), rebase, merge",
            }
        )
    merged = {
        k: v for k, v in b.items() if k not in ("signoffs", "checked_by", "state")
    }
    # b's decisions stand in the new cycle; a draft carries no verification.
    signoffs = [s for s in b.get("signoffs", []) if s["function"] != "verify_record"]
    if signoffs:
        merged["signoffs"] = signoffs
    merged.update(
        id=new_id,
        title=f"Merge proposal: {b['title']} + {a['id']}",
        cycle=b["cycle"] + 1,
        revises=b["id"],
        status="draft",
        elements=list(b["elements"]) + imported,
        qualifications=ks,
        lineage=sorted(set(b.get("lineage", [])) | set(a.get("lineage", []))),
    )
    merged.pop("reflected_from", None)
    merged = _with_boards_of_a(merged, a, b, rename, kinds)
    merged["sources"] = sorted(set(b.get("sources", [])) | set(a.get("sources", [])))
    if not merged["lineage"]:
        del merged["lineage"]
    return merged


def _with_boards_of_a(
    merged: dict[str, Any],
    a: dict[str, Any],
    b: dict[str, Any],
    rename: dict[str, str],
    kinds: dict[str, str],
) -> dict[str, Any]:
    """The merge with a's record boards that b lacks (by id), so that the
    elements imported onto them keep a board; their links are remapped like
    an element's, and dropped when they point nowhere or, for `unfolds`, to a
    kind the template does not unfold."""
    have = {x["id"] for x in b.get("boards", [])}
    profile = profile_of(b)
    extra = []
    for raw in a.get("boards", []):
        if raw["id"] in have:
            continue
        board = dict(raw)
        template = profile.template(board["template"])
        unfolds = template.unfolds if template and template.unfolds else None
        for field, allowed in (("seen_from", ("position",)), ("unfolds", unfolds)):
            if field in board:
                target = rename.get(board[field])
                if target and (allowed is None or kinds.get(target) in allowed):
                    board[field] = target
                else:
                    del board[field]
        extra.append(board)
    if not extra:
        return merged
    out: dict[str, Any] = {}
    for key, value in merged.items():
        if key == "elements":
            out["boards"] = list(b.get("boards", [])) + extra
        if key != "boards":
            out[key] = value
    return out
