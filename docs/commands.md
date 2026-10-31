# Commands: examples and details

Every command is `smd <command> --help`. The examples below use `uv run smd` inside a checkout of this repository; with the installed tool, write `smd`. The overview table is in `README.md`.

Exit codes: 0 success; 1 the check found errors (or, with `--strict`, warnings; for `eval`, a missed threshold); 2 a file could not be read or an argument is wrong.

```bash
uv run smd new path/to/case --profile program-three-boards --lang en --title "Family bakery"   # a case folder that validates at once: the first record, a source manifest, a README with the next steps; --case sets the case id (default: from the folder name); nothing is overwritten
uv run smd status cases/example/bakeries-c2.board.yaml --lang en -o out/status.md   # the core view of a board set on one page of Markdown: state line, open K, hypotheses, sign-offs waiting, transitions, counts
uv run smd next cases/example/bakeries-c2.board.yaml   # the procedure to run next, with one line why and at most two alternatives; a rule table, no model
uv run smd validate cases/example --sources cases/example/sources.yaml --hints   # a directory: each cycle is also checked against the one it revises
uv run smd validate cases/example_ru --sources cases/example_ru/sources.yaml   # the same case with Russian labels
uv run smd validate path/to/case --taxonomies path/to/taxonomies.yaml   # check tags and detail columns bound by detail.keys against the case's taxonomies
uv run smd migrate path/to/case   # report what moving the records to schema v0.3 changes; --write edits the changed lines in place, comments kept
uv run smd render cases/example/bakeries-c1.board.yaml -o out/screen.svg
uv run smd render cases/example/two-boards-c1.board.yaml -o out/two-boards.svg   # a record on the classic-two-boards profile: two boards side by side
uv run smd render cases/example_ru/pekarni-oru-c1.board.yaml -o out/oru.svg   # a record on the management-four-boards profile: G.P.'s scheme of ОРУ on four boards
uv run smd render cases/example/bakeries-c1.board.yaml --format html -o out/screen.html
uv run smd render cases/example/bakeries-c1.board.yaml --format md --lang en
uv run smd render cases/example/bakeries-c1.board.yaml --format mermaid
uv run smd render cases/example/bakeries-c2.board.yaml --format sessionflow   # «Наша малая ситуация. Материал к сообщению»
uv run smd frames cases/example/bakeries-c2.board.yaml --notes out/notes.md --write-notes -o out/frames.html   # step-by-step frames with texts to read aloud
uv run smd frames cases/example/bakeries-c1.board.yaml cases/example/bakeries-c2.board.yaml --by cycle -o out/cycles.html   # one frame per cycle, new elements ringed
uv run smd frames cases/example/bakeries-c2.board.yaml --light -o out/frames.html   # lighter screen for a dense record; facts, signals and notes go to the frame texts
uv run smd frames cases/example/bakeries-c2.board.yaml --light --zoom -o out/frames.html   # each step cut to its board; the overview folded to its skeleton with counters
uv run smd graph cases/example/bakeries-c2.board.yaml --sources cases/example/sources.yaml -o out/graph.html   # the boards as stacked planes in 3D, records above, sources below; filters by link kind; one self-contained page
uv run smd index cases/example/bakeries-c2.board.yaml --sources cases/example/sources.yaml --archive /local/sources -o out/index.html   # every K, thesis, hypothesis, O, sign-off and element with its YAML line; a cite links to its file only when the file is in --archive, otherwise the source title is shown
uv run smd publish cases/example/bakeries-c2.board.yaml --sources cases/example/sources.yaml --out out/pub   # validate, then write <id>_frames, <id>_cycle_frames, <id>_index, <id>_graph and <id> as HTML; nothing is written if validation fails; takes --lang, --light, --zoom, --notes, --archive, --strict, --taxonomies
uv run smd vault cases/example/bakeries-c2.board.yaml out/vault --sources cases/example/sources.yaml   # Obsidian vault: a note per element, thesis, hypothesis, K and source; links as typed properties; the screen as a canvas
uv run smd pack solo-session cases/example/bakeries-c2.board.yaml --sources cases/example/sources.yaml -o out/pack.md   # attach to any model; --sources carries the manifest, --taxonomies the taxonomy file; with board sets, the skeleton of the latest cycle as "Cells to fill"; prints `pack sha256: <hex>` to stderr, the hash of what it wrote, for `run.pack_sha256`
uv run smd sources cases/example/sources.yaml --clean-room --deny-lineage earlier-concept
uv run smd sources path/to/sources.yaml --folder /local/folder
uv run smd sources path/to/sources.yaml --folder /local/folder --refresh [ids]   # recompute sha256 of the named sources (default: every decision_log) and, where a source carries `lines`, its line count; edit only those lines of the manifest
uv run smd compare a.board.yaml b.board.yaml -o out/compare.md --merge out/merge.board.yaml
uv run smd eval run.board.yaml cases/example/golden/bakeries-c2-expected.board.yaml --min-agreement 10 --max-only-expected 3   # did a procedure run get worse: the five compare counts, the `run` stamps of both records (procedure, version, model, date, `pack_sha256`, `inputs`, `temperature`, `sample` when present), theses matched by cites, K and H matched by wording; exit 1 on a missed threshold
uv run smd agree out/run1.board.yaml out/run2.board.yaml out/run3.board.yaml [--fields belt,kind] [--json]   # how stable are the labels across N runs of one procedure on one input: Krippendorff's alpha per label field, and the share of cite addresses every run found; see below
uv run smd revise cases/example/bakeries-c2.board.yaml --decisions decisions.yaml -o out/bakeries-c3.board.yaml   # next cycle with the human's sign-offs applied
uv run smd apply cases/example/bakeries-c2.board.yaml cases/example/patches/bakeries-c2-1.patch.yaml -o out/bakeries-c2.board.yaml --sources cases/example/sources.yaml   # a decision on the current cycle as a patch (set and remove by id or by transition number n, board_notes): the next sub-version, validated (also --taxonomies); nothing is written on errors
```

`validate` reports three levels:
- **error:** inconsistent record (dangling reference, broken numbering).
- **warning:** breaks a convention of the method, e.g. an item with no position it is seen from.
- **hint** (with `--hints`): a methodological observation, e.g. an empty small situation, or a new frame with no functional plan.

`publish` validates the record and the earlier cycles it `revises` (found next to it). An error anywhere in that chain stops the bundle. With `--strict`, a warning on the published record stops it too; warnings on earlier cycles are printed, marked "earlier cycle: not failing", and the bundle is written. The bundle's index links files relative to the `--out` folder, so the folder can be moved or sent: the record file and `--archive` files are linked by relative paths, a file that shares no folder with `--out` except the root is named without a link, and `YAML:N` is a line number, not a VS Code link. `smd index` links the same way, relative to the folder of `-o`, or to the current folder when it prints the page; neither page holds an absolute path of the building machine.

`sources --folder` checks that every listed file is present, has a sha256, and matches it. `--refresh` rewrites the sha256 instead, for logs that grow.

`agree` takes two or more board sets, runs of one procedure on one input (the golden README shows how to make them), and measures how stable the labels the model writes are. It warns, and goes on, when `run.procedure`, `run.pack_sha256` or `run.inputs` differ between the records or are missing from some. The records must follow one profile.
- **Units.** A thesis is matched across runs by the address it cites, as `eval` pairs theses (same source, a `#t=` time within 30 s); a run with no thesis at an address gives a missing value. A thesis with no `cites` has no address and is not counted. An element of the first record is matched in each other run as `compare` matches it; elements only a later run has are not units.
- **Fields.** For theses: `belt`, `kind`, `status`, `voice`, `of`, `op` (the thesis move's op). For elements: `element.kind`, `element.of`, `element.op`. `--fields` takes a comma-separated subset; the default is all.
- **Alpha.** Krippendorff's alpha for nominal values, any number of runs, missing values allowed (`agree.py` cites Krippendorff 2011). A unit with fewer than two values is not pairable. For `of` and `op`, a run that has the unit but not the label gives the value `(none)`, so adding or dropping a label counts as a disagreement; a unit no run labels is not a unit of that field. Alpha is `n/a` when only one value occurs in all the pairable data, because chance agreement is then total and there is nothing to measure, or when no unit has two values. With fewer than five pairable units an alpha is shown with "few units" and left out of the reading line: one or two units swing it from 0 to 1.
- **Coverage.** The share of cite addresses that every run, some runs (two or more, not all) or one run only found, with the one-run-only addresses (the first 10).
- **Reading.** Krippendorff's convention: alpha of 0.800 or more is reliable, 0.667 to 0.800 tentative, below 0.667 not reliable. It is a convention and not a law; with few units, alpha moves a lot between samples.
- `--json` prints the same figures as JSON, with `alpha: null` for `n/a`. Exit 0 whatever the alpha; 2 for fewer than two records, an unknown field or records of two profiles.

`compare` matches the elements of two board sets by kind group and wording and classifies each pair as agreement, refinement, conflict, or present in one set only. `--merge` writes a draft cycle on top of B: elements only in A are imported as hypotheses with a `from-<A>` lineage tag, and each conflict becomes an open K with the options lock, fork, rebase, merge. Matching by wording is a heuristic; the report is material for a qualification pass. When an ontology record of either set has `lives_in`, `tempos`, `horizon` or `covers`, the report adds a section `ontology: continuum`: the records matched by id, with those fields in A and in B.

## new, status, next

`new <folder>` writes three files and refuses, writing nothing, if one exists: `<case>-c1.board.yaml` (the required top-level fields, `profile`, the entry where the profile has one, one position to rename, empty lists for what the procedures fill, a comment naming the profile's boards), `sources.yaml` (one entry, `s1`, pointing to `notes.txt`) and `README.md` (the next steps, with the first procedure). `smd validate <folder> --sources <folder>/sources.yaml --strict` gives 0 errors and 0 warnings on every profile; the hints left are the work to do (the empty boards, and "1 position(s) and no places for others"). `--profile` defaults to `program-three-boards`, `--lang` to `ru`. The first procedure is the first step of the `solo-session` order the profile can run: `small-situation` on the default profile, `positional-construction` on the others, since `small-situation` and `visionary-tract` are written for the default profile only.

`status <record>` prints the core view, in this order and nothing else:
- the state line (cycle, version, status, the cycle it revises, how many items are accepted and open) with `state.difficulty` and `state.next_move`;
- the K not closed, open first and then partly answered;
- the hypotheses in `testing`; then, for each `untested` or `testing` hypothesis with `rule` and `observed`, the verdict the rule proposes by the Wilson interval (`docs/data-model.md`, Hypotheses; a proposal, the group signs `accept_result`); then the `untested` ones in leverage order, below;
- AI-voiced items waiting for a human sign-off: thesis variants (`ai_variant`), candidate moves, K and H drafted by an AI that are not closed or resolved;
- the transitions;
- the counts of elements per board (halves of the situation board apart) and per kind.

Lists are cut to a fixed length and end in "and N more" (8 K, 5 hypotheses in testing, 8 verdicts, 5 untested, 5 transitions, 6 ids per waiting item, 8 kinds), one line per item. The page for the MIPT case's cycle 5 (132 elements, 19 K, 40 hypotheses) is 46 lines. The labels come from the same `LABELS` tables as the other pages; `--lang ru` is the default.

**Hypothesis leverage (a proposal).** For each untested hypothesis the engine collects what a refutation would reach: its `targets`; its `qualifications` (K); the ontology records whose `test` is this hypothesis; the theses whose `feeds` or `about` hold one of its targets; and the elements one relation away from a target (either end of a relation, a target not counted twice). The score is the size of that set, the order is by score and then by id with numbers read as numbers (H2 before H10). It is the same for the same record. It is not a probability and carries no weight: a hypothesis can be worth testing for a reason the board does not show. The group chooses which to test; the order only saves it from counting by hand. `smd status` lists it, and `smd index` shows the score in the hypotheses table (column "reach (proposal)", the parts of the count as the tooltip).

**`next <record>`.** The rules are read top to bottom; the first whose condition holds names the procedure to run (`smd pack <procedure> <record>` is printed), the next two are shown as alternatives, each procedure once. A procedure written for another profile than the record's is skipped, as `smd pack` would refuse it. If no rule fires, the output says so. The record must validate; its hint findings are read through `validate_record`. The rules sit in one list, `RULES` in `src/smd_engine/nextstep.py`, in the order of `procedures/solo-session.md` (section 3) and the `next` keys of `procedures/README.md`:

| # | Condition | Procedure | Why |
|---|---|---|---|
| 1 | the record revises a cycle and names no `reflected_from`, or `state.difficulty` is empty | `reflexive-protocol` | the reflexive questions of the closed cycle come first (gate 0) |
| 2 | a thesis has neither `feeds` nor `about` | `theses-to-board` | information not laid into a cell of a scheme |
| 3 | the small half of the situation board is empty (hint) | `small-situation` | the four questions come first |
| 4 | the big half is empty (hint) | `visionary-tract` | the big situation is not laid out |
| 5 | fewer than two positions and no place for others (hint) | `positional-construction` | the positional set looks incomplete |
| 6 | a new frame has no functions, or functions with no performer (hint) | `functional-plan` | the plan names who performs and who pays |
| 7 | a gap or a problem thesis names no block of a named scheme (hint) | `problematization` | plus and minus on a named scheme |
| 8 | the record has no K | `qualification-pass` | not yet checked against the criteria |
| 9 | cycle 1 and no theses | `ingest-transcript` | with a recorded group talk, start from it (`next` cannot see the sources) |
| 10 | a hypothesis is in `testing` | `field-result` | if the field gave an artefact, record the result |
| 11 | none of the hints of rules 3 to 7 is open and the record has K | `reflexive-protocol` | closes the cycle and opens the next |

What people have to decide (K not closed, AI variants, `state.open`) is not a procedure; `next` reports the counts above its answer. The answer is a proposal: the owner or the group may run another step (`solo-session`, section 3).
