"""One-shot migration of records to the current schema version.

Each step rewrites a record from one schema version to the next; `migrate`
applies them in sequence until the record is current. A current record comes
back unchanged. The validator accepts only the current version, so there is no
reading of old records anywhere else in the engine.

`migrate_text` makes the same changes in a record's text, line by line, so that
comments and layout stay; it is checked against `migrate` before it is used.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from collections.abc import Callable
from typing import Any

import yaml

from smd_engine.records import SCHEMA_FILES, parse_text, schema_version
from smd_engine.validate.context import AI_VOICES

# The element voice enum of v0.3, the same as the thesis voice enum.
VOICES = ("group", "participant", "moderator", "expert", "organisers", "ai")
MIGRATED = ("board_set", "source_manifest")

Step = Callable[[dict[str, Any], list[str]], dict[str, Any]]
TextStep = Callable[[str, bool], str]


def _version(data: dict[str, Any]) -> str | None:
    """The record's schema version as text; YAML reads an unquoted 0.2 as a number."""
    found = data.get("schema_version")
    return None if found is None else str(found)


def _element_voice(el: dict[str, Any]) -> tuple[str, str] | None:
    """The (old, new) voice of an element whose voice is not in the enum."""
    if el.get("voice") is None:
        return None
    old = str(el["voice"])
    if old in VOICES:
        return None
    low = old.strip().lower()
    if low in VOICES:
        return old, low
    if low in AI_VOICES:
        return old, "ai"
    return old, "participant"


def _with_voice(el: dict[str, Any], new: str, note: str | None) -> dict[str, Any]:
    """The element with a new voice, the old text placed right after it."""
    out: dict[str, Any] = {}
    for key, value in el.items():
        out[key] = new if key == "voice" else value
        if key == "voice" and note is not None:
            out["voice_note"] = note
    return out


def _0_2_to_0_3(data: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    """Schema 0.3: element voices from the thesis enum; nothing else tightens."""
    data["schema_version"] = "0.3"
    notes.append("schema_version: 0.2 -> 0.3")
    if data["record"] != "board_set":
        return data
    changed: Counter[tuple[str, str]] = Counter()
    elements = []
    for el in data.get("elements", []):
        change = _element_voice(el)
        if change:
            old, new = change
            changed[change] += 1
            keep = old if new == "participant" else None
            el = _with_voice(el, new, keep)
        elements.append(el)
    if "elements" in data:
        data["elements"] = elements
    for (old, new), n in changed.items():
        kept = ", old text in voice_note" if new == "participant" else ""
        notes.append(f"voice: {old!r} -> {new}{kept} ({n} element(s))")
    return data


# Version a step starts from -> the step, which sets the next version.
STEPS: dict[str, Step] = {"0.2": _0_2_to_0_3}


def migrate(data: dict[str, Any], notes: list[str] | None = None) -> dict[str, Any]:
    """The record rewritten to the current schema version; data is not changed.

    notes, when given, receives one line per change made. Raises ValueError for
    a record type or version there is no migration for.
    """
    record = data.get("record")
    if record not in SCHEMA_FILES:
        raise ValueError(f"unknown record type {record!r}")
    notes = notes if notes is not None else []
    out = copy.deepcopy(data)
    while (version := _version(out)) != schema_version(record):
        if record not in MIGRATED:
            raise ValueError(f"no migration for record type {record!r}")
        if version not in STEPS:
            raise ValueError(f"no migration from schema {version}")
        out = STEPS[version](out, notes)
    return out


# Text edits: (start, end, replacement) as character offsets into the text.
Edit = tuple[int, int, str]


def _scalar(node: yaml.ScalarNode, value: str) -> Edit:
    """Replace a scalar's value, keeping its quotes; a new plain value is quoted
    when YAML would read it as something other than text (0.3 as a number)."""
    quote = node.style if node.style in ('"', "'") else ""
    if not quote and not isinstance(yaml.safe_load(value), str):
        quote = '"'
    return node.start_mark.index, node.end_mark.index, f"{quote}{value}{quote}"


def _note_value(src: str, old: Any) -> str:
    """The old voice as it is written, or quoted as text when it loads as
    something else (voice: yes, voice: 12)."""
    return src if isinstance(old, str) else json.dumps(str(old), ensure_ascii=False)


def _0_2_to_0_3_text(text: str, json_text: bool) -> str:
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    assert isinstance(root, yaml.MappingNode)
    pairs = {k.value: v for k, v in root.value}
    edits: list[Edit] = [_scalar(pairs["schema_version"], "0.3")]
    if pairs["record"].value == "board_set" and "elements" in pairs:
        for item in pairs["elements"].value:
            for key, value in item.value:
                if key.value != "voice":
                    continue
                src = text[value.start_mark.index : value.end_mark.index]
                old = parse_text(src, json_text)
                change = _element_voice({"voice": old})
                if not change:
                    continue
                edits.append(_scalar(value, change[1]))
                if change[1] != "participant":
                    continue
                src = _note_value(src, old)
                if item.flow_style:
                    end = value.end_mark.index
                    note = '"voice_note"' if json_text else "voice_note"
                    edits.append((end, end, f", {note}: {src}"))
                else:
                    eol = text.find("\n", value.end_mark.index)
                    at = len(text) if eol < 0 else eol + 1
                    line = " " * key.start_mark.column + f"voice_note: {src}\n"
                    edits.append((at, at, line if eol >= 0 else "\n" + line))
    for start, end, new in sorted(edits, reverse=True):
        text = text[:start] + new + text[end:]
    return text


TEXT_STEPS: dict[str, TextStep] = {"0.2": _0_2_to_0_3_text}


def migrate_text(text: str, json_text: bool = False) -> str | None:
    """The record's text with migrate's changes made in place, comments and
    layout kept; None when the edited text does not load as migrate's result,
    and the caller writes the migrated data instead."""
    try:
        original = parse_text(text, json_text)
        expected = migrate(original)
        edited = text
        while (version := _version(parse_text(edited, json_text))) in TEXT_STEPS:
            edited = TEXT_STEPS[version](edited, json_text)
        return edited if parse_text(edited, json_text) == expected else None
    except ValueError, KeyError, AssertionError, AttributeError, yaml.YAMLError:
        return None
