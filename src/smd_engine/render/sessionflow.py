"""SessionFlow export: "Наша малая ситуация. Материал к сообщению".

The headings follow SessionFlow frame 03 (section 6) verbatim; the export is
always Russian. It lays out what the record holds and leaves the group's own
text empty: the material is a draft for discussion until the group decides
("черновик к обсуждению"). Empty blocks say "в записи не приведено".

What the first three questions draw on is the `sessionflow` block of the
record's profile; a profile without one (classic-two-boards) has no export.
"""

from __future__ import annotations

from typing import Any

from smd_engine.profile import ProfileError, matches, profile_of
from smd_engine.render.text import LABELS, hypothesis_parts, value_word
from smd_engine.verdict import detail_text, of_hypothesis, verdict_line

EMPTY = "в записи не приведено"
MAX_MOVES = 3  # SessionFlow, station Б: at most three moves per iteration


def _cite(c: str) -> str:
    sid, _, addr = c.partition("#")
    if addr.startswith("t="):
        return f"{sid}, {addr[2:]}"
    if addr.startswith("p="):
        return f"{sid}, с. {addr[2:]}"
    if addr.startswith("u="):
        return f"{sid}, реплика {addr[2:]}"
    return c


def _cites(item: dict[str, Any]) -> str:
    cites = item.get("cites") or item.get("artefacts") or []
    return f" [{'; '.join(_cite(c) for c in cites)}]" if cites else ""


def _marks(el: dict[str, Any]) -> str:
    marks = []
    if el.get("epistemic") == "hypothesis":
        marks.append("гипотеза")
    if el.get("epistemic") == "unverified":
        marks.append("не проверено")
    if (el.get("voice") or "").strip().lower() in ("ai", "ии"):
        marks.append("вариант формулировки от ИИ")
    return f" ({', '.join(marks)})" if marks else ""


def _item(el: dict[str, Any]) -> str:
    return f"- {el['label']}{_marks(el)}{_cites(el)}"


def _typed(h: dict[str, Any]) -> list[str]:
    """The typed standard of a hypothesis, one nested line each: its `type`, its
    decision `rule`, what was `observed`, and for a testing one
    the verdict the rule proposes (verdict.py; the group signs the result)."""
    words, core = LABELS["ru"]["fields"], LABELS["ru"]["core"]
    parts = hypothesis_parts(h, "ru")
    out = [
        f"  - {words[key]}: {parts[key]}"
        for key in ("type", "rule", "observed")
        if key in parts
    ]
    obs = h.get("observed")
    if h.get("rule") and obs and obs["k"] <= obs["n"] and h["status"] == "testing":
        v = of_hypothesis(h)
        said = (
            f"{verdict_line(v)}: {core['verdict'][v.outcome]}"
            + "".join(f"; {x}" for x in [detail_text(v, "ru")] if x)
            if v
            else core["no_share"]
        )
        head = core["verdicts"]
        out.append(f"  - {head[:1].lower()}{head[1:]}: {said}")
    return out


def _block(title: str, items: list[str]) -> list[str]:
    return [f"### {title}", ""] + (items or [f"- {EMPTY}"]) + [""]


def render_sessionflow(data: dict[str, Any], lang: str = "ru") -> str:
    profile = profile_of(data)
    if profile.sessionflow is None:
        raise ProfileError(
            "the SessionFlow export needs a profile with a sessionflow block "
            f"(program-three-boards); {data['id']} follows {profile.id}"
        )
    blocks = profile.sessionflow
    els = data["elements"]
    by_id = {e["id"]: e for e in els}
    state = data.get("state", {})

    def block(name: str) -> list[str]:
        """The profile's picks for a block, each in record order."""
        out: list[str] = []
        for pick in blocks.get(name, ()):
            for e in els:
                if not matches(e, pick):
                    continue
                if e["kind"] != "function":
                    out.append(_item(e))
                    continue
                who = by_id.get(e.get("performed_by", ""), {}).get("label")
                prefix = f"{who}: " if who else "исполнитель не назван: "
                out.append(f"- {prefix}{e['label']}{_marks(e)}{_cites(e)}")
        return out

    out = ["# Наша малая ситуация. Материал к сообщению", ""]
    out += ["## Тема, группа, источник и версия", ""]
    out.append(f"- Тема: {data['title']}")
    if data.get("case"):
        out.append(f"- Кейс: {data['case']}")
    if data.get("sources"):
        out.append(f"- Источники: {', '.join(data['sources'])}")
    version = f"версия {state['version']}, " if state.get("version") else ""
    revises = f", пересматривает {data['revises']}" if data.get("revises") else ""
    out.append(f"- Версия: {version}цикл {data['cycle']}{revises}")
    status = "черновик к обсуждению"
    if data["status"] == "verified":
        status += f"; запись сверена с источником ({data.get('checked_by', '')})"
    out += [f"- Статус: {status}", ""]

    out += [
        "## Как пройти этот материал",
        "",
        "Раздел 1 собирает то, что уже есть в записи, по четырём вопросам. Раздел 2 — "
        "что доработать сейчас, с местом для ответа группы. Раздел 3 — заготовка "
        "сообщения, текст пишет группа. Адреса источников и история — в приложении.",
        "",
    ]

    hyps = []
    for h in data.get("hypotheses", []):
        test = h.get("action") or "способ проверки пока не определен"
        status_h = LABELS["ru"]["hyp_status"][h["status"]]
        line = f"- {h['assumes']} — проверяем: {test} ({status_h})"
        if h.get("revise_if"):
            line += f"; пересмотрим, если: {h['revise_if']}"
        hyps.append(line + _cites(h))
        hyps += _typed(h)
    out += ["## 1. Что уже можно сказать о нашей ситуации", ""]
    out += _block("Кто мы? Что мы делаем?", block("who"))
    out += _block("Где мы? В какой системе деятельности наша позиция?", block("where"))
    out += _block(
        "Для чего мы там? В чем наша устойчивость и ценность для этой системы?",
        block("what_for"),
    )
    out += _block(
        "На что опирается наша деятельность? Какие гипотезы мы сейчас проверяем?",
        hyps,
    )

    open_k = [
        q for q in data.get("qualifications", []) if q["status"] in ("open", "partly")
    ]
    out += ["## 2. Что сейчас доработать", ""]
    if not open_k:
        out += [f"- {EMPTY}", ""]
    for q in open_k[:MAX_MOVES]:
        have = "; ".join(by_id[t]["label"] for t in q.get("targets", []) if t in by_id)
        out += [
            f"### {q['id']}",
            "",
            f"- Что уже есть: {have or EMPTY}",
            f"- Где не сходится: {q['text']}{_cites(q)}",
            "- Что сделать сейчас: …",
            "- Что вписать: …",
            "- Как это войдет в сообщение: …",
            "",
        ]
    if len(open_k) > MAX_MOVES:
        rest = ", ".join(q["id"] for q in open_k[MAX_MOVES:])
        out += [f"Остальные открытые квалификации ({rest}) — к следующей итерации.", ""]

    out += [
        "## 3. Заготовка нашего сообщения",
        "",
        "Ход: наша деятельность → место среди других → функция и устойчивость → "
        "основания и проверяемые предположения. Опоры для каждой части — в разделе 1; "
        "текст пишет группа.",
        "",
    ]
    for part in (
        "Наша деятельность",
        "Место среди других",
        "Функция и устойчивость",
        "Основания и проверяемые предположения",
    ):
        out += [f"### {part}", "", "…", ""]

    out += [
        "## 4. Перед предъявлением",
        "",
        "Один читает, другой восстанавливает: кто действует, что кому передаётся, "
        "зачем и на что это опирается.",
        "",
    ]

    out += ["## 5. С чем переходим к следующему такту", ""]
    nxt = []
    if state.get("next_move"):
        nxt.append(f"- {state['next_move']}")
    nxt += [f"- открыто: {item}" for item in state.get("open", [])]
    out += (nxt or [f"- {EMPTY}"]) + [""]

    out += ["## Приложение. Откуда взята сборка", ""]
    theses = data.get("theses", [])
    if theses:
        out += [
            "### Тезисы",
            "",
            "| тезис | адрес источника | чей голос | статус |",
            "|---|---|---|---|",
        ]
        for t in theses:
            addr = "; ".join(_cite(c) for c in t.get("cites", [])) or "—"
            status_t = LABELS["ru"]["thesis_status"][t["status"]]
            claim = t["claim"].replace("|", "/")
            out.append(
                f"| {t['id']}. {claim} | {addr} | {value_word('voice', t['voice'], 'ru')} | {status_t} |"
            )
        out.append("")
        proposals = [t for t in theses if t["status"] == "proposal"]
        if proposals:
            out += ["### Предложения модератора и экспертов", ""]
            out += [f"- {t['id']}. {t['claim']} — решение группы: …" for t in proposals]
            out.append("")
    out += ["### История", ""]
    out.append(f"- цикл {data['cycle']}{revises}")
    if data.get("reflected_from") in by_id:
        out.append(f"- рефлексивная позиция: {by_id[data['reflected_from']]['label']}")
    if state.get("difficulty"):
        out.append(f"- что не получилось: {state['difficulty']}")
    for s in data.get("signoffs", []):
        target = f" {s['target']}" if s.get("target") else ""
        signoff = LABELS["ru"]["signoff"][s["function"]]
        out.append(f"- {signoff}{target}: {s['by']}")
    out.append("")
    return "\n".join(out)
