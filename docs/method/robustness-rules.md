# Robustness rules R1-R6

The engine's rules for numeric outputs and numeric claims (gate Ж2 Б; stance in `formal-stance.md`). Robustness belongs to the procedure around a formula. Each rule says what the record carries, what the engine does, and where it does not apply. All fields are optional; a record without them reads as before.

## R1 domain

A rule is stated for some range of its inputs. `rule.domain` names the ranges (`{revenue_bn: [0.5, 2.5]}`) and `rule.assumptions` the rest in words. `observed.sample` gives the ranges the field covered. For each name in both:

- a sample range not inside the domain range: the outcome `outside_domain`, no reading, no flips;
- a sample inside that is shorter than the domain: the outcome is read, and the verdict line says which part the sample covers;
- a rule with a domain and an `observed` with no `sample`, or a `sample` that omits a name of the domain: the hint `domain-sample` lists the names missing.

A name the sample lacks is not judged. Below its scale a description stops applying; this is the engine's way to say so.

## R2 intervals

No share without an interval. Satisfied by `verdict.py`: every share verdict carries the 95% Wilson score interval. The record has no other numeric `observed` value that could carry a point estimate (`observed` is k of n; a red line's `observed` is read against a corridor, not estimated), so no further hint is needed.

## R3 bounded sensitivity

Applies to numeric outputs only. Classifications (a verdict, a hint) use R4. A numeric output never divides by a quantity that can reach zero inside its domain; where it could, it returns a status or `None`, never `inf` or NaN. Audit of the numeric code:

| Where | Division | Reaches zero? | Result |
|---|---|---|---|
| `verdict.wilson` | by `n`, by `1 + z*z/n` | `n` below 1 is refused with `ValueError`; the schema requires `n` from 1 | the denominator is at least 1; tested at k = 0, k = n, n = 1 |
| `verdict` Manski and flips | by `n + m` | no: `n` is at least 1 and `m` at least 0 | none needed |
| `agree.alpha_nominal` | by `n - 1`, by `m - 1`, by the expected disagreement `D_e` | `n` and `m` are at least 2 for a pairable unit; `D_e` is 0 only with one value in the data | returns alpha `None` with a reason; the guard for any other `D_e` of 0 is defensive (two or more values always give `D_e` above 0, so no input reaches it) |
| `agree` percentages | by the whole | a whole of 0 | returns `-` |
| `redline` | by a constant year length | no | none |
| `leverage` | none (sizes of sets) | | none |
| `compare` overlap | by the smaller stem set | guarded: only for two or more stems | none |
| drawing code (`render/`, `screen.py`) | by column counts, spans | guarded by `max`, minimums | not a method output |

## R4 fragility

Every share verdict reports `flips`: the smallest number of the n observations whose recoding (k up or down by that number, n fixed) changes the outcome (the Fragility Index; Walsh et al. 2014 [UNVERIFIED]). A verdict that a few recodings undo is firm only that far. `flips` is none when no recoding changes the outcome, and for `too_few`.

If `observed.unknown` is m, the cases of the artefact with a missing outcome, the verdict is also read with none of them counted, k/(n+m), and with all of them, (k+m)/(n+m), Wilson on n+m (Manski bounds; Manski 2003 [UNVERIFIED]). The two readings are shown, not combined. Test case: rule `< 0.30`, k = 122, n = 340, m = 91 gives confirmed, Wilson 0.3097-0.4111, flips 4 (118 of 340 has lower bound 0.2984: inconclusive), 122 of 431 = 0.283 (0.2426-0.3274) inconclusive, 213 of 431 confirmed.

The detail shows after the outcome in the verdict hint of `smd validate --hints`, in `smd status` and in the SessionFlow export.

## R5 rivals

Hypotheses carry no weights. `rivals` lists the ids of other hypotheses that answer the same question (strong inference, Platt 1964 [UNVERIFIED]); they are kept side by side and never averaged. Either side may name the other. `procedures/field-result.md` §0.1 already asks for two or more rival answers and one test that tells them apart; `rivals` records the pairing, and the surprise hint (R6) reads it. Not built: a hint on a model whose rates have no source (`cites`). The schema has no field for rates on a model or a flow (`carries` names what a flow carries, not how much), so there is nothing to check; add the hint when a case records rates.

## R6 unknown unknowns, by procedure

No formula covers a parameter whose existence is unknown. A procedure detects its footprint.

- **A red line needs a recovery time and an address** (the hint `line-without-recovery`, on all three profiles, for every element with `red_line: true` and every algedonic channel with a value). The recovery time is `recovery_time` or `line.recovery_days`. The address is an `escalates` relation to a post, position or place for others, or, on a profile without `escalates`, a `flow` with `carries: information` from the line to one (`management-four-boards` has `escalates`, and only that counts there; Beer, BEER1972 Гл. 17: a unit that cannot restore its index in an acceptable time sends the signal up, and the level above sets the time).
- **Surprise** (the hint `surprise`): a hypothesis with a share rule is refuted by its `observed`, and so is every rival, each read on the same count with the same `metric`. No hypothesis on the board expected the result. The hint proposes a dated `signal` (a `note` on a profile with no signal kind) with `escaped: [ids]`; once an element's `escaped` names the hypothesis, the hint is silent. The log of such elements is the record of what the model set did not foresee.

## Where each rule is enforced

| Rule | Code | Checks and hints |
|---|---|---|
| R1 | `verdict.py` | `domain-sample`; errors on a reversed range; warnings on sample names and on a result recorded outside the domain |
| R2 | `verdict.py` | none beyond the interval |
| R3 | `agree.py`, `verdict.py` | tests at the boundaries |
| R4 | `verdict.py` | the verdict hint, `smd status`, SessionFlow |
| R5 | schema `rivals` | errors on an unknown or own id |
| R6 | `validate/management.py`, `validate/hypotheses.py` | `line-without-recovery`, `surprise`; errors on `escaped` |
