"""Compare a procedure run with an expected record: did a model change make it worse.

The run is board set A and the expected record is board set B of
`compare.compare`, so `only_b` counts what the expected record has and the run
missed. Theses are matched by the address they cite, not by wording: the same
source id and, for a timecode, a time within WINDOW seconds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from smd_engine.compare import compare, compare_hypotheses, compare_qualifications

WINDOW = 30  # seconds between two timecodes that still name the same utterance
KINDS = ("agreement", "refinement", "conflict", "only_a", "only_b")


@dataclass(frozen=True)
class Address:
    source: str
    params: tuple[tuple[str, str], ...]  # every address key except t
    seconds: int | None  # the t= timecode, if the address has one


@dataclass(frozen=True)
class ThesisMatch:
    run: str
    expected: str
    run_cite: str
    expected_cite: str


@dataclass
class EvalResult:
    counts: dict[str, int]
    matched: list[ThesisMatch]
    only_run: list[tuple[str, str]]  # (thesis id, cites)
    only_expected: list[tuple[str, str]]
    failures: list[str] = field(default_factory=list)
    run_block: dict[str, Any] | None = None  # the run's `run` stamp
    expected_block: dict[str, Any] | None = None  # the expected record's stamp
    # K and H matched by wording: (run id, expected id) pairs, then the ids left over
    qualifications: ItemMatch | None = None
    hypotheses: ItemMatch | None = None


@dataclass
class ItemMatch:
    matched: list[tuple[str, str]]
    only_run: list[str]
    only_expected: list[str]


def _item_match(pairs: list[tuple[str | None, str | None, float]]) -> ItemMatch:
    return ItemMatch(
        [(a, b) for a, b, _ in pairs if a and b],
        [a for a, b, _ in pairs if a and not b],
        [b for a, b, _ in pairs if b and not a],
    )


def parse_cite(cite: str) -> Address:
    """Split `s3#t=00:08:10` into source id, other address keys and seconds."""
    source, _, fragment = cite.partition("#")
    params: list[tuple[str, str]] = []
    seconds: int | None = None
    for part in fragment.split("&") if fragment else []:
        key, _, value = part.partition("=")
        stamp = re.fullmatch(r"(\d+):(\d{2}):(\d{2})", value)
        if key == "t" and stamp:
            h, m, s = (int(x) for x in stamp.groups())
            seconds = h * 3600 + m * 60 + s
        else:
            params.append((key, value))
    return Address(source, tuple(sorted(params)), seconds)


def _distance(a: Address, b: Address) -> int | None:
    """Seconds apart if the two addresses name the same place, else None."""
    if a.source != b.source or a.params != b.params:
        return None
    if a.seconds is None or b.seconds is None:
        return 0 if a.seconds is b.seconds else None
    gap = abs(a.seconds - b.seconds)
    return gap if gap <= WINDOW else None


def match_theses(
    run: dict[str, Any], expected: dict[str, Any]
) -> tuple[list[ThesisMatch], list[tuple[str, str]], list[tuple[str, str]]]:
    """Pair theses one to one by cites, the smallest time gap first."""
    ra, ex = run.get("theses", []), expected.get("theses", [])
    candidates: list[tuple[int, int, int, str, str]] = []
    for i, ta in enumerate(ra):
        for j, tb in enumerate(ex):
            best: tuple[int, str, str] | None = None
            for ca in ta.get("cites", []):
                for cb in tb.get("cites", []):
                    gap = _distance(parse_cite(ca), parse_cite(cb))
                    if gap is not None and (best is None or gap < best[0]):
                        best = (gap, ca, cb)
            if best:
                candidates.append((best[0], i, j, best[1], best[2]))
    matched: list[ThesisMatch] = []
    used_a: set[int] = set()
    used_b: set[int] = set()
    for _, i, j, ca, cb in sorted(candidates):
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        matched.append(ThesisMatch(ra[i]["id"], ex[j]["id"], ca, cb))
    matched.sort(key=lambda m: m.expected)
    only_run = [_unmatched(t) for i, t in enumerate(ra) if i not in used_a]
    only_expected = [_unmatched(t) for j, t in enumerate(ex) if j not in used_b]
    return matched, only_run, only_expected


def _unmatched(thesis: dict[str, Any]) -> tuple[str, str]:
    return thesis["id"], ", ".join(thesis.get("cites", [])) or "no cites"


def evaluate(
    run: dict[str, Any],
    expected: dict[str, Any],
    min_agreement: int | None = None,
    max_only_expected: int | None = None,
) -> EvalResult:
    counts = dict.fromkeys(KINDS, 0)
    for pair in compare(run, expected):
        counts[pair.kind] += 1
    matched, only_run, only_expected = match_theses(run, expected)
    result = EvalResult(
        counts,
        matched,
        only_run,
        only_expected,
        run_block=run.get("run"),
        expected_block=expected.get("run"),
        qualifications=_item_match(compare_qualifications(run, expected)),
        hypotheses=_item_match(compare_hypotheses(run, expected)),
    )
    if min_agreement is not None and counts["agreement"] < min_agreement:
        result.failures.append(
            f"agreement {counts['agreement']} is below the minimum {min_agreement}"
        )
    if max_only_expected is not None and counts["only_b"] > max_only_expected:
        result.failures.append(
            f"only_expected {counts['only_b']} is above the maximum {max_only_expected}"
        )
    return result


def _stamp_value(value: Any) -> str:
    """A stamp value as text; `inputs` (source id to sha256) as `{s1: <sha256>, ...}`."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {v}" for k, v in value.items()) + "}"
    return str(value)


def _stamp(block: dict[str, Any] | None) -> str:
    """The `run` block as `key=value` pairs, or `none` when the record has no stamp."""
    if not block:
        return "none"
    return ", ".join(f"{k}={_stamp_value(v)}" for k, v in block.items())


def format_result(result: EvalResult) -> str:
    """Plain text: the five counts, the run blocks, the theses, K and H."""
    out = [" · ".join(f"{k} {result.counts[k]}" for k in KINDS), ""]
    out.append(f"run: {_stamp(result.run_block)}")
    out.append(f"expected: {_stamp(result.expected_block)}")
    out.append("")
    out.append(f"theses matched by cites ({len(result.matched)}):")
    for m in result.matched:
        out.append(f"  {m.run} = {m.expected}  {m.run_cite} / {m.expected_cite}")
    out.append(f"theses only in the run ({len(result.only_run)}):")
    out += [f"  {tid}  {cites}" for tid, cites in result.only_run]
    out.append(f"theses only in the expected record ({len(result.only_expected)}):")
    out += [f"  {tid}  {cites}" for tid, cites in result.only_expected]
    for name, items in (
        ("qualifications", result.qualifications),
        ("hypotheses", result.hypotheses),
    ):
        if items is None:
            continue
        out.append(f"{name} matched by wording ({len(items.matched)}):")
        out += [f"  {a} = {b}" for a, b in items.matched]
        out.append(f"{name} only in the run ({len(items.only_run)}):")
        out += [f"  {i}" for i in items.only_run]
        out.append(f"{name} only in the expected record ({len(items.only_expected)}):")
        out += [f"  {i}" for i in items.only_expected]
    for failure in result.failures:
        out.append(f"FAIL: {failure}")
    return "\n".join(out) + "\n"
