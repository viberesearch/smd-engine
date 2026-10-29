# Changelog

Dates are those of the tag. All tags v0.2.1 to v0.3.5 were made on 2026-10-29. The version in `pyproject.toml` stayed at 0.2.0 through v0.2.4 and at 0.3.0 from v0.3.0 to v0.3.5; 0.3.6 is the first release whose package version equals its tag.

## 0.5.0 - 2026-10-29

The first public release since 0.3.7; it also carries 0.3.8 and 0.4.0, which were tagged in the private repository only.

- `compare.merge` remaps `performed_by` of imported functions like `assigned_by` (kept only when the target exists in the result and is a position or place for others); before, a dangling reference was possible.
- Record boards: a profile may declare a board template (`per_record: true`, with its label, colour, the kinds it takes and, optionally, the kinds its boards may `unfold`); a record declares any number of boards of it in `boards` (`id`, `template`, `label`, optional `seen_from`, `unfolds`, `cites`), and every part of the engine handles each as a board: validation (unknown template, taken, reserved (`records`, `sources`: the layers of `smd graph`) or duplicate id, a kind the template does not take, `unfolds` of a kind the template does not unfold), the screen (placed below the profile's boards, rows as wide as its widest row), frames (a reading step on a template is read once per record board, `<step>-<board>`; zoom cuts to it), the index (a table of record boards), `smd compare` (boards matched by id, with their element counts; a merge carries A's boards that B lacks), `smd graph` (a plane each), `smd vault` (a folder each, unique and never named by the template alone), `smd pack` (record boards listed as cells), `smd revise` (carried) and `smd apply` (`add.boards`, `set` and `remove` by id; a removed record board takes its elements with it). `boards` is optional: schema 0.3 stays, and records without it give the same output byte for byte.
- `management-four-boards`: the kind `process_board` (a framed area of `ot`) is replaced by the template `process`, so each working process is idealised on a board of its own (GP-T5 p. 245) and unfolds a `work_process`; `function` lives on it, and `representation-fit` no longer lists `process_board` among a manager's targets. The reading step `process` follows `upper`. The example `pekarni-oru-c1` has two process boards.
- `scripts/export_public.py` reads its arguments with argparse: `-h/--help` prints the usage and exits 0 (before, it exported into a folder named `--help`); an output folder inside the repository, or one that exists and is not empty, is refused with exit 2.

## 0.4.0 - 2026-10-29

- Gate Ш13 В amended by Ш15 В: G.P.'s scheme of organisation, leadership and management as the profile `management-four-boards`, read against GP-T5 lectures 4-6 (1988; the latest text wins, the earlier view stays as a comment in the profile file). Schema 0.3 stays.
  - Four boards on the `regions` screen: `od` and the upper system of ОРУ `ot` on top, the apparatus of leadership `ap` and the managed polysystem `us` below; `ot` and `us` flagged `object`. Kinds: knowledge (`knowledge_retro`, `knowledge_projective`) in place of a forecast, `ideal_state`, `programme`, `means`, `functional_place`, `process_board` (a working process idealised on its own board, drawn as a framed area of `ot`); `post`, `group`, `club`; `monosystem`, `mission`, `self_motion`, `trajectory`, `work_process` and the planes `functional_structure`, `link_structure`, `morphology`, `material`, and `fact`. Relations: `organises`, `leads`, `manages`, `subordinates`, `personal`, `captures` («захват»), `knows` (not «отражение»), `contends` (politics), `parasitic`, `symbiotic`, `mechanism_of`.
  - Hints of this scheme, in `validate/management.py`: `lead-vs-manage`, `manage-via-organizedness`, `manage-without-knowledge`, `leads-outside-organisation`, `representation-fit` (the fit table revised by GP-T5: the working process is the object of управление), `development-step` («шаг развития»), `polysystem`.
  - Profiles: a relation kind other than the engine's nine is written `{id, label: {ru, en}}`, and `smd graph` and `smd vault` name its links by the label; a hint may register the kinds and relation kinds it names, which a profile enabling it must define. Reading steps `upper`, `apparatus`, `managed`.
  - Example `cases/example_ru/pekarni-oru-c1.board.yaml`.
  - Fable review: an engine relation id with a label is refused; `leads-outside-organisation` names a leader and a led who hold the same place; the leader's fit is `post` only (GP-T5 pp. 224-225, 254).
- `docs/method/sources.md`: rows for the keys the new hints cite: GP1975a, GP-STS, IT1995, GP-Guide and its sections 4, 5, 8, 10, 11, GP-Guide2004, GP-T4, GP-T5.

## 0.3.8 - 2026-10-29

- `docs/method/sources.md`: the GP1983 row gives the Избранные труды key and explains the gtmarket page header; new row GP1983a for the single-author 1983 text; GP-Guide9 gets its edition (М.: Дело, 2003).
- Gates Ш8-Ш12, from G.P.'s «Программа действий» (GP-Guide11, 1981) read against т. 5 (GP-T5, 1988; the later text wins where they disagree). Schema 0.3 stays; every new field is optional and no hint fires on a record without the new fields, except `goal-without-breakdown`, `information-without-cell` and `cells-from-information`, which read existing fields.
  - Element fields: `stance` (`inside`, `reflexive`, `external`) on the kinds a profile flags `stance` (the positions); `acts_as` (`organiser`, `leader`, `manager`, `politician`, `functionary`) on positions; `goal_source` (`breakdown`, `assigned`, `own`), `arises_from` and `assigned_by` on goals; `modality` (`fact`, `ought`) on elements and theses; `nature` (`natural`, `artificial`, `both`) on object-board elements. Each off its kind or board is an error, as are a dangling or wrong-kind `arises_from` and an `assigned_by` that is not a position or place for others; a `reflected_from` position with `stance: inside` is a warning. `arises_from` takes gaps, kinds flagged `factual`, elements and theses with `modality: fact`, and `difficulty` or `problem` theses.
  - Profiles: kind flags `stance` and `factual` (`docs/profiles.md`); `goal` is a kind the engine names when a profile enables `goal-without-breakdown`.
  - Hints, enabled in both profiles: `object-from-inside`, `external-without-reflection`, `goal-without-breakdown`, `position-without-object`, `ought-without-fact` (natural processes first, GP-T5 p. 252, in place of the 1981 forecast), `design-the-natural`, `information-without-cell`, and across cycles `cells-from-information`.
  - Lens `three-positions`, offered by `reflexive-protocol` (section 2 gets a fourth question: from which external position, and in what language, the next object scheme is drawn) and `positional-construction` (records `stance` and `acts_as`). `ingest-transcript` 0.3.0: step 0.4 "Cells first". `qualification-pass` 0.4.0: a check row asks whether a representation fits the place the position has taken (Ш10 А), read with `position-without-object`.
  - `smd pack`: with board sets among the records, a "Cells to fill" part lists the latest cycle's elements of the kinds the profile flags `skeleton`. `smd apply` drops `arises_from` and `assigned_by` links to a removed item; a `smd compare` merge remaps them on imported elements, as it does `seen_from` and `in`. `smd revise` carries `stance` and the other new fields with the elements.

## 0.3.7 - 2026-10-29

Docs after the code (update plan step 10); no change to records, schema or commands.

- The maintainer notes list every module; `docs/stages.md` marks the steps of the update with their tags; `docs/plan.md` says one schema file per record type.
- `smd_engine.__version__` is read from the installed package instead of a constant that had stayed at 0.3.0.

## 0.3.6 - 2026-10-29

First release prepared for public readers; no change to records, schema or commands.

- `README.md`, `README_ru.md` (the program vocabulary marked as such), `CONTRIBUTING.md`, `docs/README.md` and `docs/commands.md` (the command examples that were in the README).
- `LICENSE`: MIT for the code; the method notes, procedures, roles, lenses, profiles and examples are CC BY 4.0, as the README states.
- `cases/example_ru/`: the bakeries case with Russian labels, two cycles and a manifest; invented content.
- `pyproject.toml`: classifiers, URLs, licence; the sdist leaves out four absolute symlinks of the owner's tooling (`.clinerules`, `.cursorrules`, `.cursorignore`, `.rooignore`), which made `uv build` fail.
- `.github/workflows/release.yml`: on a `v*` tag, builds the sdist and wheel and publishes to PyPI through a trusted publisher.
- Test that the wheel configuration carries `profiles/`, `procedures/`, `roles/` and `lenses/`.

## 0.3.5 - 2026-10-29

- Profiles laid out by regions (`docs/profiles.md`): each board stands in its `region`; boards whose regions overlap vertically form a row, and a row that overflows grows and pushes the rows below down. `screen: regions` (the default) draws any number of boards, halved or not, as rectangles around their regions; `screen: triangles` is the program's screen, and the program profile keeps its output. A halved board's halves meet at `split`. Meanings come from attributes, not ids: the shapes `frame` and `heading`, the kind flag `light_off`, the board flag `object`, `compare_skip`. The kinds the engine names (`position`, `place_for_others`, `function`, `cooperation`, `gap`, `note`; `entry` with its hint) are required. The parser refuses a profile with no boards, boards that overlap as drawn (regions 40 apart side by side, 60 one above the other), a triangles profile whose boards leave their parts of the screen, halves other than a list of distinct halves, a duplicate relation kind or hint, a hint the engine does not have, and an empty filter. `smd frames --by cycle`, `smd publish` and `smd compare` refuse records of two profiles (exit 2, naming both). `smd vault` and `smd graph` colour each board with its ink colour from the profile, as the screen does (the program's boards change colour in the graph and the vault).
- Sign-off labels in ru and en for every function of the schema (`render/text.py`); `smd render --format sessionflow` no longer fails on `partly_k` and `reopen_k`.
- `smd frames --zoom` follows the screen: its map draws the three triangles for `screen: triangles` and the regions' rectangles for `screen: regions`. The geometry the parser and the renderers share is `src/smd_engine/screen.py`.

## 0.3.4 - 2026-10-29

- `smd apply`: `set` and `remove` address a transition by its number, `{n, <field>: value}` and `{n, reason}` (later transitions are renumbered 1..n; a transition added by the same patch can be set). The patch field `board_notes` appends text to the board's notes, before the lines for removals, so a patched board is reproduced from the patch alone. The order is `add`, `set`, `board_notes`, `remove`, `sources`, `state`, `title`.

## 0.3.3 - 2026-10-29

- `smd eval <run> <expected>`: compares a procedure run with an expected record. It prints the five `compare` counts and the theses matched by their `cites` address (same source, time within 30 seconds), and exits 1 when `--min-agreement` or `--max-only-expected` is missed.
- `run: {procedure, version, model, date}` on the record; each procedure writes it at hand-over.
- `cases/example/golden/`: an invented transcript and the record the procedures should make from it.

## 0.3.2 - 2026-10-29

- Profiles: boards, element kinds, relation kinds, hints and reading steps are data in `profiles/`. A record names its profile in `profile`; `program-three-boards` is the default. `classic-two-boards` lays out the classic org-activity and object-ontological boards side by side, with no situation board. The validator, layout, SVG, frames, graph, vault, index, Markdown, Mermaid, compare and the SessionFlow export read the profile. `smd pack` refuses a procedure of another profile.
- Malformed profile files are reported as an error of every record that names them.
- Changed error wording for malformed three-board records. The schema no longer lists the allowed boards, kinds and relation kinds, so a wrong one is no longer a schema message such as `'zz' is not one of ['od', 'oo', 's']` at `elements/2/board`. It is now `unknown board 'zz' in profile 'program-three-boards'`, with the element id as the reference (`unknown kind '...'` likewise; for a relation, `unknown relation kind '...'` with `relation a->b` as the reference). A script that matches the old text needs the new one; the exit code is unchanged.

## 0.3.1 - 2026-10-29

- `smd apply <board> <patch> -o <out>`: a decision on the current cycle as a `board_patch` record (`add`, `set`, `remove`, `state`). The result is the next sub-version of the same cycle, validated with the manifest and taxonomy file when given; nothing is written on errors, a patch applies once, and removed items take their links with them.

## 0.3.0 - 2026-10-29

- Schema v0.3, a clean break from v0.2 (one schema file per record type, no dual-version validator). The validator reports a record of another version as one error, `schema 0.2: run smd migrate`. `smd migrate <paths> [--write]` rewrites v0.2 board sets and manifests once and reports what changes per file. New fields: `run`, `applied` and `profile` on the record; `route` (`smd` | `triz`) on elements and theses; `scheme` (the named scheme next to `of`) on gaps and problem theses; `tags` on elements, theses, hypotheses and ontology records; `detail.keys` binding a detail column to a taxonomy; `lines` on manifest sources. Element `voice` takes the thesis voices only; migration lowercases `AI` and maps other texts to `participant`, keeping them in `voice_note`. Ontology `aspects` is a free object. `smd migrate --write` edits only the changed lines, so comments and layout stay; it rewrites the whole file only when the edited text does not load as the migrated record, and says so. A taxonomy file (`record: taxonomies`) is checked by `smd validate --taxonomies` and `smd publish --taxonomies` and carried by `smd pack --taxonomies`. Procedures, roles, lenses and agents write `voice: ai` instead of `voice: AI` (patch version bump of each changed procedure and lens).

## 0.2.4 - 2026-10-29

- The validator is a package with a check registry: one module per subject, checks run in the order of `REGISTRY`, each method hint has a string id. Findings are unchanged.
- The CSS and JS of the frames and graph pages are package files.

## 0.2.3 - 2026-10-29

- `smd index`: every K, thesis, hypothesis, O, sign-off and element with its YAML line; a cited source links to its file when the file is in `--archive`.
- `smd publish`: validates, then writes the frames, cycle frames, index, graph and page of a board as one bundle.

## 0.2.2 - 2026-10-29

- `smd sources --refresh`: recomputes the sha256 of growing logs (default: every `decision_log`) and edits only the sha256 lines of the manifest.

## 0.2.1 - 2026-10-29

Work of 2026-10-26 to 2026-10-29 between 0.2.0 and the schema change of 0.3.0.

- Python 3.14. `smd revise` opens the next cycle of a board set and applies the human's decisions from a YAML file. `smd graph` (3D page of a board set) and `smd vault` (Obsidian export). The element kind `vision`, the source kind `decision_log`, the cite address `#r=n&t=hh:mm:ss`, and compact YAML output for `smd revise` and `compare --merge`. Russian output writes the garland as «серия связанных событий».
- Roles and actors (`docs/method/roles-and-actors.md`, 27.10): the boards hold roles; the actors that can occupy a role go in the new `fillers` field (positions, places for others and gaps only), and «стейкхолдер» replaces «бенефициар». A role with inner structure, such as stakeholders by tier, keeps a `detail` table (`title`, `columns`, `rows`), shown in the frames panel, the HTML tables and the Markdown digest, never on the boards. `smd validate` checks where `fillers` sits and the row length of `detail`. `qualification-pass` 0.3.1 adds the check "Role, not actor"; `positional-construction` 0.2.1 and `theses-to-board` 0.3.1 apply the rule.
- Screens for dense records, after the c4 frames proved hard to read (pilot case, 27.10). `short` on elements and K: the screen draws the short label and the full one stays in texts, tables and on click; without `short`, labels over 60 characters are cut with «…» and `smd validate` warns. `smd frames --zoom` cuts each reading step to its board (the small and big situation to their half) with a map of the three boards and the count per board; transitions, K, the full screen and every cycle are folded to the skeleton (entry, positions, frames with functions, situations, ends of transitions), the rest of each region becomes a counter that names it by kind, a K whose targets fold moves to the counter, and the legend leaves these frames. The frames page has switches to show and hide AI and clean-room content, functions, places and gaps, K and transitions (with the count hidden), and a panel with the full text, note, K and sources of an element or K on click. Placement does not change when something is hidden.
- `--light` on `smd render` and `smd frames`: a lighter screen for presenting a dense record. Facts, signals, notes, moves awaiting a decision, `refers` links, link labels and the open list leave the screen; the HTML tables keep everything, and each frame's text lists what its step adds off the screen. A wide situation board keeps only a short triangle above its band, and a frame's board fits the window height.
- Sign-offs `partly_k` and `reopen_k`: a K can be marked partly answered or reopened by a human decision; `smd revise --decisions` applies both and keeps the K in `state.open`.
- `smd pack --sources MANIFEST`: the pack names the case's source manifest for `smd validate --sources` and carries it as data.
- Layout for dense records: when the org-activity or object board overflows, the top boards grow and push the situation board down; when the situation board overflows, it extends below its triangle into a full-width band. Records that fit are drawn as before.
- `qualification-pass` 0.3.0, after its first run with a human present (pilot case, 26.10): five gates with a recommendation each; a finding may be answered by a change to the boards instead of a K; the manifest path is asked for, since a pack does not carry it; C1 follows `revises` for earlier transitions; no sign-off sets a K to partly or reopens one.
- `smd frames`: a screen as step-by-step frames in one HTML page (previous/next, arrow keys, text panel toggled with T, print to PDF one frame per page). `--by reading` builds one record up in the organisers' reading order; `--by cycle` shows a chain with what each cycle added. Texts per frame live in a Markdown notes file (`## <frame id>` sections; `--write-notes` drafts the missing ones). The SVG screen starts its legend below the content when a dense record overflows its regions.

## 0.2.0 - 2026-10-25

Steps 2-6 of the build plan; the first version shared with the team. Procedures are drafts (v0.2-0.3), revised after three acceptance runs on a pilot case and not yet re-run.

- Procedures revised after three acceptance runs (blind ingestion, solo session, clean room): proposal mode for runs with no human, defined once in `solo-session`; gate 0 for the reflexive answers; performers proposed by thesis; unknown receiver and payer as gaps; models introduced from outside; inlined classic checks so a clean room needs no other docs.
- Step 6: `smd pack <procedure> [records]`, one Markdown file for any model; `smd render --format sessionflow`; method files packaged in the wheel.
- Step 4: lens library in `lenses/` (khaprov-levels, khaprov-ontology, schukin-boundaries, schukin-interface-tax, fliamer-diamond, design-chain, triz-contradictions, scamper-check) with the selection table; `lens` on hypotheses and ontology records; `smd compare` lists lenses covered.
- Step 3: procedures (small-situation, visionary-tract, positional-construction, functional-plan, problematization, qualification-pass, reflexive-protocol, solo-session), roles and three Claude Code role subagents.
- Step 5, comparison: `smd compare A B` (agreement, refinement, conflict, only in A or B, by positions, frames, functions, institutions, situation, gaps; K matched by text) and `--merge`, a draft cycle on top of B.
- Step 3, records: `ontology` (valid for named positions, per-position subjects, cooperation, what competes with what, realizability test), the `cooperation` element kind, the `represents` relation, and the subject-object warning on the object board.
- Layout: this repository is the main location for the engine's files. The build plan is `docs/plan.md`, and the structural-moves preprint is summarised in `docs/method/structural-moves.md`. Local working files stay outside the repository.
- Step 2, records: a board set carries `theses` (SessionFlow card fields; voice, the six status labels, belt, kind; `feeds` to board elements; an optional structural move), `signoffs` (human sign-off points, each with a function: `close_k`, `accept_move`, `accept_thesis`, `verify_record`) and `reflected_from` (the position a new cycle was made from). Additive to schema v0.2; existing records stay valid.
- Checks: thesis status against voice; AI moves stay candidates until a human accepts them; sign-offs must be human, aimed at the right target and change something; closed K, refined theses and verified records need a sign-off. The Markdown digest lists theses with the SessionFlow labels and the sign-offs.
- Example: `cases/example/bakeries-c2.board.yaml`, cycle 2 of the invented case.
- Hypotheses (`H1..`, the inter-module form) with field results resting on artefacts of the new source kind `field_artefact`, and the `accept_result` sign-off.
- Classic-method checks: `of` (scheme block) on gaps and problem theses, `state.difficulty`, belt degeneration hints, and, across cycles, reflection without a new scheme (`smd validate` passes the revised record when it is among the files).
- HTML page lists theses, hypotheses and sign-offs.
- Procedures: `ingest-transcript`, `theses-to-board`, `field-result`; the `/procedure` command.
- Step 0a: method notes from external primary sources in `docs/method/` (Shchedrovitsky, ОДИ, problematization, TRIZ, systems approach) and their reconciliation with the program's version.

## 0.1.0 - 2026-10-25

Step 1 of the build plan.

- Schemas v0.2: `board_set` (three boards, positions, places for others, frames and functions, gaps, numbered transitions, qualifications, cycles, structural moves) and `source_manifest`.
- `smd validate`: schema with date format checks, semantic errors and warnings, method hints.
- `smd render`: SVG screen with automatic board layout, HTML page, Markdown digest, Mermaid.
- `smd sources`: listing, file presence and sha256 check, clean-room split by lineage.
