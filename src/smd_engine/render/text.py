"""Text measurement, wrapping and interface labels for renderers.

Board and kind labels are profile data (profiles/*.yaml); LABELS holds the
engine's own strings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from xml.sax.saxutils import escape

from smd_engine.verdict import rule_line

if TYPE_CHECKING:
    from smd_engine.profile import Profile

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
        "pace": "меняется за",
        # Field names of elements and records, one table for every renderer:
        # the page, the index and the frames put them before the value, the
        # graph and the vault before an `extra` entry, the digest on the line.
        "fields": {
            "pace": "темп изменения",
            "vsm_system": "системы (Бир)",
            "threshold": "порог",
            "recovery_time": "срок восстановления",
            "of_whole": "модель целого (Бир)",
            "written": "записана",
            "acts_as": "занимает место",
            "stance": "позиция",
            "lives_in": "живёт в",
            "tempos": "темпы",
            "horizon": "горизонт",
            "covers": "охватывает",
            "action": "чем проверяем",
            "observe": "что наблюдаем",
            "revise_if": "что пересмотрим",
            "competes": "что с чем конкурирует",
            "test": "проверяется гипотезой",
            "cooperation": "кооперация",
            "result": "результат",
            "changes": "что меняет на досках",
            "type": "тип гипотезы",
            "rule": "правило решения",
            "observed": "наблюдено",
            "basis": "основание порога",
        },
        # Words of the fixed values of a record, by field (value_word); a value
        # with no word here is shown as recorded.
        "values": {
            "acts_as": {
                "organiser": "организатор",
                "leader": "руководитель",
                "manager": "управляющий",
                "politician": "политик",
                "functionary": "функционер",
            },
            "stance": {
                "inside": "внутренняя",
                "reflexive": "рефлексивная",
                "external": "внешняя",
            },
            # who brought an element or a thesis in (`voice`)
            "voice": {
                "group": "группа",
                "participant": "участник",
                "moderator": "модератор",
                "expert": "эксперт",
                "organisers": "организаторы",
                "ai": "ИИ",
            },
            "epistemic": {
                "stated": "заявлено",
                "hypothesis": "гипотеза",
                "unverified": "не проверено",
                "checked": "проверено",
            },
            "frame_state": {"old": "старая", "new": "новая"},
            "move_status": {
                "candidate": "кандидат",
                "accepted": "принят",
                "rejected": "отклонён",
            },
            "record_status": {
                "draft": "черновик",
                "extracted": "извлечено",
                "verified": "сверено",
            },
            # a hypothesis's `type` (field-result.md §0.1)
            "hyp_type": {
                "core": "ядро программы",
                "product": "методологический продукт",
                "claim": "эмпирическое утверждение",
                "estimate": "оценка",
                "probe": "разведка",
                "design": "проектное решение",
            },
            # a thesis: its belt (GP1987) and its kind
            "belt": {"md": "мД", "mk": "М-К", "m": "М"},
            "thesis_kind": {
                "statement": "утверждение",
                "difficulty": "затруднение",
                "task": "задача",
                "problem": "проблема",
                "question": "вопрос",
            },
        },
        # words of the Markdown digest's element line
        "line": {
            "in": "в",
            "fillers": "кто может занять",
            "seen_from": "с позиции",
            "lineage": "происхождение",
            "move": "ход",
            "from": "из",
            "via": "через",
        },
        # other words of the Markdown digest; record fields (`action`,
        # `cooperation`, `test`, ...) take their labels from "fields"
        "digest": {
            "board_of": "доска по шаблону",
            "unfolds": "развёртывает",
            "revises": "пересматривает",
            "version": "версия",
        },
        # words of the core view (`smd status`, status.py)
        "core": {
            "open_k": "Открытые и частично закрытые K",
            "testing": "Гипотезы в проверке",
            "untested": "Непроверенные гипотезы по охвату (предложение; выбирает группа)",
            "reach": "охват",
            "waiting": "Ждут подписи человека",
            "w_variants": "варианты тезисов от ИИ",
            "w_moves": "ходы-кандидаты",
            "w_k": "K от ИИ",
            "w_h": "H от ИИ",
            "counts": "Счёт",
            "boards": "по доскам",
            "kinds": "по видам",
            "more": "и ещё {n}",
            "none": "нет",
            "verdicts": "Вердикт по правилу решения (предложение; подписывает группа)",
            "verdict": {
                "too_few": "мало случаев, остаётся в проверке",
                "refuted": "опровергнуто",
                "confirmed": "подтверждено",
                "inconclusive": "не решено, остаётся в проверке",
            },
            "no_share": "порог не доля строго между 0 и 1, предложения нет",
        },
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
                "охват (предложение)",
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
        "pace": "changes every",
        "fields": {
            "pace": "pace",
            "vsm_system": "systems (Beer)",
            "threshold": "threshold",
            "recovery_time": "recovery time",
            "of_whole": "model of the whole (Beer)",
            "written": "written down",
            "acts_as": "acts as",
            "stance": "stance",
            "lives_in": "lives in",
            "tempos": "tempos",
            "horizon": "horizon",
            "covers": "covers",
            "action": "test",
            "observe": "observe",
            "revise_if": "revise if",
            "competes": "competes",
            "test": "tested by hypothesis",
            "cooperation": "cooperation",
            "result": "result",
            "changes": "changes",
            "type": "type",
            "rule": "decision rule",
            "observed": "observed",
            "basis": "threshold basis",
        },
        "values": {
            "acts_as": {
                "organiser": "organiser",
                "leader": "leader",
                "manager": "manager",
                "politician": "politician",
                "functionary": "functionary",
            },
            "stance": {
                "inside": "inside",
                "reflexive": "reflexive",
                "external": "external",
            },
            "hyp_type": {
                "core": "core of the programme",
                "product": "methodological product",
                "claim": "empirical claim",
                "estimate": "estimate",
                "probe": "probe",
                "design": "design choice",
            },
            # the other fixed values (voice, epistemic status, move status,
            # ...) are shown by their ids on the English pages
        },
        "line": {
            "in": "in",
            "fillers": "fillers",
            "seen_from": "seen from",
            "lineage": "lineage",
            "move": "move",
            "from": "from",
            "via": "via",
        },
        # the English digest names `action` and `test` by the field names, as
        # it always has; the page labels them "test" and "tested by hypothesis"
        "digest": {
            "board_of": "board of",
            "unfolds": "unfolds",
            "revises": "revises",
            "version": "version",
            "action": "action",
            "test": "test",
        },
        # words of the core view (`smd status`, status.py)
        "core": {
            "open_k": "Open and partly answered K",
            "testing": "Hypotheses in testing",
            "untested": "Untested hypotheses by reach (a proposal; the group chooses)",
            "reach": "reach",
            "waiting": "Waiting for a human sign-off",
            "w_variants": "AI variants of theses",
            "w_moves": "candidate moves",
            "w_k": "K drafted by AI",
            "w_h": "H drafted by AI",
            "counts": "Counts",
            "boards": "by board",
            "kinds": "by kind",
            "more": "and {n} more",
            "none": "none",
            "verdicts": "Verdicts by the decision rule (a proposal; the group signs)",
            "verdict": {
                "too_few": "too few cases, stays testing",
                "refuted": "refuted",
                "confirmed": "confirmed",
                "inconclusive": "inconclusive, stays testing",
            },
            "no_share": "the threshold is not a share strictly between 0 and 1, no proposal",
        },
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
                "reach (proposal)",
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

# The Russian pages name the sign-off functions by the words of "signoff".
LABELS["ru"]["values"]["function"] = LABELS["ru"]["signoff"]
# The graph's details panel names the status of a thesis, a hypothesis and a K
# by the words the page and the index use, in both languages (gate Г8а В).
for _lang in ("ru", "en"):
    LABELS[_lang]["values"]["thesis_status"] = LABELS[_lang]["thesis_status"]
    LABELS[_lang]["values"]["hyp_status"] = LABELS[_lang]["hyp_status"]
    LABELS[_lang]["values"]["k_status"] = LABELS[_lang]["status"]

# Names of the structural moves (docs/method/structural-moves.md) by language.
MOVE_NAMES: dict[str, dict[str, str]] = {
    "ru": {
        "adjoin": "добавить измерение (α)",
        "rescale": "сменить масштаб (ρ)",
        "respecify": "переопределить связи (τ)",
        "glue": "склеить с другой областью (γ)",
    },
    "en": {
        "adjoin": "adjoin a dimension (α)",
        "rescale": "rescale (ρ)",
        "respecify": "re-specify (τ)",
        "glue": "glue across domains (γ)",
    },
}


def value_word(field: str, value: str, lang: str) -> str:
    """A fixed value of a record (`voice`, `epistemic`, `move.status` as
    `move_status`, the record's `status` as `record_status`, a thesis's `belt`
    and `kind` as `thesis_kind`, a sign-off's `function`, the `status` of a
    thesis, a hypothesis and a K as `thesis_status`, `hyp_status`, `k_status`)
    as its word in the language; a value the language has no word for is shown
    as recorded, as the English pages show the ids."""
    words: dict[str, str] = LABELS[lang]["values"].get(field, {})
    return words.get(value, value)


def rule_text(rule: dict[str, Any], lang: str) -> str:
    """A decision rule as `доля 55+ < 0.2, n >= 30 (основание порога: ...)`."""
    basis = rule.get("basis")
    words = LABELS[lang]["fields"]
    return rule_line(rule) + (f" ({words['basis']}: {basis})" if basis else "")


def observed_text(obs: dict[str, Any]) -> str:
    """What the field gave for the rule: `12/40 (s7)`."""
    return f"{obs['k']}/{obs['n']} ({obs['artefact']})"


def hypothesis_parts(h: dict[str, Any], lang: str) -> dict[str, str]:
    """The typed-standard fields of a hypothesis as plain text, by field:
    `type` as its word, `rule` and `observed`; fields it lacks are left out."""
    out: dict[str, str] = {}
    if "type" in h:
        out["type"] = value_word("hyp_type", h["type"], lang)
    if "rule" in h:
        out["rule"] = rule_text(h["rule"], lang)
    if "observed" in h:
        out["observed"] = observed_text(h["observed"])
    return out


def board_text(
    profile: Profile, el: dict[str, Any], lang: str, short: bool = False
) -> str:
    """The board an element stands on, by its label (by its short name with
    `short`), and its half in the language: `Ситуация / малая`."""
    half = el.get("half")
    name = profile.board_short if short else profile.board_label
    label = name(el["board"], lang)
    return label + (f" / {LABELS[lang][half]}" if half else "")


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


CONTINUUM = ("lives_in", "tempos", "horizon", "covers")


def years_text(n: float, lang: str) -> str:
    """A number of years with the word in its form: in Russian 1 год, 2 года,
    5 лет, 21 год, 2.5 года; in English 1 year, 5 years."""
    if lang != "ru":
        return f"{n:g} {'year' if n == 1 else 'years'}"
    if n != int(n):
        return f"{n:g} года"
    k = int(n)
    if k % 10 == 1 and k % 100 != 11:
        return f"{k} год"
    if 2 <= k % 10 <= 4 and not 12 <= k % 100 <= 14:
        return f"{k} года"
    return f"{k} лет"


def _ref(entry: dict[str, Any]) -> str:
    """An entry of `lives_in` or `tempos`: its element id, else its text."""
    return str(entry["id"] if "id" in entry else entry["text"])


def continuum_parts(o: dict[str, Any], lang: str = "en") -> dict[str, str]:
    """The continuum fields of an ontology record as plain text, by field:
    `lives_in` and `covers` joined by commas, `tempos` as "<what> <n years>",
    `horizon` as "<n years>"; fields the record lacks are left out."""
    out: dict[str, str] = {}
    if o.get("lives_in"):
        out["lives_in"] = ", ".join(_ref(x) for x in o["lives_in"])
    if o.get("tempos"):
        out["tempos"] = ", ".join(
            f"{_ref(t)} {years_text(t['years'], lang)}" for t in o["tempos"]
        )
    if "horizon" in o:
        out["horizon"] = years_text(o["horizon"], lang)
    if o.get("covers"):
        out["covers"] = ", ".join(o["covers"])
    return out


def field_lines(parts: dict[str, str], lang: str) -> list[str]:
    """Fields given as plain text by field name, as "<label>: <text>" with the
    labels of LABELS[lang]["fields"]."""
    words = LABELS[lang]["fields"]
    return [f"{words.get(k, k)}: {v}" for k, v in parts.items()]


def continuum_lines(o: dict[str, Any], lang: str) -> list[str]:
    """The continuum fields as "<label>: <text>", labels in the language."""
    return field_lines(continuum_parts(o, lang), lang)


def pace_text(el: dict[str, Any], lang: str) -> str:
    """An element's `pace` as "<label> <n years>", empty without it."""
    if "pace" not in el:
        return ""
    return f"{LABELS[lang]['pace']} {years_text(el['pace'], lang)}"


def days_text(n: float, lang: str) -> str:
    """A number of days with the word in its form: in Russian 1 день, 2 дня,
    5 дней, 21 день, 0.5 дня; in English 1 day, 5 days."""
    if lang != "ru":
        return f"{n:g} {'day' if n == 1 else 'days'}"
    if n != int(n):
        return f"{n:g} дня"
    k = int(n)
    if k % 10 == 1 and k % 100 != 11:
        return f"{k} день"
    if 2 <= k % 10 <= 4 and not 12 <= k % 100 <= 14:
        return f"{k} дня"
    return f"{k} дней"


def beer_parts(el: dict[str, Any], lang: str = "en") -> dict[str, str]:
    """The Beer fields of an element as plain text, by field: `vsm_system`
    joined by commas, `threshold` as written, `recovery_time` as "<n days>",
    `of_whole` and `written` as yes when true; fields the element lacks are
    left out."""
    out: dict[str, str] = {}
    if el.get("vsm_system"):
        out["vsm_system"] = ", ".join(str(n) for n in el["vsm_system"])
    if el.get("threshold"):
        out["threshold"] = str(el["threshold"])
    if "recovery_time" in el:
        out["recovery_time"] = days_text(el["recovery_time"], lang)
    if el.get("of_whole") is True:
        out["of_whole"] = "да" if lang == "ru" else "yes"
    if el.get("written") is True:
        out["written"] = "да" if lang == "ru" else "yes"
    return out


def element_parts(el: dict[str, Any], lang: str = "en") -> dict[str, str]:
    """The fields of an element that the renderers show beside its label, as
    plain text by field: `pace` as "<n years>", the Beer fields (beer_parts),
    `acts_as` and `stance` as their words in the language; fields the element
    lacks are left out."""
    out: dict[str, str] = {}
    if "pace" in el:
        out["pace"] = years_text(el["pace"], lang)
    out |= beer_parts(el, lang)
    values = LABELS[lang]["values"]
    for key in ("acts_as", "stance"):
        if el.get(key):
            out[key] = values[key].get(el[key], str(el[key]))
    return out


def element_lines(el: dict[str, Any], lang: str) -> list[str]:
    """The fields of element_parts but `pace` as "<label>: <text>"; the page,
    the index and the frames write `pace` by pace_text."""
    parts = element_parts(el, lang)
    parts.pop("pace", None)
    return field_lines(parts, lang)
