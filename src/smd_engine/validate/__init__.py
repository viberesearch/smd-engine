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

from smd_engine.profile import (
    RESERVED_BOARD_IDS,
    Profile,
    ProfileError,
    profile_of,
)
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
    hint_cells_from_information,
    hint_design_the_natural,
    hint_external_without_reflection,
    hint_goal_without_breakdown,
    hint_information_without_cell,
    hint_new_frames,
    hint_no_new_scheme,
    hint_object_from_inside,
    hint_ontology,
    hint_ontology_outlives_pace,
    hint_open_qualifications,
    hint_ought_without_fact,
    hint_position_without_object,
    hint_positions,
    hint_problems,
    hint_revise_if,
    hint_situation_halves,
)
from smd_engine.validate.hypotheses import check_hypotheses
from smd_engine.validate.management import (
    hint_absorbed_into_system_1,
    hint_development_step,
    hint_lead_vs_manage,
    hint_leads_outside_organisation,
    hint_line_without_recovery,
    hint_manage_via_organizedness,
    hint_manage_without_knowledge,
    hint_model_of_whole_one_filler,
    hint_no_model_of_whole,
    hint_polysystem,
    hint_representation_fit,
    hint_single_node_metasystem,
)
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
    check_record_boards,
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
    check_record_boards,
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
    hint_ontology_outlives_pace,
    hint_difficulty,
    hint_revise_if,
    hint_ai_drafts,
    hint_ai_variants,
    hint_no_new_scheme,
    hint_object_from_inside,
    hint_external_without_reflection,
    hint_goal_without_breakdown,
    hint_position_without_object,
    hint_ought_without_fact,
    hint_design_the_natural,
    hint_information_without_cell,
    hint_cells_from_information,
    hint_lead_vs_manage,
    hint_manage_via_organizedness,
    hint_manage_without_knowledge,
    hint_leads_outside_organisation,
    hint_representation_fit,
    hint_development_step,
    hint_polysystem,
    hint_single_node_metasystem,
    hint_line_without_recovery,
    hint_absorbed_into_system_1,
    hint_no_model_of_whole,
    hint_model_of_whole_one_filler,
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
    out = _record_board_findings(data, profile)
    for el in _items(data, "elements"):
        board, kind = el.get("board"), el.get("kind")
        # an unknown kind is reported below, once
        if (
            isinstance(board, str)
            and isinstance(kind, str)
            and profile.has_board(board)
            and profile.has_kind(kind)
        ):
            template = profile.template(profile.board(board).template)
            if template and kind not in template.kinds:
                out.append(
                    Finding(
                        "error",
                        str(el.get("id")),
                        f"kind '{kind}' is not taken by board '{board}' "
                        f"(template '{template.id}': {', '.join(template.kinds)})",
                    )
                )
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


def _record_board_findings(data: dict[str, Any], profile: Profile) -> list[Finding]:
    """The boards a record makes of its profile's templates (`boards`): each
    of a known template, with an id that no profile board or template and no
    other record board has, and that is not a layer of `smd graph`.
    profile_of leaves such a board out, so an element on it is also reported
    as on an unknown board."""
    taken = {b.id for b in profile.boards if not b.template}
    taken |= {t.id for t in profile.templates}
    known = ", ".join(t.id for t in profile.templates) or "none"
    out: list[Finding] = []
    seen: set[str] = set()
    for raw in _items(data, "boards"):
        bid, tid = raw.get("id"), raw.get("template")
        if not isinstance(bid, str) or not isinstance(tid, str):
            continue
        where = f"board {bid}"
        if profile.template(tid) is None:
            message = (
                f"unknown board template '{tid}' in profile '{profile.id}'; "
                f"known: {known}"
            )
        elif bid in RESERVED_BOARD_IDS:
            message = f"board id '{bid}' is a layer of smd graph"
        elif bid in taken:
            message = f"board id '{bid}' is a board or template of the profile"
        elif bid in seen:
            message = "duplicate board id"
        else:
            seen.add(bid)
            continue
        out.append(Finding("error", where, message))
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
