"""`smd deal verify --diff`: a diff (or a position's view of it) against the
ledger, so that the holder cannot hide a logged verdict from the parties.

- The diff is for this text of the pack, and every bound item the diff (or the
  view's position) should show is there, as a sealed point of its own topic and
  side: a point left out or stripped of its `sealed` block is a `FAIL`.
- The sealed points name one ledger head, an entry of the ledger, or none at all
  (a diff made without the ledger); a mix is a `FAIL`.
- Each sealed point's verdict is the one the ledger had at that head. A point
  shown `not_tested` over a counted run must carry `changed_since_run`, and that
  claim is checked: each member it names commits a side of the topic, the answers
  file the diff read for him is not the one the run recorded, and, when that file
  is given with `--answers`, its commitment differs from the one the run used.
  Without the file the claim is `skip`, never `ok`; with files of that member
  given and none of them the one the diff names, it is a `FAIL`.
- For a committer whose answers files are given, the file the diff names must
  be one of them.
- A counted run logged after the head (or at all, with no head) that read the
  same answers files of both committers as the diff is a `FAIL`: the diff does
  not show a verdict on its own answers. Any other later run is a `FAIL` too,
  unless a file given with `--answers` shows the diff read other answers than
  the run, so an old or missing head cannot hide a verdict.
- A view names a position of the pack, which is reported."""

from __future__ import annotations

from typing import Any

from smd_engine.deal.ledger import last_run, topic_verdict
from smd_engine.deal.verify_extra import AnswersFiles, Topic
from smd_engine.deal.verify_report import FAIL, OK, SKIP, Report
from smd_engine.task.bounds import bound_items
from smd_engine.task.positions import in_audience


def _expected(
    rep: Report, pack: dict[str, Any], diff: dict[str, Any]
) -> list[dict[str, Any]]:
    """The bound items the diff should show: all of them, or for a view those of
    its position's audience. The view's position is reported, so the party sees
    whose view he checked; one that is not a position of the pack fails, and
    then every bound item is required."""
    if "view" not in diff:
        return bound_items(pack)
    view = diff["view"]
    position = view.get("position") if isinstance(view, dict) else None
    if position not in {pos["id"] for pos in pack.get("positions") or []}:
        rep.add("diff_view_bad", FAIL, position=position)
        return bound_items(pack)
    rep.add("diff_view", OK, position=position)
    return [i for i in bound_items(pack) if in_audience(i, position)]


def _points(
    rep: Report, pack: dict[str, Any], diff: dict[str, Any]
) -> list[dict[str, Any]]:
    """The sealed points of the diff that are a bound item of the pack, with the
    item's topic and side. A bound item missing from the diff, or shown as
    another kind of point or for another topic or side, fails."""
    by_id: dict[str, list[dict[str, Any]]] = {}
    for p in diff["points"]:
        by_id.setdefault(str(p.get("id")), []).append(p)
    items = {i["id"]: i for i in bound_items(pack)}
    out: list[dict[str, Any]] = []
    for item in _expected(rep, pack, diff):
        if item["id"] not in by_id:
            rep.add("diff_missing", FAIL, point=item["id"])
    for pid, found in by_id.items():
        sealed = [p for p in found if "sealed" in p]
        if pid not in items:
            for p in sealed:
                rep.add("diff_not_bound", FAIL, point=pid)
            continue
        b = items[pid]["bound"]
        if len(found) != 1 or len(sealed) != 1:
            rep.add("diff_point_shape", FAIL, point=pid)
            continue
        p = sealed[0]
        if (p["sealed"].get("topic"), p["sealed"].get("side")) != (
            b["topic"],
            b["side"],
        ):
            rep.add("diff_point_shape", FAIL, point=pid)
            continue
        out.append(p)
    return out


def _diff_file(diff: dict[str, Any], member: str) -> str | None:
    for f in diff.get("answers_files") or []:
        if f.get("member") == member:
            return str(f.get("sha256"))
    return None


def _changed_claim(
    rep: Report,
    p: dict[str, Any],
    run: dict[str, Any],
    topic: Topic,
    diff: dict[str, Any],
    files: AnswersFiles | None,
) -> None:
    """Check a point shown `not_tested` over the counted run `run` because a
    commitment changed since it."""
    changed = p.get("changed_since_run")
    if not isinstance(changed, list) or not changed:
        rep.add(
            "diff_verdict",
            FAIL,
            point=p["id"],
            diff="not_tested",
            ledger=run["verdict"],
        )
        return
    used = run.get("commitments") or {}
    unchecked = False
    for member in changed:
        side = topic.side_of(str(member))
        sha = _diff_file(diff, str(member))
        if side is None or side not in used or sha is None:
            rep.add("diff_changed_who", FAIL, point=p["id"], member=member)
            return
        if sha == (run.get("answers") or {}).get(member):
            rep.add("diff_changed_same", FAIL, run["seq"], point=p["id"], member=member)
            return
        mine = (files or {}).get(str(member), [])
        hit = next((f for f in mine if f.sha == sha), None)
        if hit is None and mine:
            rep.add("diff_changed_file", FAIL, point=p["id"], member=member)
            return
        if hit is None:
            unchecked = True
            continue
        given = (hit.answers.get(topic.items[side]["id"]) or {}).get("value")
        if given == used[side]:
            rep.add("diff_changed_same", FAIL, run["seq"], point=p["id"], member=member)
            return
    if unchecked:
        rep.add("diff_changed_nofile", SKIP, point=p["id"])
    else:
        rep.add("diff_changed_ok", OK, point=p["id"], verdict=run["verdict"])


def _given(files: AnswersFiles | None, member: str) -> set[str]:
    return {f.sha for f in (files or {}).get(member, [])}


def _check_files(
    rep: Report,
    diff: dict[str, Any],
    files: AnswersFiles | None,
    topics: dict[str, Topic],
) -> None:
    """For each committer whose answers files were given with `--answers`, the
    file the diff names for him must be one of them: the diff's own list is the
    holder's word, the files are signed by the parties."""
    who = sorted({m for t in topics.values() for m in t.members.values() if m})
    for member in who:
        given = _given(files, member)
        if given and _diff_file(diff, member) not in given:
            rep.add("diff_answers_file", FAIL, member=member)


def _later(
    rep: Report,
    p: dict[str, Any],
    later: list[dict[str, Any]],
    topic: Topic | None,
    diff: dict[str, Any],
    files: AnswersFiles | None,
) -> bool:
    """Check the counted runs of the point's topic logged after the diff's head
    (all of them, for a diff with no head); True when one is reported `FAIL`.

    A run that read the very answers files the diff names makes the diff stale:
    it does not show a verdict on its own answers. Any other later run passes
    only when the diff is shown to be about other answers: for a committer, the
    file the diff names is among the files given with `--answers` (signed by the
    party) and is not the one the run recorded. The diff's list alone is not
    enough, since the holder writes it."""
    name = p["sealed"]["topic"]
    runs = [
        e
        for e in later
        if e["type"] == "verdict"
        and e["topic"] == name
        and e["verdict"] in ("met", "not_met")
    ]
    if not runs:
        return False
    who = [m for m in topic.members.values() if m] if topic else []
    read = {m: _diff_file(diff, m) for m in who}
    for e in reversed(runs):
        rec = e.get("answers") or {}
        if who and all(read[m] is not None and rec.get(m) == read[m] for m in who):
            rep.add("diff_stale", FAIL, e["seq"], point=p["id"], verdict=e["verdict"])
            return True
        other = any(
            read[m] in _given(files, m) and rec.get(m) not in (None, read[m])
            for m in who
        )
        if not other:
            rep.add("diff_later_run", FAIL, e["seq"], point=p["id"])
            return True
    return False


def check_diff(
    rep: Report,
    pack: dict[str, Any],
    pack_sha: str,
    ledger: dict[str, Any],
    diff: dict[str, Any],
    topics: dict[str, Topic],
    files: AnswersFiles | None,
) -> None:
    """The diff against the ledger (see the module text). `topics` are the pack's
    topics, `files` the answers files given with `--answers`."""
    entries = ledger["entries"]
    if (diff.get("pack") or {}).get("sha256") != pack_sha:
        rep.add("diff_pack", FAIL)
        return
    points = _points(rep, pack, diff)
    _check_files(rep, diff, files, topics)
    heads = {p.get("ledger_head") for p in points}
    if len(heads) > 1:
        rep.add("diff_head_mixed", FAIL, heads=len(heads))
        return
    head = next(iter(heads), None)
    if head is None:
        for p in points:
            if _later(rep, p, entries, topics.get(p["sealed"]["topic"]), diff, files):
                continue
            if p.get("verdict") == "not_tested" and not p.get("changed_since_run"):
                rep.add("diff_nohead", SKIP, point=p["id"])
            else:
                rep.add(
                    "diff_verdict",
                    FAIL,
                    point=p["id"],
                    diff=p.get("verdict"),
                    ledger="-",
                )
        return
    at = next((e["seq"] for e in entries if e["sha256"] == head), None)
    if at is None:
        rep.add("diff_head", FAIL, point=points[0]["id"], head=str(head)[:12])
        return
    rep.add("diff_head_ok", OK, head=str(head)[:12], at=at, later=len(entries) - at)
    then = {"entries": entries[:at]}
    for p in points:
        name = p["sealed"]["topic"]
        if _later(rep, p, entries[at:], topics.get(name), diff, files):
            continue
        shown, logged = p.get("verdict"), topic_verdict(then, name)
        run = last_run(then, name)
        if shown == "not_tested" and run is not None and name in topics:
            _changed_claim(rep, p, run, topics[name], diff, files)
        elif shown == logged and not p.get("changed_since_run"):
            rep.add("diff_verdict_ok", OK, point=p["id"], verdict=shown)
        else:
            rep.add("diff_verdict", FAIL, point=p["id"], diff=shown, ledger=logged)
