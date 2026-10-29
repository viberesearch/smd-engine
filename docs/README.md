# Documentation

Start with `README.md` in the repository root. This folder holds the reference documents; the method files that the engine runs are in their own folders.

## Reference

| File | Content |
|---|---|
| `data-model.md` | the record format: board sets, source manifests, taxonomies, patches, the `profile` key, migration |
| `checks.md` | the checks the validator runs: errors, warnings and hints, and the profile and source of each hint |
| `profiles.md` | the profile format: boards and their regions, kinds, the screen layout, the ids every profile defines, the checks of a profile file |
| `commands.md` | the commands of `smd` with examples, and the exit codes |
| `plan.md` | the build plan approved 2026-10-25 and the architecture of the repository |
| `stages.md` | the build steps, their status, and where each method enters the engine |

## Method notes

`method/` is the method from external primary sources and what it changes in the engine. Its index is `method/README.md`. The notes keep claim marks ([V] read in the primary text, [S] secondary only, [UNVERIFIED], [ANALYSIS]) so that the reader can tell a source's statement from the engine's reading.

## Files the engine runs

| Folder | Content | Index |
|---|---|---|
| `../procedures/` | model-agnostic procedure prompts, one file each | `../procedures/README.md` |
| `../roles/` | the positions an AI or a human takes in a session | `../roles/README.md` |
| `../lenses/` | content models a procedure offers, and the selection table | `../lenses/README.md` |
| `../profiles/` | boards, element kinds and hints as data | `profiles.md`, `data-model.md` (section Profiles) |

## Examples

| Folder | Content |
|---|---|
| `../cases/example/` | an invented case in English: two cycles, a patch, a classic-profile record, a golden run |
| `../cases/example_ru/` | the same case with Russian labels, and two records on the management profile: G.P.'s scheme of ОРУ (`pekarni-oru-c1`) and its Beer layer, one bakery sold to a holding (`pekarnya-holding-c1`) |
| `../cases/example/golden/README.md` | how to check a procedure run against a reference record with `smd eval` |

## Other files in the root

| File | Content |
|---|---|
| `README.md`, `README_ru.md` | overview in English and in Russian |
| `CONTRIBUTING.md` | branch, tests, and how to add a kind, a check, a profile, a lens or a procedure |
| `CHANGELOG.md` | what each release added |
| `LICENSE` | MIT for code; the method notes and examples are CC BY 4.0, as `README.md` states |
