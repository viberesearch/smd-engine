# Glossary

The terms a first-time user meets, one line each. The format behind them is in `data-model.md`; a walkthrough that uses them is in `first-board.md`.

| Term | Meaning |
|---|---|
| board set | One YAML record: a whole screen at one moment, with its elements, relations, theses and decisions. One file per cycle (`bakery-c1.board.yaml`) |
| board | A named area of the screen that holds elements of certain kinds: org-activity (`od`), object (`oo`), situation (`s`), and in other profiles `ot`, `ap`, `us` |
| profile | A file in `profiles/` that sets the boards, the element kinds, the relation kinds and the hints in force. A record names it in `profile`; `program-three-boards` is the default |
| element | One item on a board: an `id`, a `board`, a `kind` and a `label`, usually with the position it is seen from |
| kind | What sort of element it is (`position`, `frame`, `function`, `situation`, `gap`, ...); the profile lists the allowed kinds |
| position | An element of kind `position`: a place in an activity from which something is seen or done. Most elements name the position they are seen from (`seen_from`) |
| relation | A typed link between two elements (`flow`, `belongs`, `opposes`, `refers`, ...), kept in `relations` |
| transition | A numbered move between boards (from one element to another); the numbers 1..n draw the trajectory of the group's thinking and start from 1 in each cycle |
| thesis | A card from a transcript or a dialogue: a claim, who voiced it, its status and the source address it cites. A thesis feeds elements |
| hypothesis (H) | A field test: what we assume, the action that tests it, what we observe, and when to revise it. Its status is `untested`, `testing`, `confirmed` or `refuted`; a result needs a sign-off |
| qualification (K) | A numbered remark of the methodologist on the record (`K1`, `K2`, ...) with the status `open`, `partly` or `closed`; only a human sign-off closes it |
| sign-off | A human decision recorded with its function (`close_k`, `accept_thesis`, `accept_move`, ...). The engine and the AI propose; only a sign-off raises an AI variant or closes a K |
| hint | A methodological observation from `smd validate --hints`, for example "small situation not laid out". It tells what is missing and never fails the run. Errors and warnings are the other two levels |
| lens | A content model (Khaprov, Schukin, Fliamer's diamond, TRIZ, ...) that a procedure may offer at a step: questions and the slots they fill. The human may decline it (`lenses/`) |
| role | The position an AI or a human takes in a session: игротехник (runs the session), методолог (qualifies), визионер (proposes the big picture). A procedure names its role (`roles/`) |
| procedure | A model-agnostic prompt in `procedures/` for one step of the work, run by any model after `smd pack`. It proposes a record; it does not sign off |
| patch | A decision on the current cycle as a record (`add`, `set`, `remove`, `state`), applied by `smd apply` as the next sub-version |
| cycle | One pass of the screen. A cycle ends in a reflexive exit; the next one is a new file (`-c2`) with `cycle: 2` and `revises` naming the previous one. `smd revise` opens it |
| taxonomy | A file of named value sets (for example tiers) that `tags` and bound table columns may take; the validator checks the values |
| manifest | `sources.yaml`: the case's raw materials, listed with an id, a kind, a checksum and a clean-room decision, and never copied. Records cite a source by its id and an address (`s1#t=00:08:10`) |
