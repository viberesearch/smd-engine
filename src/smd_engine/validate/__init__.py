"""Schema and semantic checks for records.

Three levels:
- error: the record is inconsistent (dangling reference, broken numbering);
- warning: the record is consistent but breaks a convention of the method;
- hint: a methodological observation a qualification pass should look at
  (empty small situation, new frame without a functional plan, open gaps).

Checks live in the modules of this package, split by subject, and run in the
order of REGISTRY; findings come out in that order.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from jsonschema import Draft202012Validator

from smd_engine.profile import ProfileError, profile_of
from smd_engine.records import load_schema, schema_version
from smd_engine.validate.context import (
    AI_VOICES,
    HINTS,
    Check,
    Ctx,
    Finding,
    build_ctx,
)
from smd_engine.validate.hints import (
    hint_ai_drafts,
    hint_ai_variants,
    hint_candidate_moves,
    hint_difficulty,
    hint_entry,
    hint_empty_boards,
    hint_gaps,
    hint_belts,
    hint_new_frames,
    hint_no_new_scheme,
    hint_ontology,
    hint_open_qualifications,
    hint_positions,
    hint_problems,
    hint_revise_if,
    hint_situation_halves,
)
from smd_engine.validate.hypotheses import check_hypotheses
from smd_engine.validate.manifest import check_manifest
from smd_engine.validate.ontology import check_ontology
from smd_engine.validate.signoffs import (
    SIGNOFF_EFFECT,
    SIGNOFF_FAMILY,
    check_signoffs,
)
from smd_engine.validate.structure import (
    SUBJECT_OBJECT,
    check_elements,
    check_qualifications,
    check_record_level,
    check_relations,
    check_transitions,
)
from smd_engine.validate.taxonomies import check_tags, taxonomy_values
from smd_engine.validate.theses import STATUS_VOICES, check_theses, check_thesis_raises

__all__ = [
    "AI_VOICES",
    "HINTS",
    "REGISTRY",
    "SIGNOFF_EFFECT",
    "SIGNOFF_FAMILY",
    "STATUS_VOICES",
    "SUBJECT_OBJECT",
    "Check",
    "Ctx",
    "Finding",
    "taxonomy_values",
    "validate_record",
]

# Run in this order; each check returns nothing for a record kind it does not cover.
REGISTRY: list[Check] = [
    check_elements,
    check_relations,
    check_transitions,
    check_qualifications,
    check_record_level,
    check_thesis_raises,
    check_theses,
    check_hypotheses,
    check_ontology,
    check_signoffs,
    check_tags,
    hint_entry,
    hint_empty_boards,
    hint_situation_halves,
    hint_positions,
    hint_new_frames,
    hint_gaps,
    hint_open_qualifications,
    hint_candidate_moves,
    hint_problems,
    hint_belts,
    hint_ontology,
    hint_difficulty,
    hint_revise_if,
    hint_ai_drafts,
    hint_ai_variants,
    hint_no_new_scheme,
    check_manifest,
]


def _version_findings(data: dict[str, Any]) -> list[Finding]:
    """An older (or newer) record is one error; its fields are not checked."""
    found = data.get("schema_version")
    # An unquoted 0.3 is the right version; the schema asks for it as text.
    if found is None or str(found) == schema_version(data["record"]):
        return []
    return [Finding("error", "schema_version", f"schema {found}: run smd migrate")]


def _schema_findings(data: dict[str, Any]) -> Iterable[Finding]:
    validator = Draft202012Validator(
        load_schema(data["record"]), format_checker=Draft202012Validator.FORMAT_CHECKER
    )
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        yield Finding("error", where, err.message)


def _items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """The mappings of a list; the schema reports anything else."""
    value = data.get(key)
    return [i for i in value if isinstance(i, dict)] if isinstance(value, list) else []


def _profile_findings(data: dict[str, Any]) -> list[Finding]:
    """An unknown or malformed profile (the parser also refuses hint ids the
    engine does not have); boards, kinds and relation kinds outside the record's
    profile. Run next to the schema check, so a field it reports missing is
    skipped here."""
    try:
        profile = profile_of(data)
    except ProfileError as exc:
        return [Finding("error", "profile", str(exc))]
    out: list[Finding] = []
    for el in _items(data, "elements"):
        for what, known in (
            ("board", profile.has_board),
            ("kind", profile.has_kind),
        ):
            value = el.get(what)
            if isinstance(value, str) and not known(value):
                out.append(
                    Finding(
                        "error",
                        str(el.get("id")),
                        f"unknown {what} '{value}' in profile '{profile.id}'",
                    )
                )
    for rel in _items(data, "relations"):
        kind = rel.get("kind")
        if isinstance(kind, str) and kind not in profile.relations:
            out.append(
                Finding(
                    "error",
                    f"relation {rel.get('from')}->{rel.get('to')}",
                    f"unknown relation kind '{kind}' in profile '{profile.id}'",
                )
            )
    return out


def validate_record(
    data: dict[str, Any],
    source_ids: set[str] | None = None,
    previous: dict[str, Any] | None = None,
    taxonomies: dict[str, set[str]] | None = None,
) -> list[Finding]:
    """Validate one record.

    A board set is checked against its profile (`profile`, profiles/): its
    boards, kinds and relation kinds, and only the hints the profile enables.
    source_ids enables citation checks; previous is the board set this one
    revises, when it is at hand, for the checks across cycles; taxonomies
    (see taxonomy_values) enables the checks of tags and bound detail columns.
    """
    findings = _version_findings(data)
    if findings:
        return findings
    findings = list(_schema_findings(data))
    if data["record"] == "board_set":
        # Boards and kinds outside the profile are reported with the schema's
        # errors and, like them, stop the checks.
        findings += _profile_findings(data)
    if any(f.level == "error" for f in findings):
        return findings
    ctx = build_ctx(data, source_ids, previous, taxonomies)
    for check in REGISTRY:
        hint_id = getattr(check, "hint_id", None)
        if hint_id is None or hint_id in ctx.profile.hints:
            findings += check(ctx)
    return findings
