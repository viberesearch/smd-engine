"""`smd next`: which procedure to run next on a board set, by a rule table.

The table RULES is the one place where the choice is written. It is read top to
bottom; the first rule whose condition holds names the procedure to run, the next
two name alternatives. Each rule is (condition, procedure, reason). The order
follows `procedures/solo-session.md` (section 3) and the `next` keys of
`procedures/README.md`; a procedure written for another profile than the
record's is skipped (`smd pack` would refuse it). There is no model in it: the
same record gives the same answer, and the answer is a proposal. What the group
or the owner has to decide (open K, AI variants) is reported beside it, since it
is not a procedure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, NamedTuple

from smd_engine.pack import asset_root, procedure_ids, procedure_profile
from smd_engine.validate import Finding, validate_record

MAX_ALSO = 2  # alternatives shown after the first choice

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


def fits(procedure: str, profile: str) -> bool:
    """Whether the procedure works on records of the profile."""
    wanted = procedure_profile(asset_root() / "procedures" / f"{procedure}.md")
    return wanted in ("any", profile)


def first_procedure(profile: str) -> str:
    """The first step of the solo-session order the profile can run."""
    return next(p for p in SOLO_ORDER if fits(p, profile))


@dataclass
class Facts:
    """What the rules read: the record, and its hint findings by wording."""

    record: dict[str, Any]
    profile: str
    hints: list[Finding] = field(default_factory=list)

    def hinted(self, text: str) -> list[Finding]:
        return [f for f in self.hints if text in f.message]

    @property
    def unplaced(self) -> list[str]:
        """Theses that feed no element and are about none."""
        return [
            t["id"]
            for t in self.record.get("theses", [])
            if not t.get("feeds") and not t.get("about")
        ]

    @property
    def empty_halves(self) -> list[str]:
        """`small` and `big` for a halved board with that half empty."""
        return [f.ref for f in self.hinted("situation not laid out")]

    @property
    def no_scheme_block(self) -> list[str]:
        """Gaps and problems tied to no block of a named scheme."""
        found = self.hinted("names no scheme block") + self.hinted("tied to a block")
        return sorted({f.ref for f in found})

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
        """Any of the steps 1 to 6 of the solo-session order still shows a hint."""
        return bool(
            self.empty_halves
            or self.hinted("positional set looks incomplete")
            or self.frame_hints
            or self.no_scheme_block
            or not self.record.get("qualifications")
        )

    @property
    def frame_hints(self) -> list[Finding]:
        return self.hinted("new frame has no functional plan") + self.hinted(
            "name no position that performs"
        )


def _list(ids: list[str], limit: int = 4) -> str:
    more = f" and {len(ids) - limit} more" if len(ids) > limit else ""
    return ", ".join(ids[:limit]) + more


class Rule(NamedTuple):
    condition: Callable[[Facts], bool]
    procedure: str
    reason: Callable[[Facts], str]


# In order: the first that holds is the proposal, the next two the alternatives.
RULES: list[Rule] = [
    Rule(
        lambda f: bool(f.reflexive_gaps),
        "reflexive-protocol",
        lambda f: f"cycle {f.record['cycle']} revises {f.record['revises']} but "
        + " and ".join(f.reflexive_gaps)
        + "; the reflexive questions come first (gate 0)",
    ),
    Rule(
        lambda f: bool(f.unplaced),
        "theses-to-board",
        lambda f: f"{len(f.unplaced)} thesis(es) feed no element and are about none: "
        + _list(f.unplaced),
    ),
    Rule(
        lambda f: any(h.endswith("small") for h in f.empty_halves),
        "small-situation",
        lambda f: "the small situation is not laid out; the four questions come first",
    ),
    Rule(
        lambda f: any(h.endswith("big") for h in f.empty_halves),
        "visionary-tract",
        lambda f: "the big situation is not laid out",
    ),
    Rule(
        lambda f: bool(f.hinted("positional set looks incomplete")),
        "positional-construction",
        lambda f: "the positional set looks incomplete: "
        + f.hinted("positional set looks incomplete")[0].message.split(": ")[0],
    ),
    Rule(
        lambda f: bool(f.frame_hints),
        "functional-plan",
        lambda f: f"{f.frame_hints[0].ref}: " + f.frame_hints[0].message,
    ),
    Rule(
        lambda f: bool(f.no_scheme_block),
        "problematization",
        lambda f: "gaps or problems name no block of a named scheme: "
        + _list(f.no_scheme_block),
    ),
    Rule(
        lambda f: not f.record.get("qualifications"),
        "qualification-pass",
        lambda f: "no K raised yet; the record is not checked against the criteria",
    ),
    Rule(
        lambda f: not f.record.get("theses") and f.record["cycle"] == 1,
        "ingest-transcript",
        lambda f: "a first cycle with no theses; if there is a recorded group talk, "
        "start from it (smd next cannot see the sources)",
    ),
    Rule(
        lambda f: bool(f.testing),
        "field-result",
        lambda f: f"{len(f.testing)} hypothesis(es) in testing ({_list(f.testing)}); "
        "if the field gave an artefact, record the result",
    ),
    Rule(
        lambda f: not f.steps_pending,
        "reflexive-protocol",
        lambda f: "steps 1 to 6 show no open hint; the reflexive protocol closes "
        "the cycle and opens the next",
    ),
]


@dataclass(frozen=True)
class Advice:
    procedure: str
    reason: str


def advise(record: dict[str, Any]) -> tuple[list[Advice], Facts]:
    """The procedures the rules propose for a validated board set, best first:
    each procedure once, only those that exist and fit the record's profile."""
    findings = validate_record(record)
    facts = Facts(
        record,
        str(record.get("profile", "program-three-boards")),
        [f for f in findings if f.level == "hint"],
    )
    known = procedure_ids(asset_root())
    out: list[Advice] = []
    for rule in RULES:
        if (
            rule.procedure in known
            and fits(rule.procedure, facts.profile)
            and rule.procedure not in [a.procedure for a in out]
            and rule.condition(facts)
        ):
            out.append(Advice(rule.procedure, rule.reason(facts)))
    return out[: 1 + MAX_ALSO], facts


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
            "No rule fires: steps 1 to 6 show no open hint for this profile, and "
            "nothing is in testing. Decide the open items, or run a procedure by hand."
        )
        return "\n".join(lines) + "\n"
    first, *also = advice
    lines += [
        f"Next: {first.procedure}",
        f"  why: {first.reason}",
        f"  run: smd pack {first.procedure} {path} -o pack.md",
    ]
    if also:
        lines.append("Also:")
        lines += [f"  {a.procedure}: {a.reason}" for a in also]
    return "\n".join(lines) + "\n"
