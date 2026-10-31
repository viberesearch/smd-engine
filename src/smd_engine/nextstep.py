"""`smd next`: which procedure to run next on a board set.

Candidates come from two places. Every hint finding of the validator carries the
procedure and section that act on it (`HINT_PROCEDURES`, `validate/context.py`),
and each is a candidate with the hint's message as its reason; a hint that points
to a document and not to a procedure (`docs/checks.md`) is shown as a note. The
conditions that are not hints stay explicit rules in `RULES`. The candidates are
then put in the one order ORDER, each procedure once: the first is the proposal,
the next two the alternatives. A procedure written for another profile than the
record's is skipped (`smd pack` would refuse it). There is no model in it: the
same record gives the same answer, and the answer is a proposal. What the group
or the owner has to decide (open K, AI variants) is reported beside it, since it
is not a procedure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, NamedTuple

from smd_engine.pack import asset_root, procedure_ids, procedure_profile
from smd_engine.validate import Finding, validate_record

MAX_ALSO = 2  # alternatives shown after the first choice
CLIP = 200  # characters of a hint's message shown as the reason

# The step procedures of `solo-session`, section 3, in its order.
SOLO_ORDER = (
    "small-situation",
    "visionary-tract",
    "positional-construction",
    "functional-plan",
    "problematization",
    "qualification-pass",
    "reflexive-protocol",
)

# The one order of the candidates. Gate 0 (RULES) ranks before all of them:
# `solo-session` section 2 puts the reflexive answers of the cycle before step 1.
# Then the step-2 procedures, which lay information on the board
# (`ingest-transcript`, `theses-to-board`, `field-result`; `procedures/README.md`,
# the hint `information-without-cell`, GP-Guide11 paragraph 5), then the steps 1 to
# 6 of `solo-session` section 3, with `stakeholder-ontology` before the positional
# construction (the note under that table). `reflexive-protocol` closes the cycle
# (step 7) and `solo-session`, which only orders the others, is last.
ORDER = (
    "ingest-transcript",
    "theses-to-board",
    "field-result",
    "small-situation",
    "visionary-tract",
    "stakeholder-ontology",
    "positional-construction",
    "functional-plan",
    "problematization",
    "qualification-pass",
    "reflexive-protocol",
    "solo-session",
)
OPENING = -1  # the rank of gate 0
# Everything before the closing: a hint that points to one holds the closing back.
STEPS = ORDER[: ORDER.index("qualification-pass") + 1]


def fits(procedure: str, profile: str) -> bool:
    """Whether the procedure works on records of the profile."""
    wanted = procedure_profile(asset_root() / "procedures" / f"{procedure}.md")
    return wanted in ("any", profile)


def first_procedure(profile: str) -> str:
    """The first step of the solo-session order the profile can run."""
    return next(p for p in SOLO_ORDER if fits(p, profile))


def split_target(target: str) -> tuple[str, str]:
    """The procedure id and the section of a hint's target, such as
    `procedures/functional-plan.md §4`; the id is empty for a target that is not
    a procedure (`docs/checks.md`)."""
    path, _, section = target.partition(" §")
    where = PurePosixPath(path)
    if where.parent.name == "procedures" and where.suffix == ".md":
        return where.stem, section
    return "", section


def _clip(text: str) -> str:
    if len(text) <= CLIP:
        return text
    return text[:CLIP].rsplit(" ", 1)[0].rstrip(",;:") + " ..."


@dataclass
class Facts:
    """What the rules read: the record, and its hint findings."""

    record: dict[str, Any]
    profile: str
    hints: list[Finding] = field(default_factory=list)

    @property
    def unplaced(self) -> list[str]:
        """Theses that feed no element and are about none."""
        return [
            t["id"]
            for t in self.record.get("theses", [])
            if not t.get("feeds") and not t.get("about")
        ]

    def pointing_to(self, procedure: str, section: str | None = None) -> list[Finding]:
        """The hints whose procedure is this one (and its section, if given)."""
        return [
            f
            for f in self.hints
            if split_target(f.procedure)[0] == procedure
            and section in (None, split_target(f.procedure)[1])
        ]

    @property
    def open_k(self) -> list[str]:
        return [
            q["id"]
            for q in self.record.get("qualifications", [])
            if q["status"] != "closed"
        ]

    @property
    def testing(self) -> list[str]:
        return [
            h["id"]
            for h in self.record.get("hypotheses", [])
            if h["status"] == "testing"
        ]

    @property
    def ai_variants(self) -> list[str]:
        return [
            t["id"]
            for t in self.record.get("theses", [])
            if t["status"] == "ai_variant"
        ]

    @property
    def reflexive_gaps(self) -> list[str]:
        """What a revising cycle leaves out of its reflexive exit."""
        if not self.record.get("revises"):
            return []
        state = self.record.get("state") or {}
        return [
            what
            for key, what, present in (
                (
                    "reflected_from",
                    "names no reflexive position (reflected_from)",
                    True,
                ),
                ("difficulty", "does not say what failed (state.difficulty)", False),
            )
            if not (self.record.get(key) if present else state.get(key))
        ]

    @property
    def steps_pending(self) -> bool:
        """A procedure before the closing still has a hint, or no K is raised yet."""
        return not self.record.get("qualifications") or any(
            self.pointing_to(p) for p in STEPS
        )


def _list(ids: list[str], limit: int = 4) -> str:
    more = f" and {len(ids) - limit} more" if len(ids) > limit else ""
    return ", ".join(ids[:limit]) + more


class Rule(NamedTuple):
    """A condition that no hint reports: the procedure and section it points
    to, and why. `opening` ranks the rule before ORDER (gate 0)."""

    condition: Callable[[Facts], bool]
    procedure: str
    section: str
    reason: Callable[[Facts], str]
    opening: bool = False


RULES: list[Rule] = [
    Rule(
        lambda f: bool(f.reflexive_gaps),
        "reflexive-protocol",
        "2",
        lambda f: f"cycle {f.record['cycle']} revises {f.record['revises']} but "
        + " and ".join(f.reflexive_gaps)
        + "; the reflexive questions come first (gate 0)",
        True,
    ),
    Rule(
        # a hint at section 2 (information without a cell, an unanchored
        # transition) already says what to lay out; section 3 (E3) does not
        lambda f: bool(f.unplaced) and not f.pointing_to("theses-to-board", "2"),
        "theses-to-board",
        "2",
        lambda f: f"{len(f.unplaced)} thesis(es) feed no element and are about none: "
        + _list(f.unplaced),
    ),
    Rule(
        lambda f: not f.record.get("qualifications"),
        "qualification-pass",
        "3",
        lambda f: "no K raised yet; the record is not checked against the criteria",
    ),
    Rule(
        lambda f: not f.record.get("theses") and f.record["cycle"] == 1,
        "ingest-transcript",
        "0",
        lambda f: "a first cycle with no theses; if there is a recorded group talk, "
        "start from it (smd next cannot see the sources)",
    ),
    Rule(
        lambda f: bool(f.testing),
        "field-result",
        "1",
        lambda f: f"{len(f.testing)} hypothesis(es) in testing ({_list(f.testing)}); "
        "if the field gave an artefact, record the result",
    ),
    Rule(
        lambda f: not f.steps_pending,
        "reflexive-protocol",
        "7",
        lambda f: "no hint is open before the closing; the reflexive protocol closes "
        "the cycle and opens the next",
    ),
]


@dataclass(frozen=True)
class Advice:
    procedure: str
    sections: tuple[str, ...]
    reason: str

    @property
    def label(self) -> str:
        """The procedure with its sections: `functional-plan §3, §4`."""
        marks = ", ".join(f"§{s}" for s in self.sections)
        return f"{self.procedure} {marks}".rstrip()


class _Candidate(NamedTuple):
    procedure: str
    section: str
    reason: str
    rank: int


def advise(record: dict[str, Any]) -> tuple[list[Advice], Facts]:
    """The procedures proposed for a validated board set, best first: each
    procedure once, only those that exist and fit the record's profile, in the
    order ORDER (gate 0 first). A procedure keeps the reason of its first
    candidate and the sections of all of them."""
    findings = validate_record(record)
    facts = Facts(
        record,
        str(record.get("profile", "program-three-boards")),
        [f for f in findings if f.level == "hint"],
    )
    known = set(procedure_ids(asset_root()))
    candidates: list[_Candidate] = []
    for rule in RULES:
        if rule.condition(facts):
            rank = OPENING if rule.opening else ORDER.index(rule.procedure)
            candidates.append(
                _Candidate(rule.procedure, rule.section, rule.reason(facts), rank)
            )
    for hint in facts.hints:
        procedure, section = split_target(hint.procedure)
        if procedure in ORDER:
            reason = _clip(f"{hint.ref}: {hint.message}")
            candidates.append(
                _Candidate(procedure, section, reason, ORDER.index(procedure))
            )
    advice: dict[str, Advice] = {}
    for cand in sorted(candidates, key=lambda c: c.rank):
        if cand.procedure not in known or not fits(cand.procedure, facts.profile):
            continue
        seen = advice.get(cand.procedure)
        if seen is None:
            sections = (cand.section,) if cand.section else ()
            advice[cand.procedure] = Advice(cand.procedure, sections, cand.reason)
        elif cand.section and cand.section not in seen.sections:
            advice[cand.procedure] = Advice(
                seen.procedure, seen.sections + (cand.section,), seen.reason
            )
    return list(advice.values())[: 1 + MAX_ALSO], facts


def notes(facts: Facts) -> list[str]:
    """The hints that point to a document and not to a procedure."""
    return [
        f"{_clip(f'{h.ref}: {h.message}')} ({h.procedure})"
        for h in facts.hints
        if not split_target(h.procedure)[0]
    ]


def render_next(record: dict[str, Any], path: str) -> str:
    """The text `smd next` prints."""
    advice, facts = advise(record)
    waiting = [
        f"{len(ids)} {what}"
        for ids, what in (
            (facts.open_k, "K not closed"),
            (facts.ai_variants, "AI variant(s) awaiting the group"),
            (facts.record.get("state", {}).get("open", []), "item(s) in state.open"),
        )
        if ids
    ]
    lines = [f"{record['id']}: cycle {record['cycle']}, profile {facts.profile}"]
    if waiting:
        lines.append("waiting for people, not a procedure: " + "; ".join(waiting))
    lines.append("")
    if not advice:
        lines.append(
            "No rule fires: no hint is open for this profile before the closing, and "
            "nothing is in testing. Decide the open items, or run a procedure by hand."
        )
    else:
        first, *also = advice
        lines += [
            f"Next: {first.label}",
            f"  why: {first.reason}",
            f"  run: smd pack {first.procedure} {path} -o pack.md",
        ]
        if also:
            lines.append("Also:")
            lines += [f"  {a.label}: {a.reason}" for a in also]
    side = notes(facts)
    if side:
        lines.append("Note (advice, no procedure):")
        lines += [f"  {n}" for n in side]
    return "\n".join(lines) + "\n"
