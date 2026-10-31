# Build steps and where each method enters

Plan approved 2026-10-25 (`docs/plan.md`). Each step is a branch and a PR. The steps of the 2026-10-29 update were released as v0.2.1 to v0.3.x; a release tag is not a schema version (schema v0.2 ran from v0.1.0 to v0.2.4, schema v0.3 starts at v0.3.0).

| Step | Content | Status |
|---|---|---|
| 0a | Method digest from external primary sources: Shchedrovitsky (thought-activity scheme, activity act, reflexive exit, ОДИ), Altshuller (TRIZ, ARIZ), systems approach; to `docs/method/` | done |
| 0b | Case sources: one manifest per case, raw files stay where they are | done for the pilot case |
| 1 | Records, validator, renderer (this repository, schema v0.2) | done in v0.1.0 (PR #1) |
| 2 | Ingestion: transcript to theses (voice, status) to board updates and a state line; field artefacts to hypothesis results | done in v0.2.0. Blind run on a pilot case's plenary transcript (25.10): the record behind the group's screen was rebuilt from the transcript, every new element citing its time; four content items missed |
| 3 | Thinking procedures, solo with AI positions: small situation by four questions, visionary tract, positional construction, functional plan, qualification pass, reflexive protocol | done in v0.2.0 for procedures, roles and records. Solo-session run on the case's K2-K4 (25.10) in proposal mode: cycle 3 drafted, 0 errors; the cycle is closed only by the owner's gate decisions and sign-offs |
| 4 | Lens library: Khaprov, Schukin, Fliamer's diamond, the transfer design chain, TRIZ | done in v0.2.0: `lenses/`, with the selection table in `lenses/README.md` |
| 4b | Patches: transitions addressed by number, and `board_notes` (update plan step 4b) | done in v0.3.4: `smd apply` sets and removes a transition by its number `n`; the patch field `board_notes` appends notes to the board |
| 5 | Clean-room run and element-by-element comparison and merge | `smd compare` done in v0.2.0. Clean-room run (25.10): two cycles from whitelisted sources, independent qualification, comparison with the group's screen; the ontology covered one position's exit only (universality test failed) |
| 6 | Portability (any model, files attached) and exports (SessionFlow formats, Russian versions into case repositories) | `smd pack` and `--format sessionflow` done in v0.2.0; the method files ship in the wheel. Open: the module start message format, the pinned validator moved to step 7 (team CI) |
| 6b | Profiles laid out by regions (update plan step 6b) | done in v0.3.5: each board stands in its `region`; see `docs/profiles.md` |
| 7 | Decisions as records: `smd apply`, `smd publish`, `smd sources refresh`; a tier taxonomy and a cycle patch of the pilot case (update plan step 7) | done: `sources --refresh` in v0.2.2, `publish` in v0.2.3, `apply` in v0.3.1. The pilot case's tier taxonomy and cycle patch are in its repository |
| 8 | Schema v0.3, `smd migrate`, profiles, taxonomies and tags | done: schema v0.3, `smd migrate`, taxonomies and tags in v0.3.0 (PR #21); profiles in v0.3.2: `program-three-boards` (default) and `classic-two-boards`, fixture `cases/example/two-boards-c1.board.yaml` |
| 9 | Run stamp, `smd eval`, golden runs (update plan step 9) | done in v0.3.3: `smd eval`, the `run` stamp on records, `cases/example/golden/` |
| 10 | Code structure: check registry, render assets | done in v0.2.4: the validator is a package with a check registry; the frames and graph assets are package files |
| docs | Architecture section, command tables and this file (update plan step 10) | done in v0.3.7 |
| 11 | Open release preparation (update plan step 11) | done in v0.3.6: licence, public READMEs, `README_ru.md`, `cases/example_ru/`, release workflow |
| Ш8-Ш12 | Gates Ш8-Ш12 (G.P.'s «Программа действий» against т. 5): element fields, hints, the three-positions lens | done in v0.3.8 |
| Ш13 | G.P.'s management scheme as the profile `management-four-boards` | done in v0.4.0 |
| boards | Record boards from profile templates; process boards on their own boards in the management profile | done in v0.5.0 |
| Х1 | Space-time continuum of an ontology (Khaprov, podcast on ontology, 28.10.2026): ontology fields `lives_in`, `tempos`, `horizon`, `covers`, element field `pace`, the hint `ontology-outlives-pace`, the lens `khaprov-ontology` 0.2.0 | done in v0.5.3 |
| Бир3 | Beer layer of the management profile (Beer, «Мозг фирмы»): `vsm_system`, `algedonic_channel`, `escalates`, `filters`, three hints, the lens `beer-viable-system`, the example `pekarnya-holding-c1` | done in v0.5.4 |
| Г2 | Model of the whole (Beer, Гл. 13): field `of_whole` on `model` in the management profile, held through `uses`; hints `no-model-of-whole` and `model-of-whole-one-filler`; the lens `beer-viable-system` 0.2.0 | done in v0.5.6 |
| Г3 | `seen_from` accepts a reflexive position as well as a position | done in v0.5.6 |
| Г5а | `reflected_from` accepts a reflexive position as well as a position | done in v0.5.7 |
| Г5б | A written-down model of the whole: field `written` on kinds flagged `of_whole`; `model-of-whole-one-filler` passes such a model by; the lens `beer-viable-system` 0.3.0 | done in v0.5.7 |
| Г5в | Russian on the pages: the digest's own words, move names by language, singular kind labels `label_one` in the profiles | done in v0.5.7 |
| Г6 | Russian words for the fixed values on the Russian pages: relation kinds, epistemic, move and record status, frame state, a thesis's voice, belt and kind, sign-off functions; board labels in the page's element table | done in v0.5.7 |
| Г7а | Words for the status, voice and epistemic status in the graph's details panel; the graph keeps the ids in its data | done in v0.5.8 |
| Г7б | Board labels and halves in the SVG legend's transitions; template labels in the index's record-boards table | done in v0.5.8 |
| Г7в | «заявлено» and «проверено» confirmed; no change | done in v0.5.8 |
| Г7г | A written model of the whole still needs a keeper for `no-model-of-whole`: docs and the lens `beer-viable-system` 0.3.1 | done in v0.5.8 |
| Г7д | A profile label with an empty `ru` or `en` is a profile error | done in v0.5.8 |
| Г8а | English words for the statuses in the graph's details panel, as on the page and the index | done in v0.5.9 |
| Г8б | An optional short board name `short` in the profiles, used in the SVG legend's transitions, on the graph's planes and in the frames' element details | done in v0.5.9 |
| Г8в | A transition's label after a dash in the SVG legend, not in brackets; the management profile's upper board renamed «Верхняя система ОРУ» | done in v0.5.9 |
| Г8г | The index's record-boards table names a board by its own label, beside the template | done in v0.5.9 |
| Ф1 | Run stamp v2: `pack_sha256`, `inputs`, `temperature`, `sample`; `smd pack` prints its hash; `smd revise` drops the stamp | done in v0.6.0 |
| Ф2, Ф3 | Graph signatures and procedure self-checks in the validator (functional plan, E2-E14, garland, bridge, `via`, cooperation, translation loss); acyclicity errors; every hint names its procedure; `board-dense` | done in v0.6.0 |
| Ф4 | `smd agree`: Krippendorff's alpha on the labels of N runs, coverage of cited addresses | done in v0.6.0 |
| Ф5, У | `smd new`, `smd status`, `smd next`; hypothesis leverage order (a proposal); `docs/first-board.md`, `docs/glossary.md` | done in v0.6.0 |
| М1, Ф6 | Hypothesis `type` (core, product, claim, estimate, probe, design), `rule` and `observed`; the Wilson interval proposes a verdict; six hints | done in v0.6.0 |
| 0.6.0 follow-ups | Example plans drawn; `carries` on `flow` and chain receivers; `smd next` from hint pointers; SessionFlow shows hypothesis fields | done in v0.6.1 |
| ИИ1 | `ai: assists / performs` on roles and functions; `red_line`; hint `ai-decision-unanswered`; AI share line in `smd status` and the index | done in v0.6.1 |
| КЛ1 | Structured red line `line` (corridor or yes/no, `since`/`until`, recovery) and `observed`; breach rule; hints for breach, expiry, pace; `docs/red-lines.md` | done in v0.6.1 |
| ОТП1 | Lettered part ids for split hypotheses (`H2a`, `H2b`) in the board and patch schemas | done in v0.6.2 |

## Structural moves (Invention as a Structural Operation)

Zharnikov D. (2026). *Invention as a Structural Operation: Why the Abductive Jump Is a Re-Coordinatization of the Space of Description, Not a Sensory Leap.* Working Paper v1.0.0, Zenodo. doi:10.5281/zenodo.21653102. Summary and limits: `docs/method/structural-moves.md`.

The paper claims invention is a change of representation made by four moves: adjoin, rescale, re-specify, glue. Candidates are chosen by a selection functional. Generation is mechanizable only where compatibility is decidable.

In the engine the moves generate and classify. They do not replace the SMD process (positions, reflection, qualification), and the group decides. Where they enter:

| Step | Use | Form |
|---|---|---|
| 1 | Every element can say which move produced it, from which elements, and with what status | `move` field; candidates listed as hints |
| 2 | Ingestion tags the moves a group made in its own talk. Example: a group's shift from the frame of a one-off deal to the frame of a continuing business adjoins a time axis (the life of the business) to a one-off deal | `move` with `status: accepted` when the group said it, `candidate` when it is the model's reading |
| 3 | Visionary tract, step "model from another reality": gamma. Choose a domain whose structure shares a substructure with the garland, and glue. Examples: medicine and healthy longevity; double entry, then national accounting standards, then professions | the AI visionary proposes 2-4 candidates per move; the validator rejects malformed ones before the group sees them |
| 3 | Bridge into the big situation: re-specify. Change which links are admissible, e.g. a sale as an operation inside the life of a business instead of its end | same |
| 3 | View of oneself: rescale. Object, ecosystem and market scales (Khaprov): one deal, a flow of deals, rules of the field | same |
| 3 | Goals and positional construction: adjoin. Add the axis the current picture holds fixed, such as time, the observer or the scale | same |
| 5 | Comparing the clean-room version with the earlier concept as two authors' module sets. Each shared element is classified as agreement, conflict, cross-refinement or cross-import (the negotiator in the paper's demo). Merge options are lock, fork, rebase, merge | `compare.py`: agreement, refinement, conflict, only in one set. Cross-import is not detected from wording alone; a qualification pass marks it |

Limits taken from the paper:
- The weights of the selection functional are untested. Any ranking of candidates is shown as a hint, with its weights logged.
- Completeness of the four moves is claimed only for formal domains. A board is not one, so the moves are a list of options, not a complete set.
- A move recorded with `status: candidate` by an AI voice stays a variant until the group accepts it (the SessionFlow status "Вариант формулировки от ИИ").

## Other methods by step

- Steps 2 and 3:
  - SessionFlow frame 03: thesis cards, six voice/status labels, the state line.
  - Girenko: three boards, visionary procedures, qualification criteria, reflexive protocol.
  - Fliamer: the field of division of labour, its technologization, and the diamond of the big situation.
- Step 4: Khaprov (7 levels x 3 kinds of complexity, 3 scales, ontology test) and Schukin (5 grounds of a work boundary, 4 kinds of change, capability probes, metrics).
- Step 0a: `docs/method/reconciliation.md` lists what the classic method (Shchedrovitsky, ОДИ, Altshuller) changes at each step:
  - belts and thesis kinds (difficulty, task, problem, question) in step 2;
  - problematization by a named scheme in step 3;
  - the roles of game technician and methodologist in step 3;
  - ontology records valid for a set of positions, with a realizability test, in step 3;
  - the solution route (SMD or TRIZ) in step 4.
- Step 8: the classic two boards [V GP-SMD; GP1987] become a profile; the situation board stays in the program profile.
