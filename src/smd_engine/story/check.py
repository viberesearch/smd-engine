"""Rules a written story must keep (`smd story check`).

| Rule | What it checks | Kind |
|---|---|---|
| G1 | each sentence has at least one id, and every id exists | error |
| G2 | the declared level is not above the weakest of the sentence's ids | error; modal words for a human to read | hint |
| G3 | every number in a sentence is in the text of one of its ids, every date is a whole date of one | error |
| G4 | the ids of a sentence are in the curated `allow` list | error |
| G5 | no `opposes` that touches the path is left out of `conflict` | error |
| G6 | a comparative or superlative with no number in the sentence | hint |
| G7 | voice ai; the stamp of each board matches the board file | error |

S1-S4 check the structure the rules lean on: ids exist, neighbours on the path
are joined by a link, conflict and resolution lie on the path, the path has 4 to 9
items and meets a conflict object before a resolution object."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from jsonschema import Draft202012Validator

from smd_engine.records import load_schema
from smd_engine.story.model import LEVELS, Boards
from smd_engine.story.numbers import Date, date_matches, has_number, parse
from smd_engine.story.paths import MAX_LEN, MIN_LEN
from smd_engine.validate.context import AI_VOICES, Finding

# Numbers the form itself introduces: the premortem looks back from three
# years on, scenarios come in twos (A and B).
FORM_CONSTANTS: dict[str, set[Fraction]] = {
    "scqa": set(),
    "premortem": {Fraction(3)},
    "scenarios": {Fraction(2)},
}

# Words that make a sentence a supposition, a duty or a question (G2).
MODAL = (
    r"если|возможн\w+|вероятно|может|могут|мог|могла|могли|можно|должен|должна|"
    r"должно|должны|нужно|надо|оцени\w+|оценк\w+|предполага\w+|предлага\w+|предположим|"
    r"представим|гипотез\w+|проверим|проверить|проверя(?:ем|ется|ют)|вопрос\w*|"
    r"ли|пока не|пока что|похоже|кажется|видимо|скорее|допустим|предположительно|"
    r"ожида\w+|планиру\w+|бы|"
    r"if|may|might|could|should|would|likely|possibly|perhaps|hypothes\w+|"
    r"assum\w+|expect\w+|question\w*|suppose|imagine"
)
MODAL_RX = re.compile(rf"(?<!\w)(?:{MODAL})(?!\w)", re.IGNORECASE)
# Comparatives and superlatives (G6).
COMPARATIVE = (
    r"больше|меньше|выше|ниже|лучше|хуже|быстрее|медленнее|дешевле|дороже|чаще|"
    r"реже|крупнее|мельче|сильнее|слабее|легче|труднее|проще|сложнее|шире|уже(?=,?\s+чем)|"
    r"дольше|короче|длиннее|более|менее|наиболее|наименее|самый|самая|самое|"
    r"самые|самого|самой|самым|самыми|наибольш\w+|наименьш\w+|лучш\w+|худш\w+|"
    r"\w+ейш\w+|"
    r"more|less|better|worse|higher|lower|faster|slower|cheaper|larger|smaller|"
    r"stronger|weaker|easier|harder|longer|shorter|most|least|best|worst|"
    r"greater|biggest|largest|smallest"
)
COMPARATIVE_RX = re.compile(rf"(?<!\w)(?:{COMPARATIVE})(?!\w)", re.IGNORECASE)


def _err(rule: str, where: str, message: str) -> Finding:
    return Finding("error", f"{rule} {where}", message)


def _hint(rule: str, where: str, message: str) -> Finding:
    return Finding("hint", f"{rule} {where}", message)


def check_story(story: dict[str, Any], boards: Boards) -> list[Finding]:
    """All findings for a story against the boards it was made from. A story
    that fails the schema gets those errors only."""
    validator = Draft202012Validator(
        load_schema("story"), format_checker=Draft202012Validator.FORMAT_CHECKER
    )
    schema = [
        Finding("error", "/".join(str(p) for p in e.path) or "(root)", e.message)
        for e in sorted(validator.iter_errors(story), key=lambda e: list(e.path))
    ]
    if schema:
        return schema
    out = _stamps(story, boards)
    out += _structure(story, boards)
    out += _g5(story, boards)
    for n, sentence in enumerate(story["sentences"], 1):
        out += _sentence(story, boards, n, sentence)
    return out


def _stamps(story: dict[str, Any], boards: Boards) -> list[Finding]:
    """G7: a story is written by an AI, for one version of each board."""
    out: list[Finding] = []
    if str(story["voice"]).strip().lower() not in AI_VOICES:
        out.append(_err("G7", "voice", "a story is voice: ai and is never signed"))
    have = {s["id"]: s for s in boards.stamps}
    for stamp in story["boards"]:
        board = have.get(stamp["id"])
        if board is None:
            out.append(
                _err("G7", stamp["id"], "board set not given (--boards): regenerate")
            )
            continue
        for field in ("version", "sha256"):
            if board[field] != stamp[field]:
                out.append(
                    _err(
                        "G7",
                        stamp["id"],
                        f"{field} of the board is {board[field][:12]}, the story "
                        f"has {stamp[field][:12]}: regenerate the story",
                    )
                )
    named = {s["id"] for s in story["boards"]}
    out += [
        _err("G7", sid, "board set given but not in the story's stamp")
        for sid in have
        if sid not in named
    ]
    return out


def _structure(story: dict[str, Any], boards: Boards) -> list[Finding]:
    """S1-S3: ids, links between neighbours, conflict and resolution."""
    out: list[Finding] = []
    elements = boards.elements
    for field in ("audience", "protagonist"):
        if story[field] not in elements:
            out.append(_err("S1", field, f"unknown element '{story[field]}'"))
    for field in ("path", "conflict", "resolution", "allow", "open"):
        for item in story[field]:
            known = (
                item in boards.items if field in ("allow", "open") else item in elements
            )
            if not known:
                out.append(_err("S1", field, f"unknown id '{item}'"))
    for item in story["open"]:
        family = boards.items.get(item, ("", {}))[0]
        if family and family != "hypothesis":
            out.append(_err("S1", "open", f"'{item}' is not a hypothesis"))
    if any(i not in elements for i in story["path"]):
        return out
    joined: dict[frozenset[str], bool] = {}
    for link in boards.links:
        pair = frozenset((link.a, link.b))
        joined[pair] = joined.get(pair, True) and link.weak
    path = story["path"]
    for a, b in zip(path, path[1:]):
        weak = joined.get(frozenset((a, b)))
        if weak is None:
            out.append(_err("S2", f"{a} - {b}", "no link on the boards joins them"))
        elif weak:
            out.append(
                Finding(
                    "warning", f"S2 {a} - {b}", "only a weak link (refers) joins them"
                )
            )
    on_path = set(path)
    partners = {
        e
        for link in boards.links
        if link.kind == "opposes" and {link.a, link.b} & on_path
        for e in (link.a, link.b)
    }
    for item in story["conflict"]:
        if item in elements and item not in on_path and item not in partners:
            out.append(
                _err(
                    "S3",
                    "conflict",
                    f"'{item}' is neither on the path nor opposed to it",
                )
            )
    for item in story["resolution"]:
        if item in elements and item not in on_path:
            out.append(_err("S3", "resolution", f"'{item}' is not on the path"))
    if not story["resolution"]:
        out.append(
            Finding(
                "warning",
                "S3 resolution",
                "empty: the board has no resolution here, and a sentence must say so",
            )
        )
    return out + _s4(story)


def _s4(story: dict[str, Any]) -> list[Finding]:
    """S4: a path of 4 to 9 items, with a conflict object on it and no
    resolution object before the first one."""
    path = story["path"]
    out: list[Finding] = []
    if not MIN_LEN <= len(path) <= MAX_LEN:
        out.append(
            _err("S4", "path", f"{len(path)} items; a path has {MIN_LEN} to {MAX_LEN}")
        )
    first = next((n for n, i in enumerate(path) if i in story["conflict"]), None)
    if first is None:
        out.append(_err("S4", "path", "no conflict object on the path"))
    else:
        early = [i for i in story["resolution"] if i in path[:first]]
        if early:
            out.append(
                _err(
                    "S4",
                    "path",
                    f"resolution '{early[0]}' comes before the first conflict "
                    f"object '{path[first]}'",
                )
            )
    return out


def _g5(story: dict[str, Any], boards: Boards) -> list[Finding]:
    """G5: an opposition that touches the path stays in the conflict."""
    out: list[Finding] = []
    on_path = set(story["path"])
    for link in boards.links:
        if link.kind != "opposes" or not {link.a, link.b} & on_path:
            continue
        for end in (link.a, link.b):
            if end not in story["conflict"]:
                out.append(
                    _err(
                        "G5",
                        f"{link.a} opposes {link.b}",
                        f"touches the path but '{end}' is not in conflict",
                    )
                )
    return out


def _sentence(
    story: dict[str, Any], boards: Boards, n: int, sentence: dict[str, Any]
) -> list[Finding]:
    where = f"sentence {n}"
    text, ids = sentence["text"], sentence["ids"]
    out: list[Finding] = []
    if not ids:
        return [_err("G1", where, "no id: a sentence rests on at least one board id")]
    unknown = [i for i in ids if i not in boards.items]
    out += [_err("G1", where, f"unknown id '{i}'") for i in unknown]
    known = [i for i in ids if i in boards.items]
    out += [
        _err("G4", where, f"'{i}' is not in allow")
        for i in known
        if i not in story["allow"]
    ]
    if known:
        out += _g2(boards, where, sentence, known)
        out += _g3(boards, story["form"], where, text, known)
    out += _hints(where, sentence)
    return out


def _g2(
    boards: Boards, where: str, sentence: dict[str, Any], ids: list[str]
) -> list[Finding]:
    """The sentence is never stronger than its weakest id."""
    weakest = min(ids, key=lambda i: LEVELS.index(boards.level(i)))
    cap = boards.level(weakest)
    if LEVELS.index(sentence["level"]) > LEVELS.index(cap):
        return [
            _err(
                "G2",
                where,
                f"declares {sentence['level']}, but '{weakest}' is only {cap}",
            )
        ]
    return []


def _g3(
    boards: Boards, form: str, where: str, text: str, ids: list[str]
) -> list[Finding]:
    """Every number of the sentence is in the text of one of its ids, and every
    date is a whole date of one of them. A bare year is met by the year of a
    date."""
    allowed = set(FORM_CONSTANTS[form])
    known: set[Date] = set()
    for i in ids:
        allowed |= boards.numbers(i)
        known |= boards.date_facts(i)
    years = {y for y, _, _ in known if y is not None}
    numbers, dates = parse(text)
    missing = [
        f"number {_show(x)}"
        for x in numbers
        if x not in allowed and not (x.denominator == 1 and int(x) in years)
    ]
    missing += [
        f"date {_show_date(d)}"
        for d in dates
        if not any(date_matches(d, k) for k in known)
    ]
    return [
        _err("G3", where, f"{x} is in none of: {', '.join(ids)}")
        for x in dict.fromkeys(missing)
    ]


def _show_date(d: Date) -> str:
    year, month, day = d
    return "-".join(
        f"{n:0{w}d}" if n is not None else "?"
        for n, w in ((year, 4), (month, 2), (day, 2))
    )


def _show(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{float(x):g}"


def _hints(where: str, sentence: dict[str, Any]) -> list[Finding]:
    """G2 modal words to read by eye; G6 comparatives with no number."""
    text, level = sentence["text"], sentence["level"]
    out: list[Finding] = []
    modal = [m.group(0) for m in MODAL_RX.finditer(text)]
    if modal and level in ("stated", "checked"):
        out.append(
            _hint(
                "G2",
                where,
                f"modal words {', '.join(dict.fromkeys(modal))} in a sentence that "
                f"declares {level}: does the wording match the level?",
            )
        )
    elif not modal and level in ("hypothesis", "unverified"):
        out.append(
            _hint(
                "G2",
                where,
                f"declares {level} but has no modal word: is it worded as a fact?",
            )
        )
    if not has_number(text):
        found = [m.group(0) for m in COMPARATIVE_RX.finditer(text)]
        if found:
            out.append(
                _hint(
                    "G6",
                    where,
                    f"comparative or superlative with no number: "
                    f"{', '.join(dict.fromkeys(found))}",
                )
            )
    return out
