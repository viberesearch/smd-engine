# Formal stance: where the engine uses mathematics

Gate Ж1 Б (the case owner, 1 November 2026). This file says what kind of mathematics the engine uses, for which parts of a case, and what it never does. It governs `src/smd_engine/verdict.py`, `leverage.py`, `redline.py`, `agree.py` and any later numeric check. Citations are from memory and marked [UNVERIFIED] until checked against the primary text (the marks of `sources.md`).

## The principle

1. **A formula attaches only to a component marked `nature: natural`.** A natural component is one that goes on without anyone designing it: owners ageing, firms drifting through a revenue band, the funnel of deals. The field `nature` (`natural`, `artificial`, `both`) exists on the elements of an object board. A count, a share, a rate or a hazard is a statement about natural components or about a population of them. The engine's counting rules (the Wilson interval of a share, the fragility of a verdict, the agreement of labels) apply to observations of such components.
2. **Answers are sets, never trajectory forecasts.** The engine asks which configurations are consistent with the record, whether a state lies inside its corridor (`line`), which regime a situation is in. It does not say what a firm, a market or a person will do next year. A verdict is an interval and a status, not a prediction.
3. **Artificial components get design mathematics.** A component that people set up (a rule, a contract, a channel, a procedure) is not forecast; it is designed. The mathematics asked of it is whether the rule keeps working when the types of its participants are unknown: bounds, worst cases, minimax regret. Robustness belongs to the procedure around a formula, not to the formula (`robustness-rules.md`).
4. **No weights.** Rival models are carried side by side and never averaged (the case owner, 26.10).

The engine proposes; a human signs. Every numeric proposal is a hint or a status line, and the record changes only by a sign-off.

## Grounds

- **G.P. Shchedrovitsky, 1988 lectures (GP-T5, p. 251).** Forecasting in organisational management is «форма подмены принципов оргуправленческой работы сциентистскими принципами». The engine already encodes this: the hint `ought-without-fact` (`validate/hints.py`) cites GP-T5 p. 251 for dropping the 1981 forecast of GP-Guide5 ¶7, and p. 252 for starting artificial action from the natural processes that limit it. `design-the-natural` (GP-STS, GP-T5 p. 231) says a natural process is used or managed, not designed. [the page numbers and the quotation are those the hints and `validate/management.py` cite; not re-read]
- **Lucas (1976),** "Econometric policy evaluation: a critique", Carnegie-Rochester Conference Series on Public Policy 1. When agents know a forecast or a policy rule, their behaviour changes and the estimated relation stops holding. A trajectory forecast of a system of such agents is therefore unsafe. [UNVERIFIED]
- **Grunberg and Modigliani (1954),** "The predictability of social events", Journal of Political Economy 62(6). The narrow conditions under which a public forecast can still come true. They are the exception that keeps the claim exact: it is forecasts of reactive systems that are refused, not every prediction. [UNVERIFIED]
- **Dekel, Lipman and Rustichini (1998),** "Standard state-space models preclude unawareness", Econometrica 66(1). A modeller or an actor cannot list in advance the states and parameters of which they are unaware. No formula covers a parameter whose existence is unknown; only a procedure that watches for its footprint can (rule R6). [UNVERIFIED]

The research note behind this stance also cites Daskalakis et al. (2009) on the computational hardness of equilibria, Jaynes (1957) on maximum entropy and Gutenkunst et al. (2007) on sloppy models. They explain why few-parameter descriptions work at all; the engine does not rely on them. [UNVERIFIED]

## What the stance rules in and out

| In | Out |
|---|---|
| The Wilson interval of a share, and how many observations it takes to flip it | A point estimate with no interval |
| Corridors, red lines and breach runs from dated observations | A forecast that a corridor will be kept |
| Consistency of labels across runs (Krippendorff's alpha) | A score of how good a board is |
| Counting what a refutation would reach (leverage) | A probability that a hypothesis is true |
| Worst and best case over a named gap (Manski bounds) | Averaging rival hypotheses, or weighting them |
| Rules for the artificial parts that hold for any participant types | A simulation of a firm (system dynamics, agent-based) |

A firm simulation would have to give every rate a source and would still fall to the reflexivity of Lucas's critique. The engine does not build one; if a case brings a model with rates, rule R5 asks that each rate cite a source before anything is simulated (not built: the schema has no rates, so the engine checks nothing here yet).

## The six robustness rules

The engine's rules for any numeric output or numeric claim. Fields and checks are in `robustness-rules.md`.

| Rule | In one line |
|---|---|
| R1 domain | A rule is stated for named ranges; a sample outside them gets `outside_domain` and no reading; a partial sample says which part |
| R2 intervals | No share without an interval |
| R3 bounded sensitivity | A numeric output never divides by a quantity that can reach zero inside its domain; it returns a status instead |
| R4 fragility | Every share verdict says how many observations would flip it, and its outcome at the two ends of the unknown cases |
| R5 rivals | Rival hypotheses are carried, never averaged; no simulation before every rate has a source (not built: the schema has no rates) |
| R6 unknown unknowns | By procedure: a red line needs a recovery time and an address; a result outside every rival's interval is logged as a dated surprise |

## Hand rules for people

Where a group has no model and two or three interviews, three rules need none: maximin (choose the option whose worst case is best; Wald), minimax regret (choose the option whose largest regret is least; Savage 1951) and satisficing (stop at the first option that clears the stated bar; Simon 1955). They suit the artificial components of point 3. [UNVERIFIED]
