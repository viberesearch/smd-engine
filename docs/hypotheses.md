# Hypotheses (field tests)

The inter-module form: what we assume, how we test it, what we got, what it changes. The field gives the result; the group accepts it by a sign-off.

| Field | Meaning |
|---|---|
| `id` | `H1..Hn`; a part of a split hypothesis adds one lowercase Latin letter: `H2a`, `H2b` |
| `assumes`, `action`, `observe`, `revise_if` | что предполагаем, каким действием проверяем, что будем наблюдать, какой результат заставит пересмотреть |
| `status` | `untested`, `testing`, `confirmed`, `refuted` |
| `result`, `changes` | what the test gave; what it changes on the boards |
| `targets`, `qualifications` | element ids and K ids it is about |
| `artefacts` | the field artefacts the result rests on: manifest ids of kind `field_artefact` |
| `raised_in`, `resolved_in` | cycle numbers |
| `voice` | who formulated it, free text (no enum, unlike an element's); `AI`, `ai` and `ИИ` all mark an AI draft, which is listed as a hint until a human keeps or drops it |
| `lens` | the lens behind it, as on elements; ontology records take `lens` too |
| `tags` | as on elements; ontology records take `tags` too |
| `type` | how it is read (gate М1 В; `procedures/field-result.md` §0.1): `core` (core of the programme, not tested directly), `product` (methodological product, tested for realizability, GP1981), `claim` (one empirical claim, falsified by a condition written before the field), `estimate` (a share, cost or frequency: an interval against a decision threshold), `probe` (a few interviews: produces hypotheses, tests none), `design` (design choice or vision, not tested) |
| `rule` | the pre-registered decision rule, a structured `revise_if` (gate Ф В): `{metric, op, threshold, n_min, basis}`; refuted when `<metric> <op> <threshold>` (`op`: `<`, `<=`, `>`, `>=`); `n_min` (integer from 1) the fewest cases it is read on; `basis` where the threshold comes from; optional `domain` (named numeric ranges the rule is stated for, `{revenue_bn: [0.5, 2.5]}`; R1) and `assumptions` (free text). `metric`, `op` and `threshold` are required |
| `observed` | what the field gave for the rule: `{k, n, artefact}`, k cases of n (k from 0, n from 1, k no more than n) in a source of kind `field_artefact`; optional `unknown` (cases with a missing outcome, not in n; R4) and `sample` (the ranges the field covered; R1) |
| `rivals` | ids of hypotheses that answer the same question otherwise (strong inference, Platt 1964; R5). Carried side by side, never averaged or weighted |

A result (`confirmed` or `refuted`) needs `result`, `artefacts`, `resolved_in` and an `accept_result` sign-off. With `rule` and `observed`, a threshold strictly between 0 and 1, and the hypothesis `testing`, the engine proposes a verdict from the 95% Wilson score interval of k/n (`src/smd_engine/verdict.py`): too few (n below `n_min`), refuted (the whole interval on the refuting side), confirmed (on the holding side) or inconclusive (it straddles the threshold); `smd validate --hints` and `smd status` print it. An `untested` hypothesis with `observed` gets no proposal, only the hint to set it `testing`. The proposal changes nothing: the sign-off stays human.

## Robustness fields (rules R1, R4, R5, R6)

`docs/method/robustness-rules.md` states the rules; this is how the record carries them.

- `rule.domain` and `observed.sample` (R1): a `sample` range not inside the matching `domain` range gives the outcome `outside_domain` (no reading); a sample inside it that covers only part keeps its outcome, and the verdict line says which part. A rule with a `domain` and an `observed` with no `sample` gets the hint `domain-sample`. A `sample` name the domain lacks is a warning; a range with min above max is an error.
- `observed.unknown` (R4): m cases of the artefact with no outcome. The verdict is also read with none of them counted in k and with all of them: k/(n+m) and (k+m)/(n+m), Wilson on n+m (Manski bounds). Every verdict on a share also reports `flips`: the smallest number of the n observations whose recoding changes the outcome (Fragility Index). Both show in the verdict line of `smd validate --hints`, `smd status` and the SessionFlow export.
- `rivals` (R5): ids of other hypotheses of the record; an unknown id, or the hypothesis itself, is an error. Hypotheses name rivals on one side; the other side is found.
- `escaped` and `date` on an element (R6): a surprise log. The hint `surprise` fires when a hypothesis in `testing` with a share rule is refuted by its `observed` and every rival, read on the same count with the same `metric`, is refuted too. The answer is a `signal` (a `note` on a profile with no signal kind) with `date` and `escaped: [ids]`. `escaped` goes only on a signal or note, needs `date`, and names hypotheses of the record; `date` goes only with `escaped`.
