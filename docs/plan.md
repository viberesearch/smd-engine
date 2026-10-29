# Build plan

Approved 2026-10-25. This is the engine part of the plan; `docs/stages.md` tracks the status of each step and where each method enters. Case-specific parts (a pilot case's clean-room whitelist, its team's rule on raw sources, its calendar) live with the case, not here.

Decisions:
- a generic engine with English originals, in this repository;
- each real case, with its Russian outputs, in the repository of its object of thinking, under that repository's rules;
- boards as YAML records plus rendered SVG and HTML;
- four modes, built step by step: solo with AI positions, ingestion of group sessions, clean room, portable prompts for teammates using other models.

## Architecture

```
smd-engine/
  src/smd_engine/  schemas (JSON Schema, one file per record type), validate (check registry), render (svg|html|md|mermaid|frames|graph|vault|index), compare, revise, apply, migrate, eval, cli   (Python 3.14, uv)
  profiles/        board layouts and kind tables as data: program-three-boards (default), classic-two-boards
  procedures/      one Markdown file per procedure, YAML front matter; model-agnostic prompts; `profile:` names the layout a procedure assumes
  lenses/          one file per lens: when to use, questions, output slots, source
  roles/           игротехник, методолог, визионер, actor positions
  .claude/         commands and subagents that run procedures
  cases/           invented examples only, with their patches and golden runs; real cases live in their own repositories
  docs/            README, method notes, data model
```

Records are the single source. Drawings and digests are generated, never edited by hand.

## Data model additions over the team's `smd/` v0.1

Implemented items are documented in `docs/data-model.md`.

1. Board set: three boards (`od`, `oo`, `s` with `small` and `big` halves). Elements carry `board`. Kinds from the program's slides are added: `entry`, `position`, `place_for_others`, `frame` (`old`/`new`), `function_chain`, `gap`, `model`, `garland`, `normality_boundary`.
2. Position attribution: each element names the position it is seen from, following the organisers' criterion that nothing lies on the boards without a position. This also records the per-position subjects of one object (the cow example).
3. Transitions: numbered, `from_board`/`to_board`, element anchors, the source time.
4. Qualifications: `K` items with target element, text, author position, status (`open`/`partly`/`closed`), and the cycles in which they were raised and closed.
5. Cycles: `cycle` n with a `revises` link; a state line per cycle (version; accepted; open; next move).
6. Theses: SessionFlow card fields, voice and status from its six labels, source address (atom plus time).
7. Hypotheses: the inter-module form (what we test, what we do, what we get, confirmed or not, what it changes), with links to K items and field artefacts.
8. Ontology record: objects, per-position subjects, the ontological object, the "what competes with what" claim (Khaprov), each marked tested or untested.
9. Source provenance: kind (`photo`, `transcript`, `typed`, `ai_generated`) and a `lineage` tag, e.g. material derived from a team's earlier concept. The clean room filters on it.
10. Profile: a record names the profile its boards and kinds come from (`profile`, default `program-three-boards`). Boards, kinds, home boards, containers, roles, shapes, labels and the hint set are data in `profiles/<id>.yaml`, read by the validator, the renderers, compare and the exports.
11. Case taxonomies: a case declares named value lists (for a pilot case, the six OST tiers) in its own file; elements, theses, hypotheses and ontology records may carry `tags`, and a `detail` table may bind a column to a taxonomy. The validator checks the values; the engine never ships a case's list.
12. Patch record (`board_patch`): the owner's or the group's decisions as data (add, set, remove, state, sources), applied by `smd apply`. Patches are committed beside the board in the case repository, so a board is reproducible from its predecessor and its patches.
13. Run stamp (`run`: procedure, version, model, date), `route` (smd or triz) on elements and theses, `scheme` (the named scheme a gap or problem belongs to), `applied` (patch ids). Element `voice` takes the thesis vocabulary.

Compatibility: schema v0.3 is a clean break from v0.2. The validator accepts only the current schema version; an older record is reported as one error that names `smd migrate`, which rewrites a v0.2 record to v0.3 once. A case repository pins the engine by tag (`uvx --from git+https://github.com/viberesearch/smd-engine@vX.Y.Z smd`) and validates its board files in CI.

## Steps

Each step is a branch and a PR in this repository. Each change to a case repository is a separate PR there, with the file list shown to the owner first.

**Step 0. Sources.**
- 0a: method digest from external verified sources, with citations, in `docs/method/`. The program's materials stay one application of the method, not its definition.
- 0b: case sources. Each case has one manifest; raw files stay where they are.

**Step 1. Records, validator, renderer.**
- Schemas v0.2 (released in v0.1.0; schema v0.2 is not release v0.2.x: the schema stayed v0.2 until v0.2.4).
- Validator: structural checks plus semantic levels (dangling references, element without a position, frame without a chain, K pointing at nothing, transitions out of order).
- SVG/HTML renderer in the program's three-board layout, with automatic placement inside board regions and optional manual geometry.
- Done when: `uv run pytest` passes, black and flake8 are clean, and two golden screens render.

**Step 2. Ingestion procedures (group sessions).**
- Transcript to theses (SessionFlow mechanism), then theses to board updates and a state line.
- Field artefact to hypothesis result.
- Done when: a real plenary transcript (a pilot case, in its repository) produces the record behind the group's screen, each element citing its source time.

**Step 3. Thinking procedures (solo with AI positions).**
- Small situation by the four questions.
- Visionary tract: normality boundary, spill-outs, garland, model, bridge, view of oneself, goals. The structural moves (alpha, rho, tau, gamma) generate candidates, the validator gates them, and the human selects.
- Positional construction; functional plan; qualification pass by the методолог role against the program's criteria and typical errors; reflexive protocol.
- AI voices carry the status "Вариант формулировки от ИИ" until accepted.
- Done when: one solo session on a case's open qualifications runs end to end and yields its next cycle.

**Step 4. Lens library.**
- Khaprov: 7 levels x 3 complexity kinds, 3 scales, ontology test, managing not-knowing.
- Schukin: 5 boundary grounds, 4 change families, capability probes, interface tax, metrics.
- Fliamer's diamond: functions, products, consumption, new technical solutions.
- The transfer design chain: goal, beneficiary, subject of transfer, form, technologies, conditions, result.
- TRIZ contradictions; SCAMPER as a cross-check of the four moves.
- A selection table decides which lens a procedure offers at which step.

**Step 5. Clean-room run and comparison.**
- A fresh subagent with an input whitelist develops an industry through the full tract. It never reads inputs whose lineage the case manifest denies.
- `compare.py` diffs two board sets element by element: positions, frames, functions, institutions, lenses covered, open K. It then proposes a merge as a separate cycle.

**Step 6. Portability and Russian outputs.**
- Prompts run without Claude Code: any model, with the files attached.
- Exports: SessionFlow formats ("Наша малая ситуация. Материал к сообщению", the module start message), Russian versions into the case repository by PR, journal entries.

**Step 7. Decisions as records.** `board_patch` and `smd apply`; `smd publish` (validate, frames, index, graph in one run); `smd sources refresh` for growing decision logs. Done when: a pilot case's board of one sub-version is reproduced byte for byte from its predecessor and the committed patch. Released as v0.2.2 (`sources --refresh`), v0.2.3 (`publish`), v0.3.1 (`apply`) and v0.3.4 (transitions by `n`, `board_notes`).

**Step 8. Schema v0.3, migration, profiles.** Versioned schema files, `smd migrate`, the fields of item 13, taxonomies and tags, the profile mechanism with `classic-two-boards` as the second profile. Done when: every v0.2 record in `cases/` and in the pilot case's repository migrates and validates with zero errors, and the two-board fixture validates with no hint about a situation board. Released as v0.3.0 (schema v0.3, `smd migrate`, taxonomies, tags), v0.3.2 (profiles) and v0.3.5 (regions, graph colours).

**Step 9. Quality across models.** Run stamp, `smd eval` on top of `compare`, a public golden run (invented bakeries transcript) and a private one in the case repository. Done when: `smd eval` on the stored plenary run reproduces the 25.10 counts. Released as v0.3.3.

**Step 10. Code structure.** Check registry in `validate/`, static assets out of `render/graph.py` and `render/frames.py`. No behaviour change: the test suite passes unchanged plus the registry test. Released as v0.2.4. Later releases: v0.3.6 (open release), v0.3.7 (docs), v0.3.8, v0.4.0 and v0.5.0 (see `docs/stages.md`).

## Not in scope (report only)

- An interactive web editor for boards; YAML plus the renderer come first.
- Changes to a case repository's rules beyond what the case needs.
- Data from real client deals. Real cases use anonymised material only.
- Research pipelines on the Claude API (they stay in the working folder; their results enter a board as a patch).
- The content of any case taxonomy.
