# Classic method and the program's version: what changes in the engine

Compiled 2026-10-25 from `smd-classic.md`, `odi-problematization.md`, `triz-systems.md` (external primary sources) and the digests of the MIPT module-1 materials. Source keys as in those files.

Claim marks follow the research notes:
- **[V]** read in the primary text;
- **[S]** confirmed only in a secondary source;
- **[UNVERIFIED]** not found in a primary text.

Three quotations were checked against the downloaded texts: "знание о незнании" (GP-PP); "проверяются лишь на реализуемость" (GP1981); "руководитель игры" and "методолог-консультант" (PG-GT).

## 1. Boards

- **Classic:** two boards, the ontology board and the org-activity board. In games this is the "double work with schemes: object-ontological and org-activity" [V GP-SMD; GP1983; GP1987]. Subject-object talk ("what must I do?") is legitimate on the org-activity board and gives a false scheme on the ontology board.
- **Program:** three boards: org-activity (ОД), object (ОО), situation (С, small and big).
- **Engine:**
  - `oo` is read as the object-ontological board, which answers the open question of what "ОО" stands for.
  - The situation board is the program's addition. In the classic texts situational analysis is work in the thought-communication belt, which turns into "analysis of situations" once schemes appear [V GP1987].
  - New check (warning): subject-object formulations such as "we must", "our task" on `oo` belong on `od`.
  - The two layouts are profiles: `classic-two-boards` and `program-three-boards` (the default); a record names its profile (`docs/data-model.md`, Profiles; the format in `docs/profiles.md`).

## 2. Positions, the cow example and ontology

- Representations from different positions are "not checked for truth against each other, because they are simply different". An ontological representation is valid only for the chosen set of positions [V GP1981].
- One common object is built through the activities, and only when they cooperate [V GP1981].
- A subject (предмет) is an organisation of means, knowledge, methods and problems, not a point of view [V GP-OP].
- **For the cow example:** four positions give four object representations; one cow exists only as a construction for their cooperation, e.g. a farm-to-table chain.
- **For Khaprov:** his "wrong ontology dooms you" and the classic "methodological products are checked for realizability, not truth" [V GP1981] do not conflict. Realizability is tested in activity: Nokia's ontology failed the test of the market. Engine: an ontology record carries the set of positions it is valid for and a realizability test (field hypothesis), not a truth flag.
- **Engine:** `seen_from` is kept. Step 3 adds `represents` (position to object representation) and a `cooperation` element that builds the common object. A common object without a cooperation is a hint.

## 3. Problematization and gaps

- **Classic procedure [V GP-PP]:**
  1. Make a reflexive exit.
  2. Take a named structural-functional scheme. For a task: product, initial material, means, method.
  3. Mark each block plus or minus.
  4. The minuses are "knowledge about ignorance".
  5. Convert them to goals and themes.
- Empty places are visible only in a functional structure [V GP-PP]. This is the reason behind the organisers' K3: without a functional plan the big situation "does not unfold".
- A problem is not a question, an error or a difficulty. A paradox of two justified, opposite statements is a problem [V GP-Guide9].
- **Engine:**
  - A `gap` must name the scheme block it is missing from (`gap.of`: product, material, means, method, function, position).
  - The validator hint "gap without a scheme" applies.
  - Step 3 gets a problematization procedure with plus/minus marking.
  - The difficulty / task / problem distinction becomes a field on theses (step 2).

## 4. Reflexive exit and the spiral

- **Classic [V GP1975]:** activity fails. If a pattern exists, copy it. If not, leave the actor's position for a reflexive one, describe past activity, and project new activity from it.
- Reflection is "the result of a change of positions" [V PG2019, later author].
- **Engine:**
  - Each new cycle (`revises`) is recorded with the reflexive position it was made from (`reflected_from`, step 2).
  - The state line names what failed (difficulty) and what was projected.
  - This makes your spiral concrete: a cycle is a reflexive exit, not a time slice.

## 5. Belts of thought-activity

- **Classic:** three belts [V GP1987]:
  - мД, collective thought-action;
  - М-К, thought-communication: texts, not graded right or wrong;
  - М, pure thinking: schemes, ontological pictures.

  Degenerate forms are pure play with words, mechanical reproduction, and reflection of reflection.
- **Engine (step 2):**
  - Each thesis carries a belt.
  - The qualification pass flags degeneration:
    - a session with many М-К theses and no scheme (play with words);
    - schemes with no situation (М cut off from мД);
    - repeated reflection with no new scheme.

## 6. Game roles for solo sessions with AI positions

- **Classic:** four positions at the first game: game leader, methodologist, game technician, researcher; later only the leader and the game technician [V PG-GT].
- The game technician has three functions: work with the board and its content, with understanding and communication, and with reflection, including entry into and exit from the game [V PG-GT].
- **Engine roles (step 3):**
  - `игротехник`: runs the three functions and owns the state line.
  - `методолог`: qualification pass, problematization.
  - `визионер`: the program's position, with the tract and the structural moves.
  - Actor positions: owner, buyer, bank, state.
  - `исследователь` is optional, for the clean room.
- Every AI voice is labelled as such.
- **Self-determination questions** for a participant [V PG1987]:
  - What is fixed and what is a zone of search?
  - What does the program require and what is our initiative?
  - What must one do in this position?
  - What must I do?
  - What can I really do?

## 7. Terms that are the program's, not the classic method's

"Такт", "рамка" as a defined procedure and "онтологическая работа" as a procedure are [UNVERIFIED] in the classic texts. So is a fixed phase sequence for every game. The only documented phase list is ОДИ-1 (1979) [V GP1983].

The engine keeps them as program vocabulary. Their source is `mipt` (Girenko, Fliamer), not `classic`.

## 8. TRIZ and SMD on contradictions

- **SMD:** a paradox is resolved by changing one's means and concepts, a turn to the activity side [V GP-Guide9].
- **TRIZ:** the contradiction is resolved inside the object, by separation in space, time or system level, using available resources and the ideal final result [V ARIZ85V].
- **Engine:** a resolution records its route (`route: smd | triz`).
- What transfers from TRIZ to organisational problems [ANALYSIS]:
  - contradiction pairs and intensifying them;
  - operative zone and time;
  - the resource inventory;
  - the ideal final result with "no new elements";
  - the three separations;
  - the shift to the supersystem;
  - post-solution reflection.
- What does not transfer: the physical-effects index and the field standards.

## 9. Structural moves

The classic chain "schematize → idealize → ontologize → objectivate → realize" [V GP1987; GP-SMD] is where the structural moves act:
- **schematization:** glue, re-specify;
- **idealization:** adjoin a dimension, rescale.

Realization is the field test. This places doi:10.5281/zenodo.21653102 inside the classic chain, not beside it.

## Changes to the plan

| Step | Addition |
|---|---|
| 2 | Theses carry belt, voice and status, and the kind: difficulty, task, problem, question. A cycle records the reflexive position it was made from. |
| 3 | Problematization with plus/minus on a named scheme. Roles of game technician and methodologist. Self-determination questions. Subject-object check on `oo`. |
| 3 | Ontology records with the positions they are valid for and a realizability test. Cooperation element for a common object. |
| 4 | TRIZ lens with route labelling. Checkland's CATWOE only as a checklist on an activity act [S]. |
