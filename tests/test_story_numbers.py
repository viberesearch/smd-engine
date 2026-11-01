from __future__ import annotations

from fractions import Fraction

import pytest

from smd_engine.story.numbers import date_matches, dates_in, has_number, numbers_in


@pytest.mark.parametrize(
    "text,expected",
    [
        ("три года", [3]),
        ("трёх лет и трех месяцев", [3, 3]),
        ("вдвое больше", [2]),
        ("вчетверо", [4]),
        ("половина смен", [Fraction(1, 2)]),
        ("треть и четверть", [Fraction(1, 3), Fraction(1, 4)]),
        ("полтора года", [Fraction(3, 2)]),
        ("двадцать пять", [25]),
        ("сто двадцать", [120]),
        ("сто двадцать пять смен", [125]),
        ("двадцать один", [21]),
        ("сто пятнадцать", [115]),
        ("двадцать пять тысяч", [25_000]),
        ("две тысячи двадцать пять", [2025]),
        ("пять шесть смен", [5, 6]),
        ("десять пять", [10, 5]),
        ("двадцать, пять", [20, 5]),
        ("двадцать. Пять смен", [20, 5]),
        ("двадцать тридцать", [20, 30]),
        ("оба партнёра", [2]),
        ("дважды и трижды", [2, 3]),
        ("4,2 млрд", [4_200_000_000]),
        ("0,95 млн евро", [950_000]),
        ("три тысячи", [3000]),
        ("тысячи клиентов", [1000]),
        ("4 200 000", [4_200_000]),
        ("18 до 25 %", [18, 25]),
        ("35.9%", [Fraction(359, 10)]),
        ("2026-08-03", []),
        ("3.08.2026", []),
        ("3 по 17 августа 2026 года, 14 дней", [14]),
        ("в марте 2026", []),
        ("9 в июне", [9]),
        ("в 2029 году 100 человек", [2029, 100]),
        ("twice as many", [2]),
        ("two hundred", [2, 100]),
        ("half of them", [Fraction(1, 2)]),
        ("1,3 раза", [Fraction(13, 10)]),
    ],
)
def test_numbers_read_as_values(text: str, expected: list[int | Fraction]) -> None:
    assert numbers_in(text) == [Fraction(x) for x in expected]


@pytest.mark.parametrize(
    "text",
    [
        "H12a и K1",
        "один из вариантов",
        "первый шаг, второй шаг",
        "пара недель",
        "несколько смен",
        "семью и друзей",
        "третья сторона",
        "one of them",
    ],
)
def test_words_that_are_not_numbers(text: str) -> None:
    assert numbers_in(text) == []
    assert not has_number(text)


def test_digits_and_words_are_one_number() -> None:
    assert numbers_in("три") == numbers_in("3") == numbers_in("трёх")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2026-08-03", [(2026, 8, 3)]),
        ("3.08.2026", [(2026, 8, 3)]),
        ("30 июня", [(None, 6, 30)]),
        ("30 июня и 30 сентября 2026 года", [(None, 6, 30), (2026, 9, 30)]),
        ("с 3 по 17 августа 2026", [(2026, 8, 3), (2026, 8, 17)]),
        ("в марте 2026 года", [(2026, 3, None)]),
        ("9 в июне", []),
        ("2026-13-45", []),
    ],
)
def test_dates_are_read_whole(
    text: str, expected: list[tuple[int | None, ...]]
) -> None:
    assert dates_in(text) == expected
    assert has_number(text) == bool(expected or numbers_in(text))


def test_a_date_of_a_sentence_matches_a_whole_date_only() -> None:
    known = (2026, 6, 30)
    assert date_matches((None, 6, 30), known)
    assert date_matches((2026, 6, 30), known)
    assert date_matches((2026, 6, None), known)
    assert not date_matches((None, 6, 9), known)
    assert not date_matches((2025, 6, 30), known)
    assert not date_matches((2026, 6, 30), (None, 6, 30))
