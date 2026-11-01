"""A proposed verdict for a hypothesis by its pre-registered decision rule.

A hypothesis may carry `rule` (`{metric, op, threshold, n_min, basis}`: the
refutation condition written before the field, like `revise_if`) and
`observed` (`{k, n, artefact}`: k of n cases in a field artefact). When the
threshold is a share (strictly between 0 and 1), the engine computes the Wilson score interval
of k/n and proposes a verdict:

- `too_few`: n is below `n_min`;
- `refuted`: the whole interval lies on the refuting side of the threshold;
- `confirmed`: the whole interval lies on the holding side;
- `inconclusive`: the interval straddles the threshold; H stays `testing`;
- `outside_domain`: the sample leaves the rule's domain (R1); no reading.

`op` states when the hypothesis is refuted: `{metric: "доля 55+", op: "<",
threshold: 0.20}` is refuted if the share is below 0.20. The interval is
two-sided 95% and read on one side, so the proposal is conservative.

Robustness rules (docs/method/robustness-rules.md):

- R1 domain: a rule may carry `domain` (named ranges, `{revenue_bn: [0.5,
  2.5]}`) and `observed` a `sample` (the ranges it covers). A sample that
  leaves the domain gets `outside_domain`, with no reading; one inside it that
  covers only part keeps its outcome and says which part.
- R4 fragility: `flips` is the smallest number of the n observations whose
  recoding (k up or down, n fixed) changes the outcome (the Fragility Index,
  Walsh et al. 2014, Journal of Clinical Epidemiology 67(6)). `observed` may
  carry `unknown: m`, cases with a missing outcome; the verdict is then also
  read with none of them counted in k and with all of them (Manski bounds,
  k/(n+m) and (k+m)/(n+m); Manski 2003, Partial Identification of Probability
  Distributions), Wilson on n+m.

The verdict is a proposal (audit of 31.10, formal section 4, row 6; gate Ф В):
the record changes only after an `accept_result` sign-off by a human.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

# The 0.975 quantile of the standard normal distribution: a 95% interval.
Z95 = 1.959963984540054

Outcome = Literal["too_few", "refuted", "confirmed", "inconclusive", "outside_domain"]


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """The Wilson score interval of the proportion k/n, without continuity
    correction (Wilson, E. B. (1927). Probable inference, the law of
    succession, and statistical inference. *Journal of the American
    Statistical Association*, 22(158), 209-212). For k = 81, n = 263 it gives
    0.2553 to 0.3662, the Wilson-score value of Newcombe, R. G. (1998).
    Two-sided confidence intervals for the single proportion: comparison of
    seven methods. *Statistics in Medicine*, 17(8), 857-872. Ends are clamped
    to [0, 1] against rounding."""
    if n < 1 or not 0 <= k <= n:
        raise ValueError(f"need 0 <= k <= n and n >= 1, got k={k}, n={n}")
    p = k / n
    zz = z * z
    denom = 1 + zz / n
    centre = (p + zz / (2 * n)) / denom
    half = z / denom * math.sqrt(p * (1 - p) / n + zz / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def _sides(op: str, t: float, low: float, high: float) -> tuple[bool, bool]:
    """(the whole interval refutes, the whole interval holds) for the
    refutation condition `share <op> t`."""
    if op == "<":
        return high < t, low >= t
    if op == "<=":
        return high <= t, low > t
    if op == ">":
        return low > t, high <= t
    if op == ">=":
        return low >= t, high < t
    raise ValueError(f"unknown op '{op}'")


# A range as written in `domain` and `sample`: (name, low, high).
Range = tuple[str, float, float]


@dataclass(frozen=True)
class Verdict:
    outcome: Outcome
    k: int
    n: int
    low: float
    high: float
    # R4: recodings that change the outcome; None when none can (or too few)
    flips: int | None = None
    # R4: cases with a missing outcome, and the verdict if none, if all, of
    # them had the outcome counted in k
    unknown: int = 0
    none_counted: Verdict | None = None
    all_counted: Verdict | None = None
    # R1: sample ranges outside the domain, and inside it but covering part:
    # (name, sample low, sample high, domain low, domain high)
    outside: tuple[tuple[str, float, float, float, float], ...] = ()
    partial: tuple[tuple[str, float, float, float, float], ...] = ()

    @property
    def share(self) -> float:
        return self.k / self.n


def is_share(rule: dict[str, Any]) -> bool:
    """A rule whose threshold is a share strictly between 0 and 1: the only
    kind with a verdict (no share is below 0 or above 1)."""
    t = rule.get("threshold")
    return isinstance(t, (int, float)) and 0 < t < 1


def _read(rule: dict[str, Any], k: int, n: int) -> tuple[Outcome, float, float]:
    """The outcome of k/n by the rule, without the domain, and the interval."""
    low, high = wilson(k, n)
    if n < rule.get("n_min", 0):
        return "too_few", low, high
    refutes, holds = _sides(rule["op"], rule["threshold"], low, high)
    outcome: Outcome = (
        "refuted" if refutes else "confirmed" if holds else "inconclusive"
    )
    return outcome, low, high


def fragility(rule: dict[str, Any], k: int, n: int) -> int | None:
    """R4, the smallest d >= 1 such that recoding d of the n observations (k
    becomes k - d or k + d, n fixed) changes the outcome; None when no
    recoding does, or when n is below `n_min` (the outcome is then too_few
    whatever the coding)."""
    base = _read(rule, k, n)[0]
    if base == "too_few":
        return None
    for d in range(1, n + 1):
        down, up = k - d, k + d
        if (down >= 0 and _read(rule, down, n)[0] != base) or (
            up <= n and _read(rule, up, n)[0] != base
        ):
            return d
        if down < 0 and up > n:
            break
    return None


def _ranges(found: Any) -> dict[str, tuple[float, float]]:
    """The well-formed ranges of a `domain` or `sample` mapping; the validator
    reports the others."""
    out: dict[str, tuple[float, float]] = {}
    if isinstance(found, dict):
        for name, pair in found.items():
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                lo, hi = pair
                if all(isinstance(x, (int, float)) for x in (lo, hi)) and lo <= hi:
                    out[str(name)] = (float(lo), float(hi))
    return out


def domain_cover(rule: dict[str, Any], observed: dict[str, Any]) -> tuple[
    list[tuple[str, float, float, float, float]],
    list[tuple[str, float, float, float, float]],
]:
    """R1, for each name in both the rule's `domain` and the observed `sample`:
    (outside, partial). A sample range not inside the domain range is outside;
    one inside that is shorter than the domain range is partial. A name the
    sample does not give is not judged (the hint `domain-sample` asks for the
    sample)."""
    domain = _ranges(rule.get("domain"))
    sample = _ranges(observed.get("sample"))
    outside, partial = [], []
    for name, (dlo, dhi) in domain.items():
        if name not in sample:
            continue
        slo, shi = sample[name]
        row = (name, slo, shi, dlo, dhi)
        if slo < dlo or shi > dhi:
            outside.append(row)
        elif slo > dlo or shi < dhi:
            partial.append(row)
    return outside, partial


def _plain(rule: dict[str, Any], k: int, n: int) -> Verdict:
    """The verdict of k/n alone: no domain, fragility or unknown cases."""
    outcome, low, high = _read(rule, k, n)
    return Verdict(outcome, k, n, low, high)


def propose(rule: dict[str, Any], observed: dict[str, Any]) -> Verdict | None:
    """The proposed verdict, or None when the threshold is not a share."""
    if not is_share(rule):
        return None
    k, n = observed["k"], observed["n"]
    outside, partial = domain_cover(rule, observed)
    outcome, low, high = _read(rule, k, n)
    if outside:
        return Verdict(
            "outside_domain",
            k,
            n,
            low,
            high,
            outside=tuple(outside),
            partial=tuple(partial),
        )
    m = observed.get("unknown", 0)
    none_counted = all_counted = None
    if m > 0:
        none_counted = _plain(rule, k, n + m)
        all_counted = _plain(rule, k + m, n + m)
    return Verdict(
        outcome,
        k,
        n,
        low,
        high,
        fragility(rule, k, n),
        m,
        none_counted,
        all_counted,
        partial=tuple(partial),
    )


def of_hypothesis(h: dict[str, Any]) -> Verdict | None:
    """The proposed verdict of a hypothesis with `rule` and a consistent
    `observed` (k <= n), else None."""
    rule, obs = h.get("rule"), h.get("observed")
    if not rule or not obs or obs["k"] > obs["n"]:
        return None
    return propose(rule, obs)


# What a proposal says against the recorded status: the opposite result.
CONTRADICTS = {"confirmed": "refuted", "refuted": "confirmed"}


def rule_line(rule: dict[str, Any]) -> str:
    """`доля 55+ < 0.2` with `, n >= 30` when n_min is set and `, revenue_bn
    0.5-2.5` for each range of the domain (no words, so the line reads the
    same in either language)."""
    line = f"{rule['metric']} {rule['op']} {rule['threshold']:g}"
    line += f", n >= {rule['n_min']}" if "n_min" in rule else ""
    for name, (lo, hi) in _ranges(rule.get("domain")).items():
        line += f", {name} {lo:g}-{hi:g}"
    return line


def verdict_line(v: Verdict) -> str:
    """`12/40 = 0.30, Wilson 95% 0.18-0.45`."""
    return f"{v.k}/{v.n} = {v.share:.2f}, Wilson 95% {v.low:.2f}-{v.high:.2f}"


# The outcome in a few words, for the detail line.
SHORT = {
    "en": {
        "too_few": "too few",
        "refuted": "refuted",
        "confirmed": "confirmed",
        "inconclusive": "inconclusive",
        "outside_domain": "outside the domain",
    },
    "ru": {
        "too_few": "мало случаев",
        "refuted": "опровергнуто",
        "confirmed": "подтверждено",
        "inconclusive": "не решено",
        "outside_domain": "вне области",
    },
}

DETAIL = {
    "en": {
        "flips": "recoding {d} of {n} observations changes the outcome",
        "no_flips": "no recoding of the {n} observations changes the outcome",
        "unknown": "{m} with the outcome unknown: if none of them is in k, {a}; if all of them are in k, {b}",
        "outside": "sample {name} {lo:g}-{hi:g} is outside the domain {dlo:g}-{dhi:g}",
        "partial": "the sample covers {name} {lo:g}-{hi:g} of the domain {dlo:g}-{dhi:g}",
    },
    "ru": {
        "flips": "перекодировка {d} из {n} наблюдений меняет исход",
        "no_flips": "никакая перекодировка {n} наблюдений не меняет исход",
        "unknown": "у {m} исход неизвестен: если ни один из них не входит в k, {a}; если все входят в k, {b}",
        "outside": "выборка {name} {lo:g}-{hi:g} вне области {dlo:g}-{dhi:g}",
        "partial": "выборка покрывает {name} {lo:g}-{hi:g} из области {dlo:g}-{dhi:g}",
    },
}


def detail_text(v: Verdict, lang: str = "en") -> str:
    """What the robustness rules add to a verdict line, as one phrase (empty
    when there is nothing to add): the part of the domain the sample leaves or
    covers (R1), the fragility (R4) and the outcomes at the two ends of the
    unknown cases (R4, Manski)."""
    words, short = DETAIL[lang], SHORT[lang]
    parts = [
        words["outside"].format(name=r[0], lo=r[1], hi=r[2], dlo=r[3], dhi=r[4])
        for r in v.outside
    ]
    parts += [
        words["partial"].format(name=r[0], lo=r[1], hi=r[2], dlo=r[3], dhi=r[4])
        for r in v.partial
    ]
    if v.outcome not in ("too_few", "outside_domain"):
        parts.append(
            words["flips"].format(d=v.flips, n=v.n)
            if v.flips is not None
            else words["no_flips"].format(n=v.n)
        )
    if v.none_counted is not None and v.all_counted is not None:
        ends = [
            f"{verdict_line(x)}, {short[x.outcome]}"
            for x in (v.none_counted, v.all_counted)
        ]
        parts.append(words["unknown"].format(m=v.unknown, a=ends[0], b=ends[1]))
    return "; ".join(parts)
