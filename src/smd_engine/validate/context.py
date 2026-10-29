"""What every check receives: the record and the lookups built once from it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
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
    previous: dict[str, Any] | None = None
    # Taxonomy id to its value ids, when a taxonomy file is given.
    taxonomies: dict[str, set[str]] | None = None


Check = Callable[[Ctx], list[Finding]]

# Method hints by string id, so a profile can name the ones it enables.
HINTS: dict[str, Check] = {}


def build_ctx(
    data: dict[str, Any],
    source_ids: set[str] | None = None,
    previous: dict[str, Any] | None = None,
    taxonomies: dict[str, set[str]] | None = None,
) -> Ctx:
    """Index a schema-valid record; only a board set has elements to index.
    A board set's profile must be known (profile_of raises otherwise)."""
    ctx = Ctx(data, source_ids=source_ids, previous=previous, taxonomies=taxonomies)
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


def hint(hint_id: str) -> Callable[[Check], Check]:
    """Mark a board-set check as a method hint with a string id."""

    def register(check: Check) -> Check:
        guarded = board_set(check)
        setattr(guarded, "hint_id", hint_id)
        HINTS[hint_id] = guarded
        return guarded

    return register


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
