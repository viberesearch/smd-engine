"""A story as readable Markdown (`smd story render`): the title, the audience
and form, the sentences by part with the board ids each rests on in brackets,
the open questions and the stamp. A view of a view: nothing here checks the
story (`smd story check`) or writes a board."""

from __future__ import annotations

from typing import Any

from smd_engine.story.model import Boards

LABELS: dict[str, dict[str, Any]] = {
    "ru": {
        "audience": "Для",
        "protagonist": "О ком",
        "form": "Форма",
        "open": "Открытые вопросы",
        "stamp": "Штамп",
        "boards": "доски",
        "draft": "Черновик ИИ, не подписан. Это вид карты, а не запись: при "
        "изменении карты текст пишется заново.",
        "parts": {
            "situation": "Ситуация",
            "complication": "Осложнение",
            "question": "Вопрос",
            "answer": "Ответ",
            "failure": "Провал",
            "cause": "Причины",
            "early_signal": "Ранние признаки",
        },
        "other": "Прочее",
    },
    "en": {
        "audience": "For",
        "protagonist": "About",
        "form": "Form",
        "open": "Open questions",
        "stamp": "Stamp",
        "boards": "boards",
        "draft": "Draft by an AI, not signed. It is a view of the map, not a "
        "record: when the map changes the text is written again.",
        "parts": {
            "situation": "Situation",
            "complication": "Complication",
            "question": "Question",
            "answer": "Answer",
            "failure": "Failure",
            "cause": "Causes",
            "early_signal": "Early signals",
        },
        "other": "Other",
    },
}


def _name(boards: Boards | None, item: str) -> str:
    if boards is None or item not in boards.items:
        return item
    return f"{boards.label(item)} [{item}]"


def render_story_md(
    story: dict[str, Any], boards: Boards | None = None, lang: str = "ru"
) -> str:
    """The story as Markdown. With the boards at hand an open question shows
    what the hypothesis assumes, and the audience its label."""
    t = LABELS[lang]
    out = [f"# {story.get('title', story['id'])}", ""]
    out.append(f"- {t['audience']}: {_name(boards, story['audience'])}")
    if story["protagonist"] != story["audience"]:
        out.append(f"- {t['protagonist']}: {_name(boards, story['protagonist'])}")
    out.append(f"- {t['form']}: {story['form']}")
    out += ["", t["draft"], ""]
    parts: dict[str, list[dict[str, Any]]] = {}
    for sentence in story["sentences"]:
        parts.setdefault(sentence.get("part", ""), []).append(sentence)
    for part, sentences in parts.items():
        out += [f"## {t['parts'].get(part, part or t['other'])}", ""]
        for s in sentences:
            out += [f"{s['text']} [{', '.join(s['ids'])}]", ""]
    if story["open"]:
        out += [f"## {t['open']}", ""]
        for item in story["open"]:
            out.append(f"- [{item}] {_open_text(boards, item)}".rstrip())
        out.append("")
    stamp = "; ".join(
        f"{b['id']}, {b['version']}, sha256 {b['sha256'][:12]}" for b in story["boards"]
    )
    run = story.get("run", {})
    made = ", ".join(str(run[k]) for k in ("procedure", "model", "date") if k in run)
    out.append(
        f"{t['stamp']}: {t['boards']} {stamp}; voice: {story['voice']}"
        + (f"; {made}" if made else "")
    )
    return "\n".join(out) + "\n"


def _open_text(boards: Boards | None, item: str) -> str:
    if boards is None or item not in boards.items:
        return ""
    return str(boards.items[item][1].get("assumes") or boards.label(item))
