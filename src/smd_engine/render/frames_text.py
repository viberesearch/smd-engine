"""Texts of the frames: step titles, notes headings, switch names, in ru and en."""

from __future__ import annotations

from typing import Any

STEPS: dict[str, dict[str, Any]] = {
    "ru": {
        "entry": ("Вход", "С чего началось мышление группы."),
        "positions": (
            "Позиции",
            "Откуда группа смотрит и куда сдвигается: позиции и цели.",
        ),
        "places": (
            "Места для других",
            "Кто ещё участвует в деятельности и чего не хватает.",
        ),
        "small": (
            "Малая ситуация",
            "Что группа видит вокруг себя из своей позиции.",
        ),
        "big": (
            "Большая ситуация",
            "Границы нормальности, сигналы, серии связанных событий, визионеры.",
        ),
        "old-frame": ("Старая рамка", "То, что уже есть: старая рамка и её функции."),
        "new-frame": (
            "Новая рамка",
            "Новый объект: рамка и её функциональный план.",
        ),
        "object": (
            "Объектная доска",
            "Понятия, модели, стандарты и кооперации вокруг рамок.",
        ),
        "transitions": ("Переходы", "Переходы между досками в порядке хода мысли."),
        "k": ("Квалификации", "Замечания, на которые группа отвечает."),
        "full": ("Экран целиком", "Все доски, переходы и квалификации вместе."),
        "cycle": ("Цикл", "Новое в этом цикле"),
        "removed": "Снято",
        "hidden": "Не на экране (есть в записи и в таблицах)",
        "next": "Следующий ход",
        "notes_title": "Тексты кадров",
        "prev": "Назад",
        "next_btn": "Вперёд",
        "toggle": "Текст",
        "switches": {
            "ai": "ИИ",
            "clean-room": "Чистая комната",
            "function": "Функции",
            "places": "Места и разрывы",
            "k": "К",
            "transitions": "Переходы",
        },
        "hidden_n": "скрыто",
        "close": "Закрыть",
    },
    "en": {
        "entry": ("Entry", "Where the group's thinking started."),
        "positions": (
            "Positions",
            "Where the group looks from and where it shifts to: positions and goals.",
        ),
        "places": (
            "Places for others",
            "Who else takes part in the activity, and what is missing.",
        ),
        "small": (
            "Small situation",
            "What the group sees around it from its own position.",
        ),
        "big": (
            "Big situation",
            "Boundaries of normality, signals, series of linked events, visionaries.",
        ),
        "old-frame": ("Old frame", "What exists: the old frame and its functions."),
        "new-frame": (
            "New frame",
            "The new object: the frame and its functional plan.",
        ),
        "object": (
            "Object board",
            "Concepts, models, standards and cooperations around the frames.",
        ),
        "transitions": ("Transitions", "Transitions between boards, in order."),
        "k": ("Qualifications", "Remarks the group answers."),
        "full": ("Full screen", "All boards, transitions and qualifications together."),
        "cycle": ("Cycle", "New in this cycle"),
        "removed": "Removed",
        "hidden": "Not on the screen (in the record and the tables)",
        "next": "Next move",
        "notes_title": "Frame texts",
        "prev": "Back",
        "next_btn": "Next",
        "toggle": "Text",
        "switches": {
            "ai": "AI",
            "clean-room": "Clean room",
            "function": "Functions",
            "places": "Places and gaps",
            "k": "K",
            "transitions": "Transitions",
        },
        "hidden_n": "hidden",
        "close": "Close",
    },
}
