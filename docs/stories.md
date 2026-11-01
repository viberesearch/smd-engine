# Stories: a checked view over the boards

A story tells the map of a business to one party: an owner, a buyer, a bank, a successor. It is a view, never a record. It is a walk through the typed links of the boards, and every sentence rests on board ids. Gate ИСТ1 Б (01.11.2026). The procedure that writes one is `procedures/story.md`; the sample is `cases/spectra_coffee/` (an invented business).

In the project's own terms a story is the journal projection π(L, Q, t): the board is the journal L, the party's intent is the query Q, the walk is the part visible under it. A story needs a conflict (it is not a description otherwise) and ends on the open hypotheses, as questions.

A story is a draft of the engine: `voice: ai`, stamped with the board version and sha256, written again when the board changes, never signed. A correction by a reader goes to the board as a thesis, a K or a patch. It is not the founding story of a firm, which is an object on the map (tier 1).

Next to a broker's work a story is an attachment, not a rival to the information memorandum: it shows which levels of the map are empty and which links are not drawn, which a memorandum can leave out. A real business needs the client's consent.

## The story file

`*.story.yaml`, `record: story`, schema 0.1 (`src/smd_engine/schemas/story.schema.json`). `smd validate` reads it by the schema; `smd story check` tests it against the rules below.

| Field | Meaning |
|---|---|
| `id`, `title` | the title says so when the business is invented |
| `boards` | one stamp per board set read: `{id, version, sha256}`; `version` is the board's `state.version`, `sha256` is of the board file |
| `audience`, `protagonist` | element ids (a position or a place for others); the audience may be the protagonist |
| `form` | `scqa`, `premortem` or `scenarios` |
| `allow` | the curated allow-list: the only ids the sentences may rest on |
| `path` | element ids in the order of the walk |
| `conflict` | the conflict objects: ends of an `opposes`, normality boundaries, a series of linked events with its events, red lines in breach |
| `resolution` | the cooperation, goal or function chain the walk reaches; empty when the board has none, and a sentence says so |
| `open` | hypotheses the story ends on |
| `sentences` | `{text, ids, level, part}`: `level` is `hypothesis`, `unverified`, `stated` or `checked`; `part` is free (situation, complication, question, answer) |
| `voice`, `run` | `ai`; `{procedure, version, model, date}` as on a board set |

## `smd story paths`

```bash
uv run smd story paths a.board.yaml [b.board.yaml] --audience ID [--protagonist ID] [--form scqa] [--allow-refers] [--limit 5] [--yaml] [--sources sources.yaml] [--taxonomies taxonomies.yaml]
uv run smd story paths a.board.yaml --gaps --audience ID --audience ID2
```

Board sets of one case are read together; one id in two of them is an error. With `--sources` and `--taxonomies` (here and in `check` and `render`) each board set is validated as `smd validate` does, so a citation or a tag error stops the command (exit 2). `--protagonist` defaults to the audience and is given once for each `--audience`.

**Walks.** Simple walks of 4 to 9 items from the protagonist, over the relations of the boards in either direction, through at least one conflict object, ending at a resolution object that comes after it.
- Typed links are every relation kind but `refers`. `refers` is walked only with `--allow-refers` and is marked `~` in the output. `performed_by`, `in` and `seen_from` are not links: they say who and where, not what passes.
- Conflict objects: both ends of an `opposes`; a `normality_boundary`; a `garland` (series of linked events) and the events that `belongs` to it; an element whose `line` and `observed` breach the red-line rule (`docs/red-lines.md`).
- Resolution objects: a `cooperation` or a `goal`; or a `function` reached from a function when both come after the last conflict object.
- The conflict of a candidate contains the conflict objects on the walk and both ends of every `opposes` that touches it (rule G5).

**Order**, lexicographic and without weights: (1) the share of typed links, more first; (2) the best leverage rank among the open hypotheses on the walk (`smd status`: a walk that contains the highest-reach hypothesis comes first; how many hypotheses it contains does not count); (3) fewer items; (4) fewer components of the typed graph crossed; (5) fewer links walked against their direction; (6) the ids. A walk that meets a resolution object before its first conflict object is not a candidate. `open` lists the untested hypotheses whose `targets` meet the walk, in leverage order, then those in testing.

`--yaml` prints one story skeleton for each candidate: structure and stamp filled, no sentences, `allow` a suggestion for a human to curate. A search stops at two million steps and says so.

**`--gaps`.** For each (audience, protagonist) pair the report says whether a typed walk exists. If not, it gives the protagonist's component of the typed graph and the conflict and resolution objects in it, and then the cheapest route to a walk: typing a `refers` that exists, linking two items that a thesis, hypothesis, K or ontology record names together, or, failing both, joining the nearest items by a new link. For each link: from, to, what exists now, a suggested kind and, for a flow, `carries`. The suggestion follows the kinds of the two ends and is a guess. The cheapest route is compared lexicographically, without weights: fewest joins between boards, then fewest joins within a board, then fewest links between items that a record names together, then fewest typed `refers`, then fewest hops. The links are claims the group has to make; the engine adds none.

## `smd story check`

```bash
uv run smd story check owner.story.yaml --boards a.board.yaml [b.board.yaml] [--sources sources.yaml] [--taxonomies taxonomies.yaml]
```

Exit 0 without errors, 1 with errors, 2 when a file cannot be read.

| Rule | Checks | Result |
|---|---|---|
| G1 | each sentence has at least one id, and each id exists on the boards | error |
| G2 | the declared level is not above the weakest of its ids | error |
| G2 | the modal words of a sentence that declares `stated` or `checked`; a `hypothesis` or `unverified` sentence with none | hint, read by eye |
| G3 | every number in a sentence is in the text of one of its ids, every date is a whole date of one | error |
| G4 | the ids of a sentence are in `allow` | error |
| G5 | no `opposes` that touches the path is left out of `conflict` | error |
| G6 | a comparative or superlative in a sentence with no number («уже» only before «чем», with or without a comma) | hint |
| G7 | `voice` is ai; the version and sha256 of each board match the stamp | error: regenerate |

Structure: `S1` ids exist (and `open` lists hypotheses), `S2` neighbours on the path are joined by a link (an error when none, a warning when only a `refers`), `S3` the conflict lies on the path or is opposed to it and the resolution lies on it (an empty resolution is a warning), `S4` the path has 4 to 9 items, a conflict object lies on it, and no resolution object comes before the first one.

**G2, the levels.** The level of an id: an element has its `epistemic`, `stated` when it has none; a hypothesis is `checked` when `confirmed` or `refuted` and `hypothesis` when `untested` or `testing`; a thesis is `stated` when `voiced` or `refined` and `hypothesis` otherwise; a K is `stated` when closed, else `hypothesis`; an ontology record has the level of its `test`. The code compares levels only. Whether the wording matches the level is for a person: the hint lists the modal words (если, возможно, предлагается, проверим, if, may) and the weak sentences that have none.

**G3, the numbers.** A number is read as a value, so «3», «три» and «трёх» are one number, «0,95 млн» is 950 000, a run of Russian number words is summed («двадцать пять» is 25, «сто двадцать» 120, «две тысячи двадцать пять» 2025). Number words: Russian and English (две, пять, сто, тысяча; two, hundred), multipliers and fractions («вдвое», «втрое», «дважды», «половина», «треть», «полтора»; "twice", "half"). Not read as numbers: ordinals, the indefinite «один» and "one", «пара», «несколько». **Dates are not numbers.** A date is read whole (ISO, dotted, «3 по 17 августа 2026», «30 июня», «в марте 2026»); its month and day never pass as loose numbers. A date in a sentence must match a date of one of its ids in every part it gives («30 июня» matches 2026-06-30; «30 июня 2026» does not match a date with no year), and a bare year must be the year of such a date. The text of an id is all its words and numbers except ids and structure fields; for a red line it also contains the days of its breaches and their first and last dates. The form's own constants are allowed: 3 for `premortem` (years back), 2 for `scenarios`. The match is by value: it cannot tell a number used for another thing, so G3 shows that a figure is on the board and not that the sentence uses it right.

**G7.** `sha256` is `shasum -a 256` of the board file; any edit of it, a comment too, means the story is written again.

## `smd story render`

```bash
uv run smd story render owner.story.yaml --md [--boards a.board.yaml] [--lang ru|en] [-o owner.md]
```

A story as readable Markdown: the title, the audience and form, the sentences by part with the board ids each rests on in brackets, the open questions (with `--boards`, each shows what its hypothesis assumes) and the stamp (boards, versions, sha256, voice, run). It checks nothing; run `smd story check` first. An invented story keeps its marking in the title, so the first line of the page says so.

## Reading a result

A story that passes has no sentence without a board id, no figure the board does not hold, no sentence stronger than its weakest source and no dropped opposition. It can still be a bad story: the walk may be the wrong one, the allow-list too wide, the wording too sure. Those are for the игротехник and the client.

The first use of `paths` on a real board is the list of gaps (`--gaps`): where the record has no typed link between two items a story would need. On the MIPT case's cycle 5 only one of five hand-drawn story skeletons followed typed links (research note of 01.11.2026).
