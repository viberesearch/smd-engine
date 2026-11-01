"""What every check receives: the record and the lookups built once from it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import wraps
from typing import Any, Literal

from smd_engine.profile import Profile, default_profile, profile_of

AI_VOICES = {"ai", "ии"}


def is_ai(voice: str | None) -> bool:
    return (voice or "").strip().lower() in AI_VOICES


@dataclass(frozen=True)
class Finding:
    level: Literal["error", "warning", "hint"]
    ref: str
    message: str
    # Where the method says how to act on it: a procedure and its section
    # (HINT_PROCEDURES for a hint); printed by `smd validate`, not compared.
    procedure: str = field(default="", compare=False)

    def __str__(self) -> str:
        return f"{self.level}: {self.ref}: {self.message}"


@dataclass
class Ctx:
    record: dict[str, Any]
    by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    theses: dict[str, dict[str, Any]] = field(default_factory=dict)
    ks: dict[str, dict[str, Any]] = field(default_factory=dict)
    hyps: dict[str, dict[str, Any]] = field(default_factory=dict)
    # The profile a board set follows: its boards, kinds and hints.
    profile: Profile = field(default_factory=default_profile)
    source_ids: set[str] | None = None
    # Source id to its manifest `kind`, when a manifest is given.
    source_kinds: dict[str, str] | None = None
    previous: dict[str, Any] | None = None
    # Taxonomy id to its value ids, when a taxonomy file is given.
    taxonomies: dict[str, set[str]] | None = None


Check = Callable[[Ctx], list[Finding]]

# Method hints by string id, so a profile can name the ones it enables.
HINTS: dict[str, Check] = {}

# The procedure and section that act on each hint, by hint id; a finding that
# names its own (one half of the situation board, say) keeps it. board-dense
# has no procedure: docs/checks.md says how to fold or split a board.
HINT_PROCEDURES = {
    # Girenko's criteria for a group screen (hints.py)
    "entry": "procedures/small-situation.md §0",
    "empty-boards": "procedures/solo-session.md §3",
    "situation-halves": "procedures/small-situation.md §2",
    "positions": "procedures/positional-construction.md §2",
    "new-frames": "procedures/functional-plan.md §2",
    "gaps": "procedures/problematization.md §5",
    "open-qualifications": "procedures/reflexive-protocol.md §6",
    "candidate-moves": "procedures/reflexive-protocol.md §6",
    "problems": "procedures/problematization.md §3",
    "belts": "procedures/qualification-pass.md §3.3",
    "ontology": "procedures/positional-construction.md §5",
    "ontology-outlives-pace": "procedures/stakeholder-ontology.md §5",
    "difficulty": "procedures/reflexive-protocol.md §2",
    "revise-if": "procedures/small-situation.md §4",
    "ai-drafts": "procedures/qualification-pass.md §3.4",
    "ai-variants": "procedures/reflexive-protocol.md §6",
    "no-new-scheme": "procedures/reflexive-protocol.md §5",
    "board-dense": "docs/checks.md",
    # The typed standard and the decision rule of hypotheses (hypotheses.py)
    "hypothesis-type": "procedures/field-result.md §0.1",
    "type-status": "procedures/field-result.md §0.1",
    "hypothesis-rule": "procedures/field-result.md §0.2",
    "rule-basis": "procedures/field-result.md §0.2",
    "rule-n-min": "procedures/field-result.md §0.2",
    "verdict": "procedures/field-result.md §3",
    # robustness rules R1 and R6 (docs/method/robustness-rules.md)
    "domain-sample": "procedures/field-result.md §0.2",
    "surprise": "procedures/field-result.md §3",
    # G.P.'s «Программа действий» (hints.py)
    "object-from-inside": "procedures/positional-construction.md §4",
    "external-without-reflection": "procedures/reflexive-protocol.md §2",
    "goal-without-breakdown": "procedures/problematization.md §5",
    "position-without-object": "procedures/positional-construction.md §4",
    "ought-without-fact": "procedures/theses-to-board.md §2",
    "design-the-natural": "procedures/qualification-pass.md §3.3",
    "information-without-cell": "procedures/theses-to-board.md §2",
    "cells-from-information": "procedures/ingest-transcript.md §0",
    # Graph signatures of the procedures (graph.py)
    "function-flows": "procedures/functional-plan.md §4",
    "unlinked-functions": "procedures/functional-plan.md §4",
    "idle-positions": "procedures/functional-plan.md §4",
    # AI on the boards, gate ИИ1 Б (ai.py)
    "ai-decision-unanswered": "procedures/functional-plan.md §3",
    "red-line-without-value": "procedures/functional-plan.md §4",
    "red-line-outlives-pace": "procedures/functional-plan.md §4",
    # red lines read from observations, gate КЛ1 В (redlines.py)
    "red-line-breach": "procedures/field-result.md §5",
    "red-line-expired": "procedures/field-result.md §5",
    "positions-unlinked": "procedures/positional-construction.md §3",
    "object-isolated": "procedures/theses-to-board.md §3",
    "isolated-facts": "procedures/small-situation.md §3",
    "jump-to-frame": "procedures/small-situation.md §2",
    "transition-unanchored": "procedures/theses-to-board.md §2",
    # Self-checks of the procedures (ontology.py, tract.py)
    "ai-cooperation": "procedures/positional-construction.md §5",
    "cooperation-flows": "procedures/positional-construction.md §5",
    "translation-loss": "procedures/stakeholder-ontology.md §5",
    "garland": "procedures/visionary-tract.md §3",
    "bridge-from": "procedures/visionary-tract.md §5",
    "move-via": "procedures/visionary-tract.md §1",
    # G.P.'s management scheme and the Beer layer (management.py): no
    # procedure builds that scheme, so the classic checks read it
    "lead-vs-manage": "procedures/qualification-pass.md §3.3",
    "manage-via-organizedness": "procedures/qualification-pass.md §3.3",
    "manage-without-knowledge": "procedures/qualification-pass.md §3.3",
    "leads-outside-organisation": "procedures/qualification-pass.md §3.3",
    "representation-fit": "procedures/positional-construction.md §4",
    "development-step": "procedures/qualification-pass.md §3.3",
    "polysystem": "procedures/qualification-pass.md §3.3",
    "single-node-metasystem": "procedures/positional-construction.md §2",
    "line-without-recovery": "procedures/functional-plan.md §4",
    "absorbed-into-system-1": "procedures/positional-construction.md §5",
    "no-model-of-whole": "procedures/functional-plan.md §4",
    "model-of-whole-one-filler": "procedures/functional-plan.md §4",
}


def build_ctx(
    data: dict[str, Any],
    source_ids: set[str] | None = None,
    previous: dict[str, Any] | None = None,
    taxonomies: dict[str, set[str]] | None = None,
    source_kinds: dict[str, str] | None = None,
) -> Ctx:
    """Index a schema-valid record; only a board set has elements to index.
    A board set's profile must be known (profile_of raises otherwise)."""
    ctx = Ctx(
        data,
        source_ids=source_ids,
        source_kinds=source_kinds,
        previous=previous,
        taxonomies=taxonomies,
    )
    if data["record"] == "board_set":
        ctx.profile = profile_of(data)
        ctx.by_id = {el["id"]: el for el in data["elements"]}
        ctx.theses = {t["id"]: t for t in data.get("theses", [])}
        ctx.ks = {q["id"]: q for q in data.get("qualifications", [])}
        ctx.hyps = {h["id"]: h for h in data.get("hypotheses", [])}
    return ctx


def board_set(check: Check) -> Check:
    """Run a check on board sets only; any other record gets no findings."""

    @wraps(check)
    def guarded(ctx: Ctx) -> list[Finding]:
        return check(ctx) if ctx.record["record"] == "board_set" else []

    return guarded


def hint(
    hint_id: str, kinds: tuple[str, ...] = (), relations: tuple[str, ...] = ()
) -> Callable[[Check], Check]:
    """Mark a board-set check as a method hint with a string id. A hint of one
    profile's scheme names that profile's kinds and relation kinds here, so a
    profile that enables it must define them (profile.py). Its findings name
    the procedure of HINT_PROCEDURES, unless they name their own."""
    procedure = HINT_PROCEDURES[hint_id]

    def register(check: Check) -> Check:
        guarded = board_set(check)

        @wraps(check)
        def pointed(ctx: Ctx) -> list[Finding]:
            return [
                f if f.procedure else replace(f, procedure=procedure)
                for f in guarded(ctx)
            ]

        setattr(pointed, "hint_id", hint_id)
        setattr(pointed, "needs", (kinds, relations))
        HINTS[hint_id] = pointed
        return pointed

    return register


def hint_needs(hint_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The kinds and relation kinds a hint names: (kinds, relations)."""
    needs: tuple[tuple[str, ...], tuple[str, ...]] = getattr(
        HINTS[hint_id], "needs", ((), ())
    )
    return needs


def cite_findings(
    cites: list[str], where: str, source_ids: set[str] | None
) -> list[Finding]:
    if source_ids is None:
        return []
    return [
        Finding("error", where, f"cites unknown source '{c.split('#')[0]}'")
        for c in cites
        if c.split("#")[0] not in source_ids
    ]
