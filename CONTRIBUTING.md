# Contributing

Thank you for reading the code. This file says how the repository is built and what a change of each common kind touches, as the code stands today. If a step below no longer matches the code, the code is right and this file needs a fix.

## Setup and rules

- Python 3.14, `uv` only. `uv sync` installs the package and the dev tools.
- Records are YAML and are the single source. Drawings and digests are generated from them and never edited by hand.
- Case material belongs to the case's own repository. This repository holds invented examples only: no real names, no real firms.
- No emojis in code or docs. Prose is plain and literal. A doc stays under 300 lines.
- A procedure, role or lens that changes its output format bumps its `version`.

## Branch, tests, pull request

1. Branch from `main`: `feature/<topic>`, `fix/<topic>`, `docs/<topic>`. Do not commit to `main`.
2. Before you push, all four must pass:

```bash
uv run black . && uv run flake8 && uv run mypy src && uv run pytest
```

3. CI (`.github/workflows/ci.yml`) runs black, flake8, mypy, pytest and a trivy scan. A pull request is merged after CI is green.
4. Commit messages are conventional: `feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `chore(scope): ...`.
5. Update the docs in the same change: `docs/data-model.md` for any record field, `docs/checks.md` for any check, `docs/profiles.md` for the profile format, `docs/commands.md` and the table in `README.md` for a command, `CHANGELOG.md` for anything a user would notice.

Tests live in `tests/`, one file per area (`test_validate.py`, `test_profile.py`, `test_apply.py`, ...). The fixtures `board`, `board2` and `manifest` in `tests/conftest.py` load `cases/example/` and are deep-copied for each test, so a test may change them freely. Add one focused test per behaviour you add.

## Where things are

| Path | What |
|---|---|
| `src/smd_engine/cli.py` | the `smd` entry point: one `cmd_*` function and one subparser per command |
| `src/smd_engine/schemas/` | JSON Schemas, one per record type: `board_set`, `source_manifest`, `taxonomies`, `board_patch` |
| `src/smd_engine/validate/` | the checks, one module per subject, run in the order of `REGISTRY` in `validate/__init__.py` |
| `src/smd_engine/profile.py`, `screen.py` | loader and parser of `profiles/*.yaml` (the `Profile` type and the checks of a profile file); the screen geometry the parser and the renderers share |
| `src/smd_engine/render/` | layout and the output formats; `render/assets/` holds the CSS and JS of the frames and graph pages |
| `src/smd_engine/apply.py`, `revise.py`, `migrate.py` | `smd apply`, `smd revise`, `smd migrate` |
| `src/smd_engine/compare.py`, `eval.py`, `pack.py`, `sources.py` | `smd compare`, `smd eval`, `smd pack`, `smd sources` |
| `profiles/`, `procedures/`, `roles/`, `lenses/` | method files as data; `pyproject.toml` includes each in the wheel under `smd_engine/assets/` |
| `cases/example/`, `cases/example_ru/` | invented teaching cases used by the tests (`example`) and as a Russian sample (`example_ru`) |
| `docs/` | data model, commands, method notes, build plan; index in `docs/README.md` |
| `.claude/` | Claude Code subagents for the roles and the `/procedure` command; optional |

## Add an element kind

A kind is data. Edit the `kinds` list of the profile file, for example `profiles/program-three-boards.yaml`: one line with `id`, `label: {ru, en}` (plural), `home` (the board it usually lies on), `shape`, and the flags `needs_position`, `container`, `role`, `scheme`, `skeleton` and `light_off` (all default to false). The list order is the layout order. The schema accepts any string as a kind, and the validator, layout and every renderer read the profile, so no code changes for a plain kind. Files touched:
- the profile file;
- `docs/data-model.md`, the list of kinds;
- a test in `tests/test_profile.py`: a record using the kind validates, and one with a typo is an error.

Meanings come from attributes, not ids: `shape: frame` marks a kind that holds function chips and has a `frame_state`, `shape: heading` draws the bold situation paragraph, `light_off: true` leaves a kind off the lighter screen (`--light`). Only a few kinds are named by id in code, and every profile must define them: `position`, `place_for_others`, `function`, `cooperation`, `gap` and `note` (`REQUIRED_KINDS` in `src/smd_engine/profile.py`), and `entry` when the profile enables the hint `entry`; the parser refuses a profile without them. A hint of one profile's scheme (`src/smd_engine/validate/management.py`) may name that profile's kinds and relation kinds: it registers them in `@hint(id, kinds=..., relations=...)`, and a profile that enables it must define them. A kind that needs behaviour of its own is code in the checks or renderers; the ids and where the engine names each are in `docs/profiles.md`.

## Add a check

A check is a function that takes the context `Ctx` (`validate/context.py`) and returns a list of `Finding("error" | "warning" | "hint", ref, message)`. More than one file:
1. Write the function in the module of its subject under `src/smd_engine/validate/` (`structure.py`, `theses.py`, `hints.py`, ...). Decorate a check that only applies to board sets with `@board_set`.
2. Add it to `REGISTRY` in `src/smd_engine/validate/__init__.py` (and its import). Findings come out in registry order.
3. A method hint is declared with `@hint("hint-id")` and runs only for a profile that lists the id under `hints`. Add the id to the `hints` list of each profile that should have it; an id that no check declares is an error of every record that names it.
4. Describe the check in `docs/checks.md`.
5. Test it in `tests/test_validate.py`: take the `board` fixture, break one thing, assert on the finding.

## Add a profile

One file: `profiles/<id>.yaml`. The file name is the profile id. The keys are `id`, `title`, `screen`, `boards`, `kinds`, `relations`, `hints`, `compare_groups`, `compare_skip`, `reading` and optionally `sessionflow`; the format is `docs/profiles.md`. The loader lists the folder, so there is no registry to edit, and the wheel already includes the whole folder. A malformed file is reported as an error of every record that names it. What to get right:
- **Boards stand in their regions.** Each board has a `region: [x0, y0, x1, y1]` on the screen (width 1600) and the layout places its items there, kind by kind in the order of `kinds`. Boards whose regions overlap vertically form a row, and a row that overflows grows and pushes the rows below down. `screen: regions` (the default) draws any number of boards, halved (`halves: [small, big]`, with `split`) or not, as rectangles around their regions; `screen: triangles` is the program's screen and takes exactly three boards. The parser refuses boards off the screen or overlapping as drawn.
- **Required ids.** Define the kinds `position`, `place_for_others`, `function`, `cooperation`, `gap` and `note`, and `entry` if the hint `entry` is on. No board id is fixed; flag the board of objects with `object: true`, and name the screen meaning of a kind by `shape` and the flags `light_off` and `compare_skip`.
- **Hints and reading.** List only hints that exist in `src/smd_engine/validate/hints.py`; leave `situation-halves` off if no board is halved into situations. `reading` uses the step ids that `smd frames` has texts for (`entry`, `positions`, `places`, `small`, `big`, `old-frame`, `new-frame`, `object`), each at most once.

Then:
- a sample record on the profile under `cases/example/`, like `two-boards-c1.board.yaml`, and a test in `tests/test_profile.py` that it validates and draws;
- the list of shipped profiles in the Profiles section of `docs/data-model.md`, and `docs/profiles.md` if the format changed.
Existing tests that list the known profiles (`test_unknown_kind_or_board_is_an_error`) need the new id.

## Add a lens

One file: `lenses/<id>.md`, with the front matter and sections described in `lenses/README.md`. More than one file: add a row for each place a procedure offers it to the selection table in `lenses/README.md`, and list the lens id in the procedure's text. `tests/test_lenses.py` checks every file in the folder (front matter keys, `id` equal to the file name, `offered_by` naming existing procedures), so a new lens is covered without a new test. `smd pack <procedure>` includes the lenses whose `offered_by` lists that procedure.

## Add a procedure

One file: `procedures/<id>.md`, with the front matter described in `procedures/README.md` (`id`, `title`, `step`, `version`, `role`, `profile`, `inputs`, `outputs`, `sources`, optionally `next`). More than one file: add a row to the table in `procedures/README.md`. `tests/test_procedures.py` checks every file in the folder, and `smd pack <id>` and `/procedure <id>` find it by name. The existing procedures end by writing `run: {procedure, version, model, date}` into the record and by running `smd validate`; do the same. A procedure for a new role also needs the role file in `roles/` and an entry in `ROLE_FILES` in `src/smd_engine/pack.py`.

## Release

The owner releases. The version is in `pyproject.toml` and the entry in `CHANGELOG.md`; a tag `vX.Y.Z` that matches the version runs `.github/workflows/release.yml`, which builds the sdist and the wheel and publishes them to PyPI through a trusted publisher. `uv build` should produce both files locally before you propose a release.
