"""Text measurement, wrapping and interface labels for renderers.

Board and kind labels are profile data (profiles/*.yaml); LABELS holds the
engine's own strings."""

from __future__ import annotations

from typing import Any
from xml.sax.saxutils import escape

CHAR_WIDTH = 0.56  # average glyph width as a share of font size, Latin and Cyrillic
SCREEN_CHARS = 60  # a screen label longer than this is cut unless `short` is given

LABELS: dict[str, dict[str, Any]] = {
    "ru": {
        "small": "малая",
        "big": "большая",
        "cycle": "цикл",
        "transitions": "Переходы",
        "qualifications": "Квалификации",
        "lineage": "жёлтым — элементы с происхождением",
        "epistemic": "курсивом — гипотеза или не проверено",
        "state": "Состояние",
        "accepted": "принято",
        "open": "открыто",
        "next": "следующий ход",
        "status": {"open": "открыто", "partly": "частично", "closed": "закрыто"},
        "moves": "Структурные ходы",
        "more": "ещё на доске",
        "fillers": "кто может занять",
        "details": "Таблицы элементов",
        "relations": "Связи",
        "elements": "Элементы",
        "record_boards": "Доски записи",
        "columns": ["К", "статус", "текст", "кто", "источники"],
        "el_columns": ["id", "доска", "вид", "подпись", "источники"],
        "theses": "Тезисы",
        "signoffs": "Подписи",
        "hypotheses": "Гипотезы",
        "ontology": "Онтология",
        "valid_for": "для позиций",
        "o_columns": ["О", "объект", "для позиций", "кооперация", "проверка"],
        "difficulty": "что не получилось",
        "hyp_status": {
            "untested": "не проверено",
            "testing": "проверяем",
            "confirmed": "подтверждено",
            "refuted": "опровергнуто",
        },
        "th_columns": ["тезис", "адрес источника", "чей голос", "статус"],
        "h_columns": ["Г", "статус", "что предполагаем", "чем проверяем", "результат"],
        "s_columns": ["функция", "цель", "кто", "основания"],
        "index": {
            "suffix": "указатель",
            "file": "Файл записи",
            "hint": "«YAML:N» открывает строку в VS Code; ссылки на PDF открывают страницу.",
            "hint_relative": "«YAML:N» — номер строки в файле записи; "
            "ссылки на PDF открывают страницу.",
            "web": "сеть",
            "no_file": "локального файла нет",
            "no_entry": "нет в реестре",
            "k_columns": ["id", "статус", "текст", "цели", "заметка", "источники"],
            "t_columns": [
                "id",
                "голос, статус",
                "утверждение",
                "питает / о чём",
                "заметка",
                "источники",
            ],
            "h_columns": [
                "id",
                "статус",
                "что предполагаем",
                "чем проверяем",
                "что пересмотрим",
                "цели, К",
                "источники",
            ],
            "o_columns": [
                "id",
                "объект",
                "для позиций",
                "кооперация, проверка",
                "заметка",
                "источники",
            ],
            "s_columns": ["функция", "цель", "кто, когда", "заметка", "источники"],
            "e_columns": [
                "id",
                "доска",
                "вид",
                "экран",
                "полный текст",
                "исполнители",
                "источники",
            ],
            "b_columns": [
                "id",
                "шаблон",
                "доска",
                "с позиции",
                "развёртывает",
                "источники",
            ],
            "src_title": "Источники, на которые ссылается запись",
            "src_columns": ["id", "название", "где лежит"],
        },
        # SessionFlow frame 03, the six labels verbatim.
        "thesis_status": {
            "voiced": "Прозвучало в группе",
            "assumption": "Предположение участников",
            "proposal": "Предложение модератора / эксперта",
            "ai_variant": "Вариант формулировки от ИИ",
            "refined": "Уточнено группой после записи",
            "open": "Оставляем открытым",
        },
        # One per sign-off function of the board_set schema (tests check the enum).
        "signoff": {
            "close_k": "закрыть квалификацию",
            "partly_k": "частично закрыть квалификацию",
            "reopen_k": "вновь открыть квалификацию",
            "accept_move": "принять ход",
            "reject_move": "отклонить ход",
            "accept_thesis": "принять уточнение тезиса",
            "accept_result": "принять результат проверки",
            "verify_record": "запись сверена с источником",
        },
    },
    "en": {
        "small": "small",
        "big": "big",
        "cycle": "cycle",
        "transitions": "Transitions",
        "qualifications": "Qualifications",
        "lineage": "yellow: elements with a lineage tag",
        "epistemic": "italic: hypothesis or unverified",
        "state": "State",
        "accepted": "accepted",
        "open": "open",
        "next": "next move",
        "status": {"open": "open", "partly": "partly", "closed": "closed"},
        "moves": "Structural moves",
        "more": "more on this board",
        "fillers": "who can occupy",
        "details": "Element tables",
        "relations": "Relations",
        "elements": "Elements",
        "record_boards": "Record boards",
        "columns": ["K", "status", "text", "by", "cites"],
        "el_columns": ["id", "board", "kind", "label", "cites"],
        "theses": "Theses",
        "signoffs": "Sign-offs",
        "hypotheses": "Hypotheses",
        "ontology": "Ontology",
        "valid_for": "valid for",
        "o_columns": ["O", "object", "valid for", "cooperation", "test"],
        "difficulty": "what failed",
        "hyp_status": {
            "untested": "untested",
            "testing": "testing",
            "confirmed": "confirmed",
            "refuted": "refuted",
        },
        "th_columns": ["thesis", "source address", "voice", "status"],
        "h_columns": ["H", "status", "assumes", "test", "result"],
        "s_columns": ["function", "target", "by", "grounds"],
        "index": {
            "suffix": "index",
            "file": "Record file",
            "hint": '"YAML:N" opens the line in VS Code; PDF links open the page.',
            "hint_relative": '"YAML:N" is the line in the record file; '
            "PDF links open the page.",
            "web": "web",
            "no_file": "no local file",
            "no_entry": "not in the manifest",
            "k_columns": ["id", "status", "text", "targets", "note", "cites"],
            "t_columns": [
                "id",
                "voice, status",
                "claim",
                "feeds / about",
                "note",
                "cites",
            ],
            "h_columns": [
                "id",
                "status",
                "assumes",
                "test",
                "revise if",
                "targets, K",
                "cites",
            ],
            "o_columns": [
                "id",
                "object",
                "valid for",
                "cooperation, test",
                "note",
                "cites",
            ],
            "s_columns": ["function", "target", "by, date", "note", "cites"],
            "e_columns": [
                "id",
                "board",
                "kind",
                "screen",
                "full text",
                "fillers",
                "cites",
            ],
            "b_columns": ["id", "template", "board", "seen from", "unfolds", "cites"],
            "src_title": "Sources the record cites",
            "src_columns": ["id", "title", "where it is"],
        },
        "thesis_status": {
            "voiced": "voiced in the group",
            "assumption": "participants' assumption",
            "proposal": "moderator or expert proposal",
            "ai_variant": "AI wording variant",
            "refined": "refined by the group after the recording",
            "open": "left open",
        },
        "signoff": {
            "close_k": "close the qualification",
            "partly_k": "partly close the qualification",
            "reopen_k": "reopen the qualification",
            "accept_move": "accept the move",
            "reject_move": "reject the move",
            "accept_thesis": "accept the refined thesis",
            "accept_result": "accept the test result",
            "verify_record": "record checked against the source",
        },
    },
}

MOVE_NAMES = {
    "adjoin": "adjoin a dimension (α)",
    "rescale": "rescale (ρ)",
    "respecify": "re-specify (τ)",
    "glue": "glue across domains (γ)",
}


def title_line(data: dict[str, Any], lang: str = "ru") -> str:
    """The record's title and, when `state.version` is set, its cycle: `title · цикл 0.2`."""
    version = (data.get("state") or {}).get("version")
    if not version:
        return str(data["title"])
    return f"{data['title']} · {LABELS[lang]['cycle']} {version}"


def cut(text: str, limit: int = SCREEN_CHARS) -> str:
    """The text, or its first words up to `limit` characters and an ellipsis."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    head = text[: limit - 1]
    if " " in head:
        head = head[: head.rfind(" ")]
    return head.rstrip(" ,;:—-") + "…"


def screen_label(item: dict[str, Any], field: str = "label") -> str:
    """What the screen shows for an element (`label`) or a K (`text`): `short`
    when given, otherwise the full text, cut to SCREEN_CHARS."""
    return cut(str(item.get("short") or item[field]))


def text_width(text: str, size: float) -> float:
    return len(text) * size * CHAR_WIDTH


def wrap(text: str, max_width: float, size: float) -> list[str]:
    """Greedy word wrap by estimated width; long words are cut."""
    limit = max(4, int(max_width / (size * CHAR_WIDTH)))
    lines: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split():
            while len(word) > limit:
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:limit])
                word = word[limit:]
            candidate = f"{line} {word}".strip()
            if len(candidate) <= limit:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return [ln for ln in lines if ln] or [""]


def esc(text: str) -> str:
    return escape(text, {'"': "&quot;"})
