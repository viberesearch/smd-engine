# Commands: examples and details

Every command is `smd <command> --help`. The examples below use `uv run smd` inside a checkout of this repository; with the installed tool, write `smd`. The overview table is in `README.md`.

Exit codes: 0 success; 1 the check found errors (or, with `--strict`, warnings; for `eval`, a missed threshold); 2 a file could not be read or an argument is wrong.

```bash
uv run smd validate cases/example --sources cases/example/sources.yaml --hints   # a directory: each cycle is also checked against the one it revises
uv run smd validate cases/example_ru --sources cases/example_ru/sources.yaml   # the same case with Russian labels
uv run smd validate path/to/case --taxonomies path/to/taxonomies.yaml   # check tags and detail columns bound by detail.keys against the case's taxonomies
uv run smd migrate path/to/case   # report what moving the records to schema v0.3 changes; --write edits the changed lines in place, comments kept
uv run smd render cases/example/bakeries-c1.board.yaml -o out/screen.svg
uv run smd render cases/example/two-boards-c1.board.yaml -o out/two-boards.svg   # a record on the classic-two-boards profile: two boards side by side
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
uv run smd pack solo-session cases/example/bakeries-c2.board.yaml --sources cases/example/sources.yaml -o out/pack.md   # attach to any model; --sources carries the manifest, --taxonomies the taxonomy file
uv run smd sources cases/example/sources.yaml --clean-room --deny-lineage earlier-concept
uv run smd sources path/to/sources.yaml --folder /local/folder
uv run smd sources path/to/sources.yaml --folder /local/folder --refresh [ids]   # recompute sha256 of the named sources (default: every decision_log) and edit only the sha256 lines of the manifest
uv run smd compare a.board.yaml b.board.yaml -o out/compare.md --merge out/merge.board.yaml
uv run smd eval run.board.yaml cases/example/golden/bakeries-c2-expected.board.yaml --min-agreement 10 --max-only-expected 3   # did a procedure run get worse: the five compare counts, theses matched by cites; exit 1 on a missed threshold
uv run smd revise cases/example/bakeries-c2.board.yaml --decisions decisions.yaml -o out/bakeries-c3.board.yaml   # next cycle with the human's sign-offs applied
uv run smd apply cases/example/bakeries-c2.board.yaml cases/example/patches/bakeries-c2-1.patch.yaml -o out/bakeries-c2.board.yaml --sources cases/example/sources.yaml   # a decision on the current cycle as a patch (set and remove by id or by transition number n, board_notes): the next sub-version, validated (also --taxonomies); nothing is written on errors
```

`validate` reports three levels:
- **error:** inconsistent record (dangling reference, broken numbering).
- **warning:** breaks a convention of the method, e.g. an item with no position it is seen from.
- **hint** (with `--hints`): a methodological observation, e.g. an empty small situation, or a new frame with no functional plan.

`sources --folder` checks that every listed file is present, has a sha256, and matches it. `--refresh` rewrites the sha256 instead, for logs that grow.

`compare` matches the elements of two board sets by kind group and wording and classifies each pair as agreement, refinement, conflict, or present in one set only. `--merge` writes a draft cycle on top of B: elements only in A are imported as hypotheses with a `from-<A>` lineage tag, and each conflict becomes an open K with the options lock, fork, rebase, merge. Matching by wording is a heuristic; the report is material for a qualification pass.
