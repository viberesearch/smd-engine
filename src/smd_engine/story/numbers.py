"""Numbers in a sentence, as values: digits, Russian and English number words.

A story sentence may not hold a number that none of its ids holds (rule G3). The
sentence and the ids are read by the same function, so «три», "3" and «3»
are one number, and so are «вдвое» and "twice", or «4,2 млрд» and «4 200 млн».
A decimal spelled in words is not parsed. Russian number words that follow one
another are summed («двадцать пять» is 25, «две тысячи двадцать пять» 2025).

Dates are not numbers. A date in a text (ISO, dotted, «3 по 17 августа 2026»,
«30 июня», «в марте 2026») is read as a whole date, a (year, month, day) triple
with None for what the text does not say, and its parts are never loose numbers.
A date in a sentence matches only a whole date of an id's text.

Not numbers here: ordinals («первый», "third"), the indefinite «один» and "one"
(they mean "a" far more often than 1, but «двадцать один» is 21), «пара» and
vague quantities («несколько»)."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

# Whole words, oblique cases spelled out. ё is read as е.
_RU_UNITS = {
    "ноль": 0,
    "нуль": 0,
    "ноля": 0,
    "нуля": 0,
    "два": 2,
    "две": 2,
    "двух": 2,
    "двум": 2,
    "двумя": 2,
    "двое": 2,
    "двоих": 2,
    "оба": 2,
    "обе": 2,
    "обоих": 2,
    "обоим": 2,
    "три": 3,
    "трех": 3,
    "трем": 3,
    "тремя": 3,
    "трое": 3,
    "троих": 3,
    "четыре": 4,
    "четырех": 4,
    "четырем": 4,
    "четырьмя": 4,
    "четверо": 4,
    "пять": 5,
    "пяти": 5,
    "пятью": 5,
    "шесть": 6,
    "шести": 6,
    "шестью": 6,
    "семь": 7,
    "семи": 7,
    "восемь": 8,
    "восьми": 8,
    "восемью": 8,
    "девять": 9,
    "девяти": 9,
    "девятью": 9,
    "десять": 10,
    "десяти": 10,
    "десятью": 10,
    "одиннадцать": 11,
    "одиннадцати": 11,
    "двенадцать": 12,
    "двенадцати": 12,
    "тринадцать": 13,
    "тринадцати": 13,
    "четырнадцать": 14,
    "четырнадцати": 14,
    "пятнадцать": 15,
    "пятнадцати": 15,
    "шестнадцать": 16,
    "шестнадцати": 16,
    "семнадцать": 17,
    "семнадцати": 17,
    "восемнадцать": 18,
    "восемнадцати": 18,
    "девятнадцать": 19,
    "девятнадцати": 19,
    "двадцать": 20,
    "двадцати": 20,
    "тридцать": 30,
    "тридцати": 30,
    "сорок": 40,
    "сорока": 40,
    "пятьдесят": 50,
    "пятидесяти": 50,
    "шестьдесят": 60,
    "шестидесяти": 60,
    "семьдесят": 70,
    "семидесяти": 70,
    "восемьдесят": 80,
    "восьмидесяти": 80,
    "девяносто": 90,
    "девяноста": 90,
    "сто": 100,
    "ста": 100,
    "двести": 200,
    "двухсот": 200,
    "триста": 300,
    "трехсот": 300,
    "четыреста": 400,
    "четырехсот": 400,
    "пятьсот": 500,
    "пятисот": 500,
    "шестьсот": 600,
    "шестисот": 600,
    "семьсот": 700,
    "семисот": 700,
    "восемьсот": 800,
    "восьмисот": 800,
    "девятьсот": 900,
    "девятисот": 900,
}
# Multipliers and fractions: the value is what the word stands for.
_RU_OTHER = {
    "вдвое": 2,
    "втрое": 3,
    "вчетверо": 4,
    "впятеро": 5,
    "вдесятеро": 10,
    "дважды": 2,
    "трижды": 3,
    "четырежды": 4,
    "вдвоем": 2,
    "втроем": 3,
    "вчетвером": 4,
    "половина": Fraction(1, 2),
    "половины": Fraction(1, 2),
    "половину": Fraction(1, 2),
    "половиной": Fraction(1, 2),
    "половине": Fraction(1, 2),
    "пополам": Fraction(1, 2),
    "полтора": Fraction(3, 2),
    "полторы": Fraction(3, 2),
    "полутора": Fraction(3, 2),
    "треть": Fraction(1, 3),
    "трети": Fraction(1, 3),
    "третью": Fraction(1, 3),
    "четверть": Fraction(1, 4),
    "четверти": Fraction(1, 4),
}
_EN = {
    "zero": 0,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
    "twice": 2,
    "thrice": 3,
    "double": 2,
    "triple": 3,
    "half": Fraction(1, 2),
    "dozen": 12,
}
# What a number word stands for on its own.
_ALL: list[dict[str, Any]] = [_RU_UNITS, _RU_OTHER, _EN]
WORDS: dict[str, Fraction] = {w: Fraction(v) for d in _ALL for w, v in d.items()}
# A scale multiplies the number before it; alone it stands for its own size.
SCALES: dict[str, int] = {
    **{w: 1000 for w in ("тысяча", "тысячи", "тысяч", "тысячу", "тыс", "thousand")},
    **{w: 10**6 for w in ("миллион", "миллиона", "миллионов", "млн", "million", "mln")},
    **{
        w: 10**9
        for w in ("миллиард", "миллиарда", "миллиардов", "млрд", "billion", "bn")
    },
}


Date = tuple[int | None, int | None, int | None]

_MONTH_FORMS = {
    1: "январь января январе january",
    2: "февраль февраля феврале february",
    3: "март марта марте march",
    4: "апрель апреля апреле april",
    5: "май мая мае may",
    6: "июнь июня июне june",
    7: "июль июля июле july",
    8: "август августа августе august",
    9: "сентябрь сентября сентябре september",
    10: "октябрь октября октябре october",
    11: "ноябрь ноября ноябре november",
    12: "декабрь декабря декабре december",
}
MONTHS: dict[str, int] = {w: n for n, ws in _MONTH_FORMS.items() for w in ws.split()}
_MONTH = (
    "(?P<month>" + "|".join(sorted(MONTHS, key=len, reverse=True)) + ")(?![a-zа-я])"
)

_DATE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_DATE_DOT = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)")
# «3 по 17 августа 2026», «30 июня», «5 и 7 мая»
_DATE_DAY = re.compile(
    r"(?<![\d.,])(?P<d1>\d{1,2})(?:\s*(?:по|и|до|[-–—]|to)\s*(?P<d2>\d{1,2}))?"
    rf"\s+{_MONTH}(?:\s+(?P<year>\d{{4}})(?!\d))?"
)
# «в марте 2026»
_DATE_MONTH = re.compile(rf"(?<![a-zа-я]){_MONTH}\s+(?P<year>\d{{4}})(?!\d)")
_TOKEN = re.compile(
    r"(?<!\w)(?P<digits>\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"(?!\w)|(?P<word>[a-zа-я]+)"
)

# Russian number words that add up: hundreds, then tens or teens, then units.
_RU_ADD = {w: v for w, v in _RU_UNITS.items() if v > 0}
# «один» is not a number alone, but «двадцать один» is 21.
_RU_ONE = {w: 1 for w in ("один", "одна", "одно", "одну", "одного", "одной", "одним")}
_RU_JOIN = {**_RU_ADD, **_RU_ONE}


SCALED = 4


def _class(value: int) -> int:
    """3 hundreds, 2 tens, 1 teens, 0 units."""
    return 3 if value >= 100 else 2 if value >= 20 else 1 if value >= 10 else 0


def _adds(last: int, value: int) -> bool:
    """Whether a Russian number word of `value` goes on a run whose last word
    is of class `last` (SCALED after a scale word): a lower place each time
    (100, 20, 5), teens only after hundreds or a scale."""
    if last < 2 or _class(value) >= last:
        return False
    return not (_class(value) == 1 and last == 2)


def _valid(month: int, day: int | None) -> bool:
    return 1 <= month <= 12 and (day is None or 1 <= day <= 31)


def _plain(text: str) -> str:
    """Lower case, ё as е."""
    return text.lower().replace("ё", "е")


def _take_dates(text: str) -> tuple[str, list[Date]]:
    """The dates of a plain text, and the text with each date blanked."""
    dates: list[Date] = []

    def blank(m: re.Match[str]) -> str:
        return " " * len(m[0])

    def iso(m: re.Match[str]) -> str:
        if not _valid(int(m[2]), int(m[3])):
            return m[0]
        dates.append((int(m[1]), int(m[2]), int(m[3])))
        return blank(m)

    def dot(m: re.Match[str]) -> str:
        if not _valid(int(m[2]), int(m[1])):
            return m[0]
        dates.append((int(m[3]), int(m[2]), int(m[1])))
        return blank(m)

    def day(m: re.Match[str]) -> str:
        month = MONTHS[m["month"]]
        days = [int(x) for x in (m["d1"], m["d2"]) if x]
        if not all(_valid(month, d) for d in days):
            return m[0]
        year = int(m["year"]) if m["year"] else None
        dates.extend((year, month, d) for d in days)
        return blank(m)

    def month(m: re.Match[str]) -> str:
        dates.append((int(m["year"]), MONTHS[m["month"]], None))
        return blank(m)

    for rx, fn in (
        (_DATE_ISO, iso),
        (_DATE_DOT, dot),
        (_DATE_DAY, day),
        (_DATE_MONTH, month),
    ):
        text = rx.sub(fn, text)
    return text, dates


def _value(digits: str) -> Fraction:
    cleaned = re.sub(r"[   ]", "", digits).replace(",", ".")
    return Fraction(cleaned)


def parse(text: str) -> tuple[list[Fraction], list[Date]]:
    """The loose numbers a text holds, in order, as exact values (digits with a
    decimal point or comma, spaced thousands, number words, a number before a
    scale word multiplied by it, a run of Russian number words summed), and
    the whole dates it holds."""
    plain, dates = _take_dates(_plain(text))
    found: list[Fraction] = []
    previous_is_number = False
    # class of the last word of the run of Russian number words that ends the
    # list, or None when the last token is not one
    run: int | None = None
    ended = 0
    for m in _TOKEN.finditer(plain):
        adjacent = not plain[ended : m.start()].strip()
        ended = m.end()
        if m["digits"] is not None:
            found.append(_value(m["digits"]))
            previous_is_number, run = True, None
            continue
        word = m["word"]
        if word in SCALES:
            if previous_is_number:
                found[-1] *= SCALES[word]
            else:
                found.append(Fraction(SCALES[word]))
            previous_is_number, run = False, SCALED
        elif word in _RU_JOIN and adjacent and run and _adds(run, _RU_JOIN[word]):
            found[-1] += _RU_JOIN[word]
            previous_is_number, run = True, _class(_RU_JOIN[word])
        elif word in WORDS:
            found.append(WORDS[word])
            previous_is_number = True
            run = _class(_RU_ADD[word]) if word in _RU_ADD else None
        else:
            previous_is_number, run = False, None
    return found, dates


def numbers_in(text: str) -> list[Fraction]:
    """The loose numbers of a text: all numbers except the parts of dates."""
    return parse(text)[0]


def dates_in(text: str) -> list[Date]:
    """The whole dates of a text, as (year, month, day) with None for a part the
    text does not give."""
    return parse(text)[1]


def date_matches(sentence: Date, known: Date) -> bool:
    """Every part a date of a sentence gives is the same part of a date of an
    id: «30 июня» matches 2026-06-30, «30 июня 2026» does not match a date with
    no year."""
    return all(a is None or a == b for a, b in zip(sentence, known))


def has_number(text: str) -> bool:
    numbers, dates = parse(text)
    return bool(numbers or dates)
