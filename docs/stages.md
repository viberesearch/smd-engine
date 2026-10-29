# Build steps and where each method enters

Plan approved 2026-10-25 (`docs/plan.md`). Each step is a branch and a PR.

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
| docs | Architecture section, command tables and this file (update plan step 10) | done in the step after v0.3.6 |
| 11 | Open release preparation (update plan step 11) | done in v0.3.6: licence, public READMEs, `README_ru.md`, `cases/example_ru/`, release workflow |

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
