"""Loading of record files and discovery of records in a tree."""

from __future__ import annotations

import datetime as dt
import json
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

SCHEMA_FILES = {
    "board_set": "board_set.schema.json",
    "source_manifest": "source_manifest.schema.json",
    "taxonomies": "taxonomies.schema.json",
    "board_patch": "board_patch.schema.json",
    "story": "story.schema.json",
}


class RecordError(Exception):
    """A file cannot be read as a record."""


def load_record(path: Path) -> dict[str, Any]:
    """Read a YAML or JSON record and check it names a known record type."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RecordError(f"{path}: cannot read ({exc})") from exc
    try:
        data = parse_text(text, path.suffix == ".json")
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise RecordError(f"{path}: not valid YAML/JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise RecordError(f"{path}: top level must be a mapping")
    if data.get("record") not in SCHEMA_FILES:
        raise RecordError(f"{path}: unknown record type {data.get('record')!r}")
    return data


def parse_text(text: str, json_text: bool = False) -> Any:
    """The data of a record's text, with dates kept as ISO text."""
    return _dates_to_text(json.loads(text) if json_text else yaml.safe_load(text))


def _dates_to_text(value: Any) -> Any:
    """YAML reads unquoted dates as date objects; records keep them as ISO text."""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _dates_to_text(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_dates_to_text(v) for v in value]
    return value


def is_record_file(path: Path) -> bool:
    return path.name == "sources.yaml" or path.name.endswith(
        (".board.yaml", ".patch.yaml", ".story.yaml")
    )


@cache
def load_schema(record_type: str) -> dict[str, Any]:
    """Return the packaged JSON Schema for a record type."""
    name = SCHEMA_FILES[record_type]
    text = resources.files("smd_engine.schemas").joinpath(name).read_text("utf-8")
    schema: dict[str, Any] = json.loads(text)
    return schema


def schema_version(record_type: str) -> str:
    """The schema version the engine accepts for a record type."""
    version: str = load_schema(record_type)["properties"]["schema_version"]["const"]
    return version


def discover(paths: list[Path]) -> list[Path]:
    """Expand directories into record files, keeping explicit files as given."""
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(
                p
                for p in sorted(path.rglob("*.yaml"))
                if is_record_file(p) and ".venv" not in p.parts
            )
        else:
            found.append(path)
    return found


FLOW_WIDTH = (
    160  # a mapping or list of scalars shorter than this is written on one line
)


class _RecordDumper(yaml.SafeDumper):
    """Writes small leaf mappings and lists in flow style, as records are hand-written."""


def _leaf(value: Any) -> bool:
    return not isinstance(value, (dict, list))


def _short(value: Any) -> bool:
    text = yaml.safe_dump(
        value, default_flow_style=True, allow_unicode=True, width=10**6
    )
    return len(text.strip()) <= FLOW_WIDTH


def _represent_dict(dumper: yaml.SafeDumper, data: dict[str, Any]) -> yaml.Node:
    flow = all(
        _leaf(v) or (isinstance(v, list) and all(_leaf(x) for x in v))
        for v in data.values()
    ) and _short(data)
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=flow)


def _represent_list(dumper: yaml.SafeDumper, data: list[Any]) -> yaml.Node:
    flow = all(_leaf(x) for x in data) and _short(data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


_RecordDumper.add_representer(dict, _represent_dict)
_RecordDumper.add_representer(list, _represent_list)


def dump_record(data: dict[str, Any]) -> str:
    """YAML text of a record, compact where the hand-written records are compact."""
    text: str = yaml.dump(
        data, Dumper=_RecordDumper, allow_unicode=True, sort_keys=False, width=4096
    )
    return text
