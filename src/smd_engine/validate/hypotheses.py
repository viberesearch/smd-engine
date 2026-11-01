"""Hypotheses: links, and a result only on a field artefact; the typed
standard (`type`) and the decision rule (`rule`, `observed`) of the method
review of 31.10 (gates М1 В, Ф В)."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, board_set, cite_findings, hint
from smd_engine.verdict import (
    CONTRADICTS,
    detail_text,
    is_share,
    of_hypothesis,
    propose,
    rule_line,
    verdict_line,
)


@board_set
def check_hypotheses(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    data = ctx.record
    seen: set[str] = set()
    for h in data.get("hypotheses", []):
        hid = h["id"]
        if hid in seen:
            out.append(Finding("error", hid, "duplicate hypothesis id"))
        seen.add(hid)
        for ref in h.get("targets", []):
            if ref not in ctx.by_id:
                out.append(Finding("error", hid, f"target '{ref}' is not an element"))
        for k in h.get("qualifications", []):
            if k not in ctx.ks:
                out.append(Finding("error", hid, f"'{k}' is not a qualification"))
        if h["status"] in ("confirmed", "refuted"):
            if not h.get("artefacts"):
                out.append(
                    Finding(
                        "error", hid, "a result needs the field artefact it rests on"
                    )
                )
            if not h.get("result"):
                out.append(Finding("error", hid, "a result needs its text in 'result'"))
            if "resolved_in" not in h:
                out.append(Finding("error", hid, "a result needs resolved_in"))
        elif "resolved_in" in h:
            out.append(
                Finding("warning", hid, "resolved_in set but no result was recorded")
            )
        if h["status"] == "testing" and not h.get("action"):
            out.append(Finding("warning", hid, "testing, but no action is named"))
        if h.get("raised_in", 0) > data["cycle"]:
            out.append(
                Finding("error", hid, "raised in a later cycle than this record")
            )
        if h.get("resolved_in", 10**6) < h.get("raised_in", 0):
            out.append(Finding("error", hid, "resolved before it was raised"))
        out += _observed_findings(h)
        out += _domain_findings(h)
        out += _rival_findings(h, ctx.hyps)
        out += cite_findings(h.get("artefacts", []), hid, ctx.source_ids)
        if "observed" in h:
            out += cite_findings([h["observed"]["artefact"]], hid, ctx.source_ids)
            out += _artefact_kind(h, ctx.source_kinds)
        out += cite_findings(h.get("cites", []), hid, ctx.source_ids)
    out += _escaped_findings(ctx)
    return out


def _range_errors(found: Any, what: str, where: str) -> list[Finding]:
    """A range with its minimum above its maximum (the schema checks the shape)."""
    return [
        Finding(
            "error", where, f"{what} '{name}': min {pair[0]:g} is above max {pair[1]:g}"
        )
        for name, pair in (found or {}).items()
        if pair[0] > pair[1]
    ]


def _domain_findings(h: dict[str, Any]) -> list[Finding]:
    """R1: ranges the right way round; sample names the domain does not name;
    a recorded result on a sample outside the domain."""
    rule, obs = h.get("rule") or {}, h.get("observed") or {}
    hid = h["id"]
    out = _range_errors(rule.get("domain"), "domain", hid)
    out += _range_errors(obs.get("sample"), "sample", hid)
    if rule.get("domain") and obs.get("sample"):
        extra = sorted(set(obs["sample"]) - set(rule["domain"]))
        if extra:
            out.append(
                Finding(
                    "warning",
                    hid,
                    f"sample names {', '.join(extra)}, which the rule's domain does not",
                )
            )
    v = None if any(f.level == "error" for f in out) else of_hypothesis(h)
    if v and v.outcome == "outside_domain" and h["status"] in ("confirmed", "refuted"):
        out.append(
            Finding(
                "warning",
                hid,
                f"recorded {h['status']}, but the sample leaves the rule's domain: "
                f"{detail_text(v)}",
            )
        )
    return out


def _rival_findings(
    h: dict[str, Any], hyps: dict[str, dict[str, Any]]
) -> list[Finding]:
    """R5: a rival is another hypothesis of the record."""
    out = []
    for r in h.get("rivals", []):
        if r == h["id"]:
            out.append(Finding("error", h["id"], "a hypothesis is not its own rival"))
        elif r not in hyps:
            out.append(Finding("error", h["id"], f"rival '{r}' is not a hypothesis"))
    return out


# Kinds that may record a surprise: the default profile's signal, else a note.
SURPRISE_KINDS = ("signal", "note")


def _escaped_findings(ctx: Ctx) -> list[Finding]:
    """R6: `escaped` names hypotheses of the record, is for a signal or a
    note, and goes with the `date` of the surprise."""
    out: list[Finding] = []
    for el in ctx.by_id.values():
        eid = el["id"]
        if "date" in el and "escaped" not in el:
            out.append(
                Finding(
                    "error", eid, "'date' is only for a surprise: it needs 'escaped'"
                )
            )
        if "escaped" not in el:
            continue
        if el["kind"] not in SURPRISE_KINDS:
            out.append(
                Finding(
                    "error", eid, "'escaped' is only for " + " or ".join(SURPRISE_KINDS)
                )
            )
        if "date" not in el:
            out.append(
                Finding("error", eid, "'escaped' needs the 'date' of the surprise")
            )
        out += [
            Finding("error", eid, f"escaped '{h}' is not a hypothesis")
            for h in el["escaped"]
            if h not in ctx.hyps
        ]
    return out


def _observed_findings(h: dict[str, Any]) -> list[Finding]:
    """k of n: k no more than n; a recorded result the proposed verdict
    contradicts (confirmed while the whole interval refutes, or the reverse)."""
    obs = h.get("observed")
    if not obs:
        return []
    if obs["k"] > obs["n"]:
        return [
            Finding("error", h["id"], f"observed k={obs['k']} exceeds n={obs['n']}")
        ]
    v = of_hypothesis(h)
    if v and CONTRADICTS.get(h["status"]) == v.outcome:
        detail = detail_text(v)
        return [
            Finding(
                "warning",
                h["id"],
                f"recorded {h['status']}, but by the rule ({rule_line(h['rule'])}) "
                f"{verdict_line(v)} proposes {v.outcome}"
                + (f"; {detail}" if detail else ""),
            )
        ]
    return []


def _artefact_kind(h: dict[str, Any], kinds: dict[str, str] | None) -> list[Finding]:
    """The source counted in `observed` is a field artefact, when the manifest
    is given (field-result.md §0.2); an unknown id is reported by cite_findings."""
    sid = h["observed"]["artefact"].split("#")[0]
    kind = (kinds or {}).get(sid)
    if kind is None or kind == "field_artefact":
        return []
    return [
        Finding(
            "warning",
            h["id"],
            f"observed counts '{sid}', a source of kind '{kind}', not field_artefact",
        )
    ]


# Statuses with no recorded result: the verdict hint reads them.
OPEN = ("untested", "testing")
# Types read without a refutation condition: not tested, or exploration.
UNTESTED_TYPES = ("core", "design", "probe")
# Types that need a decision rule written before the field.
RULED_TYPES = ("claim", "estimate")


@hint("hypothesis-type")
def hint_hypothesis_type(ctx: Ctx) -> list[Finding]:
    """An untyped hypothesis raised in a cycle in which other hypotheses are
    typed: once a cycle uses the standard, its new rows follow it. Records
    with no typed hypothesis, and hypotheses with no `raised_in`, are left
    alone."""
    hyps = ctx.record.get("hypotheses", [])
    typed = {h["raised_in"] for h in hyps if "type" in h and "raised_in" in h}
    return [
        Finding(
            "hint",
            h["id"],
            "no type, while other hypotheses of its cycle have one "
            "(core, product, claim, estimate, probe, design)",
        )
        for h in hyps
        if "type" not in h and h.get("raised_in") in typed
    ]


@hint("hypothesis-rule")
def hint_hypothesis_rule(ctx: Ctx) -> list[Finding]:
    return [
        Finding(
            "hint",
            h["id"],
            f"a {h['type']} with no decision rule: write `rule` (or at least "
            "`revise_if`) before the field",
        )
        for h in ctx.record.get("hypotheses", [])
        if h.get("type") in RULED_TYPES and not h.get("rule") and not h.get("revise_if")
    ]


@hint("rule-basis")
def hint_rule_basis(ctx: Ctx) -> list[Finding]:
    return [
        Finding(
            "hint",
            h["id"],
            f"the threshold {h['rule']['threshold']:g} has no basis: say what "
            "decision it changes or where it comes from",
        )
        for h in ctx.record.get("hypotheses", [])
        if h.get("rule") and not h["rule"].get("basis")
    ]


@hint("rule-n-min")
def hint_rule_n_min(ctx: Ctx) -> list[Finding]:
    return [
        Finding(
            "hint",
            h["id"],
            "an estimate with a rule but no n_min: how many cases is it read on?",
        )
        for h in ctx.record.get("hypotheses", [])
        if h.get("type") == "estimate" and h.get("rule") and "n_min" not in h["rule"]
    ]


@hint("type-status")
def hint_type_status(ctx: Ctx) -> list[Finding]:
    """A probe explores and tests nothing: it is not confirmed or refuted. A
    core of the programme or a design choice is not tested at all."""
    out: list[Finding] = []
    for h in ctx.record.get("hypotheses", []):
        kind, status = h.get("type"), h["status"]
        if kind == "probe" and status in ("confirmed", "refuted"):
            message = (
                f"a probe is {status}: exploration produces hypotheses, tests none"
            )
        elif kind in ("core", "design") and status != "untested":
            message = f"a {kind} is {status}: it is not tested; leave it untested"
        else:
            continue
        out.append(Finding("hint", h["id"], message))
    return out


@hint("verdict")
def hint_verdict(ctx: Ctx) -> list[Finding]:
    """The verdict proposed by the rule for each hypothesis in `testing` with
    `observed`; the group signs `accept_result`. An `untested` one with
    `observed` gets no proposal, only the advice to set it `testing`."""
    out: list[Finding] = []
    for h in ctx.record.get("hypotheses", []):
        obs = h.get("observed")
        # a recorded result is not re-proposed; a contradiction is a warning
        if not obs or obs["k"] > obs["n"] or h["status"] not in OPEN:
            continue
        rule = h.get("rule")
        if h["status"] == "untested":
            out.append(
                Finding(
                    "hint",
                    h["id"],
                    "observed data recorded but status is untested: set testing, "
                    "then the rule proposes a verdict",
                )
            )
            continue
        if not rule:
            message = "observed, but no rule to read it by"
        elif not is_share(rule):
            message = (
                f"no proposal: the threshold {rule['threshold']:g} is not a share "
                "(strictly between 0 and 1)"
            )
        else:
            v = of_hypothesis(h)
            assert v is not None
            word = {
                "too_few": f"too few (n_min {rule.get('n_min')}), stays testing",
                "refuted": "refuted",
                "confirmed": "confirmed",
                "inconclusive": "inconclusive, stays testing",
                "outside_domain": "outside the rule's domain, no proposal",
            }[v.outcome]
            detail = detail_text(v)
            message = (
                f"proposed by the rule ({rule_line(rule)}): {verdict_line(v)}: "
                f"{word}; "
                + (f"{detail}; " if detail else "")
                + "the group signs accept_result"
            )
        out.append(Finding("hint", h["id"], message))
    return out


@hint("domain-sample")
def hint_domain_sample(ctx: Ctx) -> list[Finding]:
    """R1: a rule with a `domain` and an `observed` with no `sample`, or a
    `sample` that omits some of the domain's names: the verdict cannot say
    whether the field covered that part of the domain."""
    out: list[Finding] = []
    for h in ctx.record.get("hypotheses", []):
        domain = (h.get("rule") or {}).get("domain")
        if not domain or not h.get("observed"):
            continue
        sample = h["observed"].get("sample")
        if not sample:
            message = (
                "the rule has a domain, but observed has no sample: give the "
                f"ranges the field covered ({', '.join(domain)})"
            )
        elif missing := [name for name in domain if name not in sample]:
            message = (
                "the rule has a domain, but the sample omits "
                f"{', '.join(missing)}: give the ranges the field covered"
            )
        else:
            continue
        out.append(Finding("hint", h["id"], message))
    return out


def _rivals_of(hid: str, hyps: dict[str, dict[str, Any]]) -> list[str]:
    """The rivals of a hypothesis, either side naming the other, in order."""
    found = list(hyps[hid].get("rivals", []))
    found += [g for g, other in hyps.items() if hid in other.get("rivals", [])]
    return [r for n, r in enumerate(found) if r in hyps and r not in found[:n]]


@hint("surprise")
def hint_surprise(ctx: Ctx) -> list[Finding]:
    """R6: an observed result outside the interval of the hypothesis and of
    every rival, each rival read on the same count (same metric, a share
    rule). No model on the board expects it: the hint proposes a dated
    surprise, a `signal` (a `note` where the profile has no signal) with
    `escaped` naming them. Only for a hypothesis in `testing`. Silent once an element's `escaped` names the
    hypothesis."""
    logged = {h for el in ctx.by_id.values() for h in el.get("escaped", [])}
    kind = "signal" if ctx.profile.has_kind("signal") else "note"
    out: list[Finding] = []
    for hid, h in ctx.hyps.items():
        obs, rule = h.get("observed"), h.get("rule")
        # a hypothesis in testing, as for the hint verdict; a recorded
        # result is not proposed again, an untested one is set testing first
        if h["status"] != "testing" or not obs or not rule or hid in logged:
            continue
        if obs["k"] > obs["n"]:
            continue
        rivals = _rivals_of(hid, ctx.hyps)
        v = of_hypothesis(h)
        if not rivals or v is None or v.outcome != "refuted":
            continue
        if not all(_refutes(ctx.hyps[r], rule["metric"], obs) for r in rivals):
            continue
        out.append(
            Finding(
                "hint",
                hid,
                f"{verdict_line(v)} is outside the interval of {hid} and of its "
                f"rivals {', '.join(rivals)}: no hypothesis on the board expects "
                f"it. Record a surprise: a {kind} with date and escaped: "
                f"[{', '.join([hid, *rivals])}]",
            )
        )
    return out


def _refutes(rival: dict[str, Any], metric: str, obs: dict[str, Any]) -> bool:
    """Whether the rival's own share rule, on the same metric, is refuted by
    this count."""
    rule = rival.get("rule")
    if not rule or rule["metric"] != metric:
        return False
    v = propose(rule, obs)
    return v is not None and v.outcome == "refuted"
