"""Sealed numbers: the commitment of a bound item and the sealed file that holds
the number. Only the standard library is used.

A party seals a number on its own machine (`smd deal seal`). The sealed file
(`task_sealed`) holds the number and a random salt and stays with the party; its
commitment, a sha256, goes into the party's answers file and is all the other
members and the diff ever see. The salt keeps a round number from being found by
trying them all. The commitment names the deal, the pack, the item, the member,
the side and the unit, so it cannot be moved to another item or another person.
The holder opens a sealed file only inside a verdict run. No message of this
module repeats the number or the salt."""

from __future__ import annotations

import hashlib
import json
import math
import secrets
import subprocess
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from smd_engine.records import RecordError, parse_text
from smd_engine.task.model import Issue, load_task_schema, read_bytes

SEAL_TAG = "smd-seal-v1\n"


def canon_number(value: float) -> int | float:
    """3 and 3.0 are one number, so they commit alike."""
    return int(value) if float(value) == int(value) else float(value)


def commitment_of(sealed: dict[str, Any]) -> str:
    """The sha256 commitment of a sealed record."""
    body = {
        "deal": sealed["deal"],
        "pack_id": sealed["pack"]["id"],
        "core_sha": sealed["pack"]["sha256"],
        "item": sealed["item"],
        "member": sealed["member"],
        "side": sealed["side"],
        "unit": sealed["unit"],
        "value": canon_number(sealed["value"]),
        "salt": sealed["salt"],
    }
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((SEAL_TAG + text).encode("utf-8")).hexdigest()


def usable_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def make_sealed(
    pack: dict[str, Any],
    pack_sha: str,
    item: dict[str, Any],
    member: str,
    value: float,
    date: str,
) -> dict[str, Any]:
    """A sealed record for a bound item, with a fresh random salt."""
    b = item["bound"]
    return {
        "record": "task_sealed",
        "schema_version": "0.1",
        "pack": {"id": pack["id"], "version": pack["version"], "sha256": pack_sha},
        "deal": pack["deal"]["id"],
        "member": member,
        "item": item["id"],
        "side": b["side"],
        "unit": b["unit"],
        "value": canon_number(value),
        "salt": secrets.token_hex(32),
        "date": date,
    }


def read_sealed(path: Path) -> dict[str, Any] | None:
    """The sealed record in a file, or None when it is not a valid one. Neither
    the parse error nor the schema error is kept: either could quote the number."""
    try:
        data = parse_text(read_bytes(path).decode("utf-8", errors="replace"))
    except yaml.YAMLError, RecordError:
        return None
    validator = Draft202012Validator(
        load_task_schema("task_sealed"),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )
    if not isinstance(data, dict) or not validator.is_valid(data):
        return None
    return data if usable_number(data["value"]) else None


def unignored_in_worktree(path: Path) -> bool:
    """Whether the file sits in a git work tree and is not ignored there."""
    folder = str(path.parent)
    try:
        inside = subprocess.run(
            ["git", "-C", folder, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        )
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return False
        ignored = subprocess.run(
            ["git", "-C", folder, "check-ignore", "-q", str(path)],
            capture_output=True,
        )
    except OSError:
        return False
    return ignored.returncode != 0


def stray_sealed_issues(folders: list[Path]) -> list[Issue]:
    """Warnings for `sealed_*.yaml` files beside answers files in a git work tree
    where they are not ignored: they would be committed with the rest."""
    out: list[Issue] = []
    for path in sorted({p for f in folders for p in f.glob("sealed_*.yaml")}):
        if unignored_in_worktree(path):
            out.append(
                Issue(
                    "warning",
                    str(path),
                    "a sealed file sits in a git work tree and is not ignored; "
                    "keep it outside every repository",
                )
            )
    return out


def seal_file_name(member: str, item: str) -> str:
    return f"sealed_{member}_{item}.yaml"


def write_private(path: Path, text: str) -> None:
    """Write a file only its owner can read; refuse to overwrite one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x", encoding="utf-8") as fh:
            path.chmod(0o600)
            fh.write(text)
    except FileExistsError as exc:
        raise RecordError(
            f"{path} exists: one commitment stands per item and member; a new one "
            "is a new run, which both parties have to consent to"
        ) from exc
