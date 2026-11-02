"""Loading and schema checks of the task records: pack, answers, replies and the
diff. They are plain YAML files named by the cycle (`pack.yaml`,
`answers_<member>.yaml`, `diff.yaml`, `replies_<member>.yaml`), not record files
that `smd validate` discovers, so they are read here and not by `load_record`."""

from __future__ import annotations

import hashlib
import json
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any, NamedTuple

import yaml
from jsonschema import Draft202012Validator

from smd_engine.records import RecordError, parse_text

SCHEMAS = {
    "task_pack": "task_pack.schema.json",
    "task_answers": "task_answers.schema.json",
    "task_replies": "task_replies.schema.json",
    "task_acceptance": "task_acceptance.schema.json",
    "task_sealed": "task_sealed.schema.json",
    "task_verdicts": "task_verdicts.schema.json",
}
ITEM_KINDS = ("choice", "multi", "text", "number", "ids", "steps")
TERM_CHECK_RANGE = (3, 7)  # items a term check should have (procedures/task-pack.md)


class Issue(NamedTuple):
    level: str  # error | warning
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level}: {self.where}: {self.message}"


@cache
def load_task_schema(record: str) -> dict[str, Any]:
    text = resources.files("smd_engine.schemas").joinpath(SCHEMAS[record])
    schema: dict[str, Any] = json.loads(text.read_text("utf-8"))
    return schema


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise RecordError(f"{path}: cannot read ({exc})") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(read_bytes(path))


def load_task(path: Path, record: str | None = None) -> dict[str, Any]:
    """A task file as a mapping. With `record` the file must be of that type."""
    text = read_bytes(path).decode("utf-8", errors="replace")
    try:
        data = parse_text(text)
    except yaml.YAMLError as exc:
        raise RecordError(f"{path}: not valid YAML ({exc})") from exc
    if not isinstance(data, dict):
        raise RecordError(f"{path}: top level must be a mapping")
    if data.get("record") == "task_sealed" and record != "task_sealed":
        # a sealed number goes to the holder's verdict and nowhere else
        raise RecordError(f"{path}: a sealed file is not an input here")
    if record is not None and data.get("record") != record:
        raise RecordError(
            f"{path}: expected record {record}, found {data.get('record')!r}"
        )
    return data


def schema_issues(data: dict[str, Any], record: str, where: str) -> list[Issue]:
    validator = Draft202012Validator(
        load_task_schema(record), format_checker=Draft202012Validator.FORMAT_CHECKER
    )
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(top)"
        out.append(Issue("error", where, f"{path}: {err.message}"))
    return out


def member_ids(pack: dict[str, Any]) -> list[str]:
    return [m["id"] for m in pack["members"]]
