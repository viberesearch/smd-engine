---
id: design-chain
title: "Design chain for a pass between positions (goal, beneficiary, subject, form, technologies, conditions, result)"
version: 0.2.1
source: "Report P, a design study of organised transfer prepared for the program by a model run (local, not in the repo): its closing design chain and its classification rule, as read in a local digest; generalised by this lens"
route: smd
offered_by: [positional-construction, functional-plan]
---

# Design chain for a pass between positions

A lens for designing how something passes from one position to another, so that the pass is checked link by link: what is to be achieved, for whom, what exactly passes, in what form it is held afterwards, with what instruments, under what conditions, and how the result will be seen.

The source is report P, a design study of organised transfer, prepared for the program by a model run. It is written as comparative law and service design, with no SMD vocabulary. It ends with a design chain and states one rule for classifying what people call a purpose. This lens keeps both and widens "subject of transfer" to whatever passes between positions. Every widening is marked. The report's own content (its tables, country sections and the roles it names) is not reproduced.

Marks: **[P]** stated in report P as the digest reads it; **[X]** this lens's extrapolation; **[?]** not shown in the digest or open in the source.

## The chain and the rule

The chain, in the order P closes with [P]:

1. goal (in P, a preservation goal);
2. beneficiary;
3. subject of transfer;
4. form of ownership and management;
5. enabling technologies;
6. mandatory conditions;
7. observable result.

The rule [P]: classify purpose, method of transfer and enabling instrument separately. A platform, a loan, a register and an advisory service serve purposes but are not purposes. In this lens:
- **purpose**: what is to be preserved or achieved, in whose interest;
- **method**: the way the subject passes (sale, gift, lease, delegation, split into parts) [X wording];
- **instrument**: what makes a method workable (a service, a loan, a register, a rule of relief).

Subject of transfer, generic reading [X]: whatever passes between positions. It may be an asset, a task, a product, a place in a chain, a responsibility. P splits what passes into four subjects and says that one method of passing can change only the first [P]. This lens reads the four generically [X]:
- (a) the formal right: who may dispose;
- (b) authority to act and decide;
- (c) knowledge and relations;
- (d) obligations and benefits: what is owed and what is earned.

Passing (a) alone changes only (a) [P, generalised].

## When to use

- A move needs something to pass between positions and the group must design the pass: a right, a task, a product, a place in a chain. In the engine: `positional-construction` section 3 (the `flow` relations between positions: what passes, from whom, to whom) and `functional-plan` section 3 (who performs, pays and receives).
- When the first answer to "what is the goal?" is a tool ("an exchange", "a loan", "a platform"). The classification rule exists for that case.
- Not to describe a practice that already exists (`small-situation`), and not to rank purposes across a whole field. Report P ranks nothing [P].

## Questions

1. **Goal.** What is to be preserved or achieved, and what would the parties regard as an unacceptable loss? Ask the loss first, before any form of the pass is named [P: the first interview opens with it]. Write the goal as a purpose, not as a method or an instrument.
2. **Classification.** For each item named so far, is it a purpose, a method of passing or an instrument? Move any misfiled item to its class, and say what purpose it serves. [P]
3. **Beneficiary.** Whose interests decide? Who else bears the loss or the cost? Where two beneficiaries want different goals, which goals conflict? [P: the table of purposes names whose interests decide; P has a section on conflicts]
4. **Subject.** What passes, from which position to which? For each of (a) to (d): does it pass, when, and what stays behind or is lost? [P, generalised X]
5. **Form.** After the pass, who holds the right, who acts, and how are the two tied? May they be separated? [P: "ownership and management form"; the wording is generalised X]
6. **Instruments.** Which instruments make the form workable? For each: which purpose it serves, who performs it, and who pays. Where one performer plays two operator roles, is the conflict disclosed, and is the fee logic? [P] P separates five operator roles and allows combining them only with disclosed conflicts and fee logic. The digest names them without defining them, and this lens does not reproduce the names: use the question only to check that roles are not silently combined [?].
7. **Conditions.** Which rules must hold: law, programme rules, contracts, tax conditions? For each: source, addressee, date, supervisor, and the consequence of breach. Is it in force, deferred, or only proposed? [P: the legal register; in-force, deferred and proposed rules are kept apart]
8. **Result.** What would be seen, by whom and by when, so that the group could say the goal was met? P suggests reading results at one, three and five years [P]; the group chooses its own timing. Its success criteria are proposals, not official indicators [P].
9. **Chain check** [X]. Read the chain forward. Is any link empty: a goal with no beneficiary, a subject with no receiving position, a form with no one acting, an instrument with no performer, a condition with no source, a result nobody will observe?

## Output slots

Every element carries `lens: design-chain`, `voice: ai`, `epistemic: hypothesis` unless a registered source supports it (then `cites`). `seen_from` is the position the design is drawn from. All are proposals until the human decides.

| Answer | Kind | Board | Fields and links |
|---|---|---|---|
| Q1 goal | `goal` | `od` | `seen_from` the position whose goal it is |
| Q1 unacceptable loss | `note` | `od` | label "unacceptable loss: ..." |
| Q2 class | no new element | | relabel or move the misfiled item; say the class in the reply |
| Q3 beneficiary | `position` or `place_for_others` | `od` | a `position` only if the human works from it or an AI position is agreed |
| Q3 conflict of goals | none | | `opposes` relation between the two `goal` elements. A `problem` thesis only if the group itself states two justified, opposite claims |
| Q4 a subject | `other` | `oo` | label "subject: (a) formal right of ...", (b), (c) or (d); `flow` from giving position to it, and from it to receiving position |
| Q4 a subject that nobody carries after the pass | `gap` | `od` | `of: function`: the function of carrying it is missing [X] |
| Q5 form | `concept` | `oo` | label "form: ..." |
| Q6 an instrument | `function` | `oo` | `performed_by` its performer (a position or a place for others); `seen_from` the position the design is drawn from; payer and receiver as `flow` relations, as in `functional-plan` section 3 |
| Q6 a missing performer | `gap` | `od` | `of: position` |
| Q6 operator roles combined | `note` | `oo` | label "combined roles: ...; conflict disclosed: yes or no" |
| Q7 a condition | `standard` | `oo` | label begins "in force", "deferred" or "proposed"; `cites` the source, else `epistemic: unverified` |
| Q8 the result | H record | | `assumes` (the chain works), `action`, `observe` (the result and its timing), `revise_if`, `targets` the goal. No result is written until the field gives one |
| Q9 an empty link | `gap` | `od` or `oo` | `of`: `position` for beneficiary, receiver or actor; `function` for instrument; `method` for the way of passing; `product` for a result nobody receives [X] |

A requirement's five register fields (source, addressee, date, supervisor, breach) go in the reply as a table. The record holds one `standard` per requirement, with the source in `cites`.

## Limits

- Report P was prepared by a model run and names no author in its text. The digest says nearly every statement in it links to a primary source and assessed the evidence quality; the links were not re-checked here. Whether the report's owners accept its being cited as a source in a committed lens file is open.
- P says its classification is an analytic construct, not an official standard, and that its success criteria are proposals. It cannot rank jurisdictions, and it notes missing deal, survival and budget data [P].
- The order of the chain and the one, three and five year readings are P's recommendations. The digest shows no argument that the chain is complete or that the order matters [?].
- P covers the law and programmes of several countries. Whether a given rule applies to a given case is unchecked: the lens asks for the source and the status, it does not supply them.
- The generic reading of the subject (a) to (d), and of "goal", "form" and "method", is this lens's [X]. P writes for organised transfer of an enterprise. Not reproduced here: P's tables of purposes and of functions that transfer technologies must cover, its country sections and its correction register. A lens for a transfer in one jurisdiction would cite those directly.
- P is not an SMD text. `route: smd` means only that the engine uses it on SMD boards. Its split of purpose, method and instrument is a classification, not a scheme in the classic sense (product, material, means, method).
- The data model has no kind for "what passes", so subjects use `other`. This is reported as a possible format addition, not met with a new field.

## Example (invented bakeries case)

A shared plant takes over the dough ordering that each bakery did by phone. A proposal for questions 1, 4, 6 and 7:

```yaml
- {id: g-order, board: od, kind: goal, label: "dough ordering keeps working when the bakeries stop ordering by phone",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: design-chain}
- {id: sub-auth, board: oo, kind: other, label: "subject: (b) authority to place orders with the mill",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: design-chain}
- {id: sub-know, board: oo, kind: other, label: "subject: (c) which bakeries need an early delivery",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: design-chain}
- {id: gap-know, board: od, kind: gap, of: function, label: "who carries the knowledge of early deliveries after the pass?",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: design-chain}
- {id: fn-order, board: oo, kind: function, label: "order consolidation service for members",
   seen_from: p-organiser, performed_by: p-plant, voice: ai, epistemic: hypothesis, lens: design-chain}
- {id: std-min, board: oo, kind: standard, label: "in force: the mill's minimum order size",
   seen_from: p-organiser, voice: ai, epistemic: unverified, lens: design-chain}
relations:
  - {from: p-bakery, to: sub-auth, kind: flow, label: "gives"}
  - {from: sub-auth, to: p-plant, kind: flow, label: "receives"}
```

Question 2 would flag a first answer of "a shared ordering app" as an instrument, not a goal. Question 8 then becomes an H record, for example `observe: orders placed late per month, read after one, three and six months`.
