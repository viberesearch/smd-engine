---
id: fliamer-diamond
title: "Diamond of the big situation (functions, products, consumption, new technical solutions)"
version: 0.1.1
source: "Fliamer, module-1 workspace slides 3-6 (slide 6 diagram and the big-situation prompt it names; slides 3-5 for the field of division of labour and its technologization); SessionFlow frame 03 for the takt scope"
route: smd
offered_by: [visionary-tract, functional-plan]
---

# Fliamer's diamond of the big situation

A lens for laying out a wider system of activity: which complexes of activity make it up, what functions they carry, what they produce, who consumes it, and which technical solutions change them. The source is a deck of six slides and a prompt it names. This file reads the deck as a local digest of the slides describes it (the digest is not in the repo), and keeps the digest's uncertainty marks.

Marks used below:
- **[S]** stated in the slides, as read in the digest;
- **[R]** on a reconstructed slide. Slides 2 and 5 are redrawn from slide 1 and some labels are uncertain; the digest says to check them against slide 1;
- **[X]** this lens's own extrapolation, to confirm with the organisers;
- **[?]** open in the source.

## What the source gives

- Slide 6 names a second prompt, "analysis of the big situation" (v6, not seen by the digest). Input: the formulation of the group's field of work, plus materials of group discussions, reports and answers to questions. Output: foci (очаги) described as complexes of activities and the functions they carry, and how activities change through (А) new functions, products and consumer categories, (Б) new technology that cheapens delivery of a function, (В) new technology that customises products, (Г) institutional norms, technologies and organisational structures that become demanded [S].
- The slide's diagram is a diamond with four vertices: functions in the chain, products, consumption and consumers, new technological solutions [S]. The digest lists the vertices only. It does not describe edges, order or direction [?].
- Slide 3 sets the field: a "new industry" is an area of the division of labour (РТ) subjected to mechanisation or automation (технологизация), thought of systemically by analysts. A group's theme is expected to turn out plural: "not a complex but complexes" [S]. "РТ" is never expanded; reading it as "разделение труда" (division of labour) is the digest's inference [?].
- Slide 4 shows a sample output in card form, one card per complex: an integrator, four numbered links of the division of labour, notable participants, a result, numbered source codes with footnotes, and a line on what the difference between complexes means. Its point: a shared technology base is not one industrial chain, because customer, functions, infrastructure and accepted result differ [S]. That the cards show the expected output of the slide 6 prompt is the digest's reading ("evidently") [?].
- Slide 5 gives three movements: set the whole area as a complex of activities; cut out a place in the object for oneself; read the situation and what it demands, which feeds the revising of one's intent. Beside the second movement: two computations that set "what is in the object", one from the situation and one from raising the efficiency of resource use [R]. The digest does not say how either is done [?].

## When to use

- The group has a theme or a field and wants its big situation laid out before choosing a place in it. In the engine: `visionary-tract` step 1 (the system of activity to which the normality applies: questions 1 and 2) and step 4 (the bridge: question 6, the change channels); `functional-plan` section 2 (the chain: questions 3 to 5) and section 5 (material on how the same chain is arranged elsewhere). Which steps get the lens is the engine's choice **[X]**; the slides tie the diamond to the big situation, not to named procedure steps.
- Not on first-takt material. SessionFlow frame 03 scopes the first takt to the small situation, and the big situation belongs to the second takt (digest, frame 03 and Fliamer). If the only material is a small-situation message, keep the big-situation items as questions for the next takt.
- Not to describe the group's own practice: that is `small-situation`.
- Expect more than one complex. A result with a single complex is a finding that needs a reason, not the default [S, slide 3].
- Without registered material on the field, every answer is an AI hypothesis. Say so at the start.

## Questions

1. **Field.** What area of the division of labour does the theme point to, in the group's words, and which part of it is being mechanised or automated? [S]
2. **Complexes.** Is it one complex or several? For each: what is it called, who integrates it, who are the notable participants, what is its accepted result? [S]
3. **Functions in the chain.** For each complex, which links of the division of labour does it contain, in order? Who performs each, and what passes to the next? The sample cards show four links; that number is not a rule [S, X].
4. **Products.** What does each link deliver, and what does the whole chain deliver? Which product of one link is the material of the next? [S for the vertex; the chain reading follows `functional-plan` and GP1975, X]
5. **Consumption and consumers.** Who consumes each product, for what, and in which categories? Which category is new? [S]
6. **New technical solutions.** Which technologies are present or arriving? For each, through which channel does it change the complex: new functions, products or consumer categories (А); cheaper delivery of an existing function (Б); customised products (В); demanded norms, technologies or organisational structures (Г)? [S]
7. **Difference between complexes.** If there is more than one: what differs, customer, functions, infrastructure or accepted result? Is a shared technology base being read as one chain? In one sentence, what does the difference mean for someone who wants a place in the field? [S]
8. **Empty places.** Where in a chain does no one perform, no one pay, or no one consume? [X; the check is `functional-plan` section 4. Choosing a place for oneself is not asked here: it belongs to `visionary-tract` step 5.]
9. **Two computations** (optional). What is "in the object" if counted from the situation, and what if counted from raising the efficiency of resource use? [R, ?] Record the answer as given; the digest gives no method.

## Output slots

Every element carries `lens: fliamer-diamond`, `voice: ai` and `epistemic: hypothesis`, unless a registered source supports it: then `cites` is set and `epistemic` follows the source. `seen_from` is the position the view is drawn from (`visionary-tract` section 0, owner of the vision). All elements are proposals until the human decides.

| Answer | Kind | Board / half | Fields and links |
|---|---|---|---|
| Q1 the field | `situation` | `s`, big | label "field: ..." |
| Q2 a complex | `situation` | `s`, big | label "complex: ..." |
| Q2 integrator, participants | `place_for_others` | `od` | one per actor; a `position` only if the human works from it |
| Q2 accepted result | `fact` | `s`, big | label "result: ..."; `cites` required, else `epistemic: unverified` |
| Q3 frame of a complex (if none in the record) | `frame` | `oo` | `frame_state: old`: the complex exists in the world; the group's own new frame is not touched |
| Q3 a link of the chain | `function` | `oo` | `in` the complex's frame; `flow` to the next function, labelled with what passes; `performed_by` its performer, a `place_for_others` for an outside actor; `seen_from` stays the viewing position |
| Q4 a product | `other` | `oo` | label "product: ..."; `produces` from its function |
| Q5 consumer category | `place_for_others` | `od` | label says "new" for a new category; `flow` from the product |
| Q5 consumption | `fact` | `s`, big | label "consumption: ..." |
| Q6 a technical solution | `concept` | `oo` | label "technical solution: ..." |
| Q6 a demanded norm | `standard` | `oo` | `cites` or `epistemic: unverified` |
| Q6 a demanded organisational structure | `note` | `s`, big | label "demanded structure: ..." |
| Q6 a change channel | `situation` | `s`, big | label "change А|Б|В|Г: ..."; `refers` to the complex and to the technical solution |
| Q7 difference, its meaning | `note` | `s`, big | labels "difference: ...", "meaning of the difference: ..." |
| Q8 an empty place | `gap` | `od` or `oo` | `of` as in `functional-plan` section 4: `position`, `function`, `material`, `means`, `method` or `product` |
| Q9 the two computations | `note` | `oo` | label "in the object from the situation: ..." or "... from resource efficiency: ..." |

Rules:
- No named participant, company or figure without a registered source. Where the source does not name one, write "not named". The sample cards name actors; an AI filling such a card from memory invents them (frame 03: no invented counterparties).
- Complexes are not merged. Two complexes with different customers or results stay two elements (Q7).
- A thesis from a session that answers these questions may carry `lens: fliamer-diamond` too.
- Hypotheses about links nobody has checked are written as H records, as in `functional-plan` section 7. Each H carries `lens: fliamer-diamond`.

## Limits

- The diamond is given as four vertices. Whether it is asked clockwise, as a cycle, or in any order is not described; the order of questions 3 to 6 is this lens's [X].
- The prompt v6 was not seen. This lens follows the description on slide 6, not the prompt text, and is not a copy of it.
- The two computations on slide 5, and the unlabelled figure with "?" on the same slide, are unexplained [R, ?].
- The slides give no cadence, roles, tests or criteria: no rule for when complexes are one or two, none for ranking them, none for what counts as a "new" function.
- Slide 4 is a sample of the expected output, not an output of the prompt [?]. Its example complexes are not reproduced here.
- The source links the diamond to the revising of intent (slide 5) but not to the four structural moves. Any `move` on these elements would be the engine's reading, not Fliamer's.
- The data model has no `product` kind, so products use `other`. This is reported as a possible format addition, not met with a new field. A function's outside performer is carried by `performed_by`, which the format now has; the lens does not use `belongs` for it.
- The lens gives structure. Facts about real complexes need sources. The sample cards on slide 4 cite numbered sources with footnotes; the lens supplies none.

## Example (invented bakeries case)

Question 2 to 5 on one complex, as an AI proposal:

```yaml
- {id: cx-central, board: s, half: big, kind: situation, label: "complex: central production for chains",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: fliamer-diamond}
- {id: f-central, board: oo, kind: frame, frame_state: old, label: "central production for chains",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: fliamer-diamond}
- {id: place-central, board: od, kind: place_for_others, label: "central plants of the chains",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: fliamer-diamond}
- {id: fn-c-bake, board: oo, kind: function, label: "baking at scale", in: [f-central],
   seen_from: p-organiser, performed_by: place-central, voice: ai, epistemic: hypothesis, lens: fliamer-diamond}
- {id: fn-c-ship, board: oo, kind: function, label: "night delivery to chain stores", in: [f-central],
   seen_from: p-organiser, performed_by: place-central, voice: ai, epistemic: hypothesis, lens: fliamer-diamond}
- {id: pr-c-bread, board: oo, kind: other, label: "product: par-baked bread",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: fliamer-diamond}
- {id: place-chain, board: od, kind: place_for_others, label: "chain store buyer",
   seen_from: p-organiser, voice: ai, epistemic: hypothesis, lens: fliamer-diamond}
relations:
  - {from: fn-c-bake, to: fn-c-ship, kind: flow, label: "baked bread"}
  - {from: fn-c-bake, to: pr-c-bread, kind: produces}
  - {from: pr-c-bread, to: place-chain, kind: flow, label: "delivered fresh"}
```

Question 6 then asks, for example, whether a new oven type cheapens baking per loaf (channel Б) or lets the chain order bread to its own recipe (channel В). The answer becomes a `concept` and a `situation` labelled "change Б: ...". It stays a hypothesis until a source is registered.
