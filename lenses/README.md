# Lenses

A lens is a content model that a procedure offers at a given step. It says when to use it, which questions it asks, and which elements of a board-set record the answers fill. A lens adds no procedure of its own: the procedure runs, the lens is a set of questions it may put to the human, and the human decides whether to use it.

One Markdown file per lens, `lenses/<id>.md`. The checks are in `tests/test_lenses.py`.

## Front matter

| Key | Meaning |
|---|---|
| `id` | the file name without `.md`, lowercase-hyphen; the value of `lens:` on elements and theses |
| `title` | one line |
| `version` | semver; bump on any change of the questions or the output slots |
| `source` | who and where: lecture or slides, or the primary-text keys of `docs/method/sources.md` |
| `route` | `smd`, `triz` or `both`: the way of thinking the lens belongs to (`docs/method/reconciliation.md` section 8) |
| `offered_by` | procedure ids that offer the lens; must agree with the selection table below |

Sections of every lens, in this order or close to it:
- **When to use**, with the procedure sections where it is offered, and when not to use it;
- **Questions**, numbered, each answerable from a session;
- **Output slots**, a table: answer, then element kind, board and field. Only kinds and fields of `docs/data-model.md` are used. Every element and thesis carries `lens: <id>`;
- **Limits**: what the source does not say, and which claims are unverified.

Each lens marks which statements are the source's and which are the engine's own reading. The mark sets differ by lens (`[V]`, `[S]`, `[X]`, `[ANALYSIS]`, `[UNVERIFIED]`, "own extrapolation"); each file defines its marks near the top.

## How a procedure applies a lens

1. The procedure reaches the step in the table and offers the lens in one line, naming the questions. The human may decline.
2. The lens questions are asked in the procedure's role. Wording that the model writes is `voice: ai`, with `epistemic: hypothesis` unless a registered source supports it, as in `roles/README.md`.
3. The answers go to the slots of the lens and are tagged `lens: <id>`. `smd compare` reads the tag (`compare.py`).
4. Where a procedure writes no elements (`qualification-pass` writes only K) or restricts them (`small-situation` writes only the small half), the table says "questions only" or names the one allowed output. The lens then supplies the check behind a K, a label or a thesis, and the text names the lens id.
5. A lens never writes a sign-off, a status or a result. Moves it proposes are `candidate`.

Elements, theses, hypotheses and ontology records carry `lens: <id>`; `smd compare` lists the lenses each board set used. Qualifications and relations have no `lens` field.

## Lenses

| Lens | Route | Source | What it asks |
|---|---|---|---|
| `khaprov-levels` | smd | Khaprov, lecture | at which of seven levels of management complexity a problem is decided; the three kinds of complexity |
| `khaprov-ontology` | smd | Khaprov, lecture; GP1981 | three scales; the ontology test; managing not-knowing |
| `schukin-boundaries` | smd | Schukin, written talk | five grounds of a cut between functions; four families of change; capability probes |
| `schukin-interface-tax` | smd | Schukin, written talk | the function of each human touchpoint; achievement and balancing metrics; the engine's own sign-offs |
| `fliamer-diamond` | smd | Fliamer, module-1 slides | complexes of the big situation: functions, products, consumption, new technical solutions |
| `design-chain` | smd | team design study (local) | goal, beneficiary, subject, form, instruments, conditions, result of a pass between positions |
| `triz-contradictions` | triz | ARIZ-85V, Altshuller | a contradiction inside one object: zone, time, resources, ideal result, separation |
| `scamper-check` | smd | Eberle, Osborn; Zharnikov | a cross-check of the four structural moves after the tract |
| `three-positions` | smd | G.P., «Программа действий» (GP-Guide11); т. 5 | from where a scheme is drawn: inside, reflexive, external; which structures stay conditions |

## Selection table

Rows are procedure and step. "Q" is the question number in the lens file. Where a procedure or step is missing from the table, no lens is offered there.

| Procedure | Step | Lens | Questions | Why here |
|---|---|---|---|---|
| `small-situation` | 2 Where we are | `khaprov-ontology` | Q1 | The procedure allows the scale question when the human is unsure; the answer goes into the fragment label, no new element |
| `small-situation` | 7 Record, sign-offs | `schukin-interface-tax` | Q11 | Asks no sign-off that changes nothing |
| `visionary-tract` | 1 Boundary of normality | `fliamer-diamond` | Q1, Q2 | Names the system of activity as fields and complexes |
| `visionary-tract` | 4 Bridge (respecify) | `fliamer-diamond` | Q6 | The change channels (new functions, cheaper delivery, customised products, demanded norms) say which links change |
| `visionary-tract` | 5 View of oneself (rescale) | `khaprov-ontology` | Q1-Q4 | The three scales are the grain options of the move |
| `visionary-tract` | after 6, before the hand-over | `scamper-check` | all | Looks for candidates the four-move pass missed |
| `visionary-tract` | 10 Hand over | `schukin-interface-tax` | Q11 | As above |
| `positional-construction` | 2 Positional set | `khaprov-levels` | Q1-Q3, Q10 | Asks whether a position acts at the level its task needs, and whether the missing one is a gap or missing knowledge |
| `positional-construction` | 2 Positional set, 4 Representations | `three-positions` | Q1, Q2, Q5, Q6 | A position that draws the structure it works inside draws a condition, not an object (GP-Guide11 ¶36); `stance` on the positions |
| `positional-construction` | 3 The construction | `design-chain` | Q1-Q5, Q9 | The `flow` relations label what passes, from whom, to whom; the chain asks what stays behind |
| `positional-construction` | 5 One common object | `khaprov-ontology` | Q5-Q11 | The ontology record's `subjects`, `valid_for`, `competes`, `cooperation` and `test` |
| `functional-plan` | 2 Draft the chain, 5 Align | `fliamer-diamond` | Q3-Q5 | Functions in a chain, products, consumers; material on how the chain is arranged elsewhere |
| `functional-plan` | 3 Performs, pays, receives | `design-chain` | Q6, Q9 | Instruments with performer and payer; empty links of the chain |
| `functional-plan` | 4 Empty places | `khaprov-levels` | Q2, Q3 | A function with no performer: is the performer missing at a higher or lower level, or is knowledge missing |
| `functional-plan` | 6 Candidate moves | `schukin-boundaries` | Q1-Q8, Q14 optional | The four families and five grounds the procedure already names; grounds for `respecify` |
| `functional-plan` | 6, after the line above | `schukin-interface-tax` | Q1-Q10 | The human touchpoints that remain after a merge or shared state |
| `functional-plan` | 6 | `triz-contradictions` | Q0 first | Only when one function carries two opposed demands; Q0 sends a paradox between positions back to the SMD route |
| `functional-plan` | 7 Hypotheses | `schukin-boundaries` | Q9-Q13 | Capability probes are ready-made hypotheses `assumes`, `action`, `observe`, `revise_if` |
| `functional-plan` | 9 Hand over | `schukin-interface-tax` | Q11 | As above |
| `problematization` | 2 Sort what is on the table | `khaprov-ontology` | Q12-Q14 | A difficulty may be a wrongly posed problem; output is a thesis |
| `problematization` | 6 Pointer to the other route | `triz-contradictions` | all | The procedure flags a contradiction inside the object and writes no TRIZ terms; the lens is a separate pass |
| `qualification-pass` | 3.1 C7, 3.3 realizability | `khaprov-ontology` | Q1-Q4, Q9-Q11 | Questions only: the scale and the stated reason; the test and the cooperation. No elements |
| `qualification-pass` | 6 Hand over | `schukin-interface-tax` | Q11 | As above |
| `reflexive-protocol` | 2 The exit, fourth question | `three-positions` | all | The longer form of the fourth question: the reflexive and the external position, and the language of the next object scheme |
| `reflexive-protocol` | 6 Sign-offs | `schukin-interface-tax` | Q11 | As above |
| `theses-to-board` | 5 Sign-offs | `schukin-interface-tax` | Q11 | As above |
| `solo-session` | none of its own | all of the above | by step | It orders the step procedures and inherits their lenses; the human may call another lens at a gate |
| `ingest-transcript`, `field-result` | none | none | | They turn a record of talk or a field artefact into theses or a result, and a lens would put the model's questions into that reading |

The table is the engine's selection. The source materials do not say which lens belongs at which step. A procedure already names the source in these places: the scale test at tract step 5 and in `qualification-pass`, the four families and five grounds at functional-plan section 6, the ontology test at positional-construction section 5, the three positions at reflexive-protocol section 2, the sign-off rule everywhere.

## Rules for every lens

- Generic: no participants' names and no case facts. Examples use the invented bakeries case in `cases/example/`.
- Source material is kept outside the repository and never committed. A lens names the source and the section, and marks what it could not check.
- Plain English; Russian only for the source's terms, given once in brackets.
- Under 200 lines per file.
- A lens that needs a kind or field the format lacks reports it in Limits, and does not invent a field.
