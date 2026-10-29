---
id: three-positions
title: Three positions, inside, reflexive and external
version: 0.1.0
source: "G.P. Shchedrovitsky, «Путеводитель по методологии организации, руководства и управления» (М.: Дело, 2003; lectures of 1981), section 11 «Программа действий» ¶35-36, ¶46-47 (GP-Guide11, https://gtmarket.ru/library/basis/3344/3356; the same text in «Из архива Г.П. Щедровицкого», т. 4, М., 2000, pp. 116-117), section 10 ¶10 (GP-Guide10), section 8 ¶8-10 (GP-Guide8); checked against т. 5, «Организация, руководство, управление (2)» (lectures of 1988; GP-T5), pp. 150-151, 240. Paragraphs are counted on the gtmarket pages, headings included"
route: smd
offered_by: [reflexive-protocol, positional-construction]
---

# Three positions: inside, reflexive, external

A lens that asks from where a scheme on the boards is drawn. G.P. works "на соединении трёх позиций": the inside position, where I am a place in a structure; the reflexive position, from which I describe what I did; and the external position, from which, "если у меня есть соответствующий язык", I draw the scheme of the object I was inside before. The lens gives no answers. It gives the human questions whose answers set `stance` on positions, `reflected_from` on the next cycle, and the position the object board is seen from.

Marks: **[V]** read in the primary text cited; **[ANALYSIS]** the engine's reading, not a claim of the source.

## What the source gives

- Three positions [V GP-Guide11 ¶35]: "Эти три позиции — очень значимая вещь. Вся наша дальнейшая работа будет идти по этой схеме."
- A structure one works inside is not an object [V GP-Guide11 ¶36]: "Когда я работаю внутри структуры, эта структура для меня объектом не является, она является условием моего действия."
- The same three steps for the activity approach [V GP-Guide11 ¶46-47]: a breakdown (прокол), the reflexive position, then "особую позицию, собственно мыслительную", where the boundaries of the object are drawn.
- A structure is rebuilt "не в этой структуре, а вне её" [V GP-Guide10 ¶10].
- The руководитель exists four ways: the place, its filling, a person without a place, and a reflexive position "со звёздочкой" [V GP-Guide8 ¶8-10].
- In 1988 the same order without the three-position wording [V GP-T5 p. 150]: at a dead end (тупик) one goes out into the reflexive position, describes the work, then constructs what is not yet there as an ideal object. The scheme "является результатом рефлексивного анализа того, что есть" [V GP-T5 p. 240]. Lectures 4-6 of т. 5 do not name three positions; nothing there contradicts the 1981 text.

## When to use

- In `reflexive-protocol`, section 2, with the fourth question (from which external position is the object scheme of the next cycle drawn, and in what language). The lens is the longer form of that question.
- In `positional-construction`, section 2 (the positional set) and section 4 (representations per position), when a position draws the object it works inside, or when the human cannot say from where the object board is seen.
- Not in `ingest-transcript` or `field-result`, which only read talk and artefacts, and not as a ranking: the three positions are steps of one human's work, not three people.

## Questions

1. **Inside.** In which structure do I act now, and what place do I hold in it? Who else holds places in it?
2. **Conditions.** Which of those structures do I keep as conditions of my action, not as objects? Which one do I want to change, and so must step out of?
3. **Breakdown.** What broke (прокол, тупик), so that acting from the place no longer worked? If nothing broke, a known pattern covers the next step and no exit is needed (GP1975).
4. **Reflexive.** From where do I describe what I did and how I did it? What did I take as given that I now see as a choice?
5. **External.** What is the object now, seen from outside the structure I was in? In what language, that is, with which scheme or notions, do I draw it?
6. **Boundaries.** Where do the boundaries of that object run, and what stays outside it as a condition?

## Output slots

| Answer | Element kind | Board | Field |
|---|---|---|---|
| Q1: the place held | `position` | `od` | `stance: inside`; the structure in `label`; `acts_as` when the place is an organiser, leader, manager or politician |
| Q2: structures kept as conditions | thesis (`kind: statement`, `about` the inside position) | | they are not drawn on the object board from the inside position; `object-from-inside` flags one that is |
| Q3: what broke | `state.difficulty`; or a thesis with `kind: difficulty` | | a goal set at the breakdown names it in `arises_from` |
| Q4: the reflexive position | `position` | `od` | `stance: reflexive`; the next cycle's `reflected_from` (`reflexive-protocol`, section 2) |
| Q5: the external position and its language | `position` | `od` | `stance: external`; the language in `label_note`; object-board elements take it as `seen_from` |
| Q6: the object's boundaries | `frame` (or the profile's frame kind) | the object board | `seen_from` the external position |

Every element and thesis carries `lens: three-positions`. Wording the model writes is `voice: ai`, `epistemic: hypothesis`.

The validator reads the slots [ANALYSIS]: an object-board element seen from a position with `stance: inside` gets the hint `object-from-inside`; a revising cycle drawn from an `external` position with no `reflected_from` gets `external-without-reflection`; a `reflected_from` position with `stance: inside` is a warning.

## Limits

- `reflected_from` must be an element of kind `position`. In the classic profile a `reflexive_position` element can carry `stance` but cannot be `reflected_from`; the lens writes the reflexive position as a `position` with `stance: reflexive`.
- The record has no field for the language of the external position; `label_note` keeps it as text [ANALYSIS].
- The sequence "breakdown, reflexive, external" is G.P.'s order for one exit. The lens does not check that the three positions were taken in that order within a session; only the record's fields are checked.
- Paragraph numbers follow the gtmarket pages of the 2003 хрестоматия; the т. 4 and т. 5 pages are the book pages.
