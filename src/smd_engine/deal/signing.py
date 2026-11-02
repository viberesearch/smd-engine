"""OpenSSH signatures for the sealed floor of a deal pack. A party signs his consent
files, his sealed file and his answers file with his own SSH key; the pack lists
the public key of each party (`members[].ssh_key`). The engine calls
`ssh-keygen -Y` and adds no Python dependency; the private key is never read here.

Namespace `smd-deal`; the signer principal is the member id. A signature proves
that the holder of the key wrote the file, so the holder's operator cannot forge a
party's consent, sealed file or answers file. Everything below applies only when
the pack has `deal.sealed_floor: true`; without it nothing changes."""

from __future__ import annotations

import base64
import binascii
import hashlib
import shlex
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from smd_engine.records import RecordError

NAMESPACE = "smd-deal"
# the suffix of the security-key types, kept apart so the public export scan does
# not read "<type>@openssh.com" as an email address
OPENSSH = "@openssh.com"
KEY_TYPES = (
    "ssh-ed25519",
    "ssh-rsa",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    f"sk-ssh-ed25519{OPENSSH}",
    f"sk-ecdsa-sha2-nistp256{OPENSSH}",
)
SIGNING_KINDS = ("seller", "buyer")  # the positions that commit or consent
TIMEOUT = 60  # seconds for one ssh-keygen call

Found = list[tuple[str, str]]


def signatures_on(pack: dict[str, Any]) -> bool:
    return bool((pack.get("deal") or {}).get("sealed_floor"))


def key_problem(line: Any) -> str:
    """Why `line` is not one OpenSSH public key line, or an empty string."""
    if not isinstance(line, str) or len(line.splitlines()) != 1:
        return "must be one line of text"
    parts = line.split()
    if len(parts) < 2 or parts[0] not in KEY_TYPES:
        return "must be an OpenSSH public key line, e.g. 'ssh-ed25519 AAAA... name'"
    try:
        blob = base64.b64decode(parts[1], validate=True)
        (size,) = struct.unpack(">I", blob[:4])
    except binascii.Error, struct.error:
        return "is not a valid OpenSSH public key (the key part is not base64)"
    if blob[4 : 4 + size] != parts[0].encode("ascii"):
        return (
            "is not a valid OpenSSH public key (the key part does not match its type)"
        )
    return ""


def public_key(line: str) -> str:
    """The key line without its comment: `type base64`."""
    return " ".join(line.split()[:2])


def key_list_sha(pack: dict[str, Any]) -> str:
    """The sha256 of the pack's list of signing keys: the lines `<member> <type>
    <base64>` of every member with a usable `ssh_key` (comment dropped), sorted and
    joined by newlines. A consent names it, so it is tied to the keys of the pack
    it was written for."""
    lines = sorted(
        f"{m['id']} {public_key(m['ssh_key'])}"
        for m in pack["members"]
        if m.get("ssh_key") is not None and not key_problem(m["ssh_key"])
    )
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def key_findings(pack: dict[str, Any]) -> Found:
    """Errors of the keys of a pack with a sealed floor: every seller and buyer
    needs one, each must be well formed, and no two members share one."""
    if not signatures_on(pack):
        return []
    kinds = {p["id"]: p["kind"] for p in pack.get("positions", [])}
    out: Found = []
    seen: dict[str, str] = {}
    for m in pack["members"]:
        key = m.get("ssh_key")
        if key is None:
            if kinds.get(m.get("position", "")) in SIGNING_KINDS:
                out.append(
                    (
                        "error",
                        f"member {m['id']}: ssh_key is required with "
                        "deal.sealed_floor (consents and sealed files are signed)",
                    )
                )
            continue
        problem = key_problem(key)
        if problem:
            out.append(("error", f"member {m['id']}: ssh_key {problem}"))
        elif public_key(key) in seen:
            out.append(
                (
                    "error",
                    f"member {m['id']}: ssh_key is the key of {seen[public_key(key)]} "
                    "too; each member signs with his own",
                )
            )
        else:
            seen[public_key(key)] = m["id"]
    return out


def ssh_keygen() -> str:
    found = shutil.which("ssh-keygen")
    if found is None:
        raise RecordError(
            "ssh-keygen was not found; a pack with deal.sealed_floor needs it "
            "(OpenSSH 8.0 or later) to sign and verify"
        )
    return found


def _run(
    args: list[str], data: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            args, input=data, capture_output=True, timeout=TIMEOUT, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecordError(f"ssh-keygen failed ({exc})") from exc


def sign_command(key: str, path: Path) -> str:
    return f"ssh-keygen -Y sign -f {key} -n {NAMESPACE} {shlex.quote(str(path))}"


def sign_file(key: Path, path: Path) -> Path:
    """Sign `path` with the private key at `key` (ssh-keygen reads it, not this
    program); the signature is written to `<path>.sig`."""
    done = _run(
        [ssh_keygen(), "-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(path)]
    )
    sig = path.with_name(path.name + ".sig")
    if done.returncode != 0 or not sig.is_file():
        reason = done.stderr.decode("utf-8", errors="replace").strip()
        raise RecordError(f"{path}: not signed ({reason or 'ssh-keygen failed'})")
    return sig


def verify_signature(
    pack: dict[str, Any], member: str, data: bytes, signature: str, what: str
) -> None:
    """Refuse (RecordError) unless `signature` is the signature of `member` over
    `data`, made with the key the pack lists for him."""
    exe = ssh_keygen()
    members = {m["id"]: m.get("ssh_key") for m in pack["members"]}
    if key_problem(members.get(member)):
        raise RecordError(f"{what}: the pack lists no usable ssh_key for {member}")
    lines = [
        f'{who} namespaces="{NAMESPACE}" {public_key(key)}\n'
        for who, key in members.items()
        if key is not None and not key_problem(key)
    ]
    with tempfile.TemporaryDirectory() as tmp:
        allowed, sig = Path(tmp) / "allowed_signers", Path(tmp) / "signature"
        allowed.write_text("".join(lines), encoding="utf-8")
        sig.write_text(signature, encoding="utf-8")
        args = [exe, "-Y", "verify", "-f", str(allowed), "-I", member]
        done = _run([*args, "-n", NAMESPACE, "-s", str(sig)], data)
    if done.returncode != 0:
        raise RecordError(
            f"{what}: the signature is not {member}'s (the key in the pack, "
            f"namespace {NAMESPACE}) over this text"
        )


def verify_file(
    pack: dict[str, Any], member: str, path: Path, signature: Path | None
) -> str:
    """Refuse a file that has no valid signature of `member` at `signature`
    (`<path>.sig` by default). Returns the sha256 of the bytes verified."""
    sig = signature or path.with_name(path.name + ".sig")
    try:
        data, text = path.read_bytes(), sig.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RecordError(
            f"{path}: not signed by {member}: cannot read the file or {sig} ({exc}); "
            f"the party signs it with: {sign_command('<private key>', path)}"
        ) from exc
    verify_signature(pack, member, data, text, str(path))
    return hashlib.sha256(data).hexdigest()


def key_holders(pack: dict[str, Any]) -> set[str]:
    """The members whose answers files are signed: those with a usable ssh_key."""
    return {
        m["id"]
        for m in pack["members"]
        if m.get("ssh_key") is not None and not key_problem(m["ssh_key"])
    }


def verify_answers(
    pack: dict[str, Any], loaded: list[tuple[Path, str, dict[str, Any]]]
) -> None:
    """Refuse (RecordError) unless the answers file of every member with a key is
    signed by him (`<file>.sig`) and is the file `loaded` read (its sha256)."""
    holders = key_holders(pack)
    for path, sha, ans in loaded:
        member = str(ans["member"])
        if member in holders and verify_file(pack, member, path, None) != sha:
            raise RecordError(f"{path}: the file changed while it was read")


def unsigned_answers(
    pack: dict[str, Any], loaded: list[tuple[Path, str, dict[str, Any]]]
) -> list[str]:
    """One message per answers file of a member with a key that has no valid
    signature of his; for the warnings of `smd task diff`, which does not refuse."""
    holders = key_holders(pack)
    out: list[str] = []
    for path, _, ans in loaded:
        if ans["member"] in holders:
            try:
                verify_file(pack, str(ans["member"]), path, None)
            except RecordError as exc:
                out.append(str(exc))
    return out
