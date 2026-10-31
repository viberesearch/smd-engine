"""`smd new`: a case folder that validates at once.

Three files: the first record of the case (cycle 1) on the chosen profile, a
source manifest with one entry to fill in, and a README naming the next steps.
Nothing is overwritten; the files are written as text, so the comments that
guide the first edit stay."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from smd_engine.nextstep import first_procedure
from smd_engine.profile import DEFAULT_PROFILE, Profile, load_profile
from smd_engine.records import schema_version

ID_CHARS = re.compile(r"[^a-z0-9._-]+")

# Words of the scaffold by language: the two elements, the manifest entry, the
# record's comments and the README.
TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "entry": "entry",
        "position": "the position the work starts from (rename it)",
        "source": "Notes for the first session (rename, or list your own files)",
        "boards": "boards of the profile",
        "templates": "record boards, made of the templates of the profile",
        "next_move": "run {procedure} on this record with your notes (see README.md)",
        "readme": """# {title}

A case folder made by `smd new` on the profile `{profile}`.

- `{board}`: the first record, cycle 1. It holds an entry and one position; rename the position and add what you know.
- `sources.yaml`: the manifest of what you bring. One entry, `s1`, points to `notes.txt`.

## Next steps

1. Save your notes as `notes.txt` in this folder, then fix their checksum:
   `smd sources sources.yaml --folder . --refresh s1`
2. Check the folder: `smd validate . --sources sources.yaml --hints`. The hints say what the boards still lack.
3. Draw it: `smd render {board} --lang {lang} -o out/screen.svg`
4. Run the first procedure. Which one depends on what you brought:
   - a transcript or notes of a session: `ingest-transcript`, then `theses-to-board`
     `smd pack ingest-transcript {board} --sources sources.yaml -o pack.md`
   - a solo session with no transcript: `{procedure}`: {why}
     `smd pack {procedure} {board} --sources sources.yaml -o pack.md`
   Attach `pack.md` and your notes to a model, or in Claude Code run `/procedure {procedure} <full path>/{board}`.
5. Ask the engine what comes next: `smd next {board}`; read the open work on one page: `smd status {board} --lang {lang}`.

The walkthrough is `docs/first-board.md` in the smd-engine repository; the terms are in `docs/glossary.md`.
""",
        "why_first": "it lays out the small situation, the positions and the first hypotheses from your answers to four questions.",
        "why_other": "the procedures written for the default profile do not run on this one, so the work starts from the positions.",
    },
    "ru": {
        "entry": "вход",
        "position": "позиция, с которой ведётся работа (переименуйте)",
        "source": "Заметки к первой сессии (переименуйте или укажите свои файлы)",
        "boards": "доски профиля",
        "templates": "доски записи, собираемые из шаблонов профиля",
        "next_move": "запустить {procedure} на этой записи с вашими заметками (README.md)",
        "readme": """# {title}

Папка дела, созданная `smd new` на профиле `{profile}`.

- `{board}`: первая запись, цикл 1. В ней вход и одна позиция; переименуйте позицию и добавьте то, что знаете.
- `sources.yaml`: реестр того, что вы приносите. Одна запись, `s1`, указывает на `notes.txt`.

## Следующие шаги

1. Сохраните заметки как `notes.txt` в этой папке и обновите контрольную сумму:
   `smd sources sources.yaml --folder . --refresh s1`
2. Проверьте папку: `smd validate . --sources sources.yaml --hints`. Подсказки говорят, чего ещё не хватает доскам.
3. Нарисуйте: `smd render {board} --lang {lang} -o out/screen.svg`
4. Запустите первую процедуру. Какую, зависит от того, что вы принесли:
   - стенограмму или заметки сессии: `ingest-transcript`, затем `theses-to-board`
     `smd pack ingest-transcript {board} --sources sources.yaml -o pack.md`
   - сессию в одиночку, без стенограммы: `{procedure}`: {why}
     `smd pack {procedure} {board} --sources sources.yaml -o pack.md`
   Приложите `pack.md` и заметки к модели; в Claude Code: `/procedure {procedure} <полный путь>/{board}`.
5. Что дальше, скажет `smd next {board}`; открытое одной страницей: `smd status {board} --lang {lang}`.

Пошаговый разбор: `docs/first-board.md` в репозитории smd-engine; термины: `docs/glossary.md`.
""",
        "why_first": "она раскладывает малую ситуацию, позиции и первые гипотезы по вашим ответам на четыре вопроса.",
        "why_other": "процедуры профиля по умолчанию здесь не работают, поэтому работа начинается с позиций.",
    },
}


class ScaffoldError(Exception):
    """The folder cannot be scaffolded as asked."""


def case_id(folder: Path) -> str:
    """An id of letters, digits, `.`, `_`, `-` from a folder name."""
    slug = ID_CHARS.sub("-", folder.resolve().name.lower()).strip("-._")
    if not slug:
        raise ScaffoldError(
            f"{folder}: no case id can be made of the folder name; give --case"
        )
    return slug


def _quote(text: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(text, ensure_ascii=False)


def _board_lines(profile: Profile, lang: str) -> list[str]:
    own = [b for b in profile.boards if not b.template]
    names = ", ".join(
        f"{b.id} ({b.label[lang]}"
        + (f"; {', '.join(b.halves)}" if b.halves else "")
        + ")"
        for b in own
    )
    return [f"# {TEXTS[lang]['boards']} {profile.id}: {names}"]


def record_text(
    profile: Profile, case: str, title: str, lang: str, procedure: str, today: str
) -> str:
    words = TEXTS[lang]
    home = profile.home_board["position"]
    elements = []
    if profile.has_kind("entry"):
        elements.append(
            f"  - {{id: entry, board: {home}, kind: entry, label: {_quote(words['entry'])}}}"
        )
    elements.append(
        f"  - {{id: p-start, board: {home}, kind: position, "
        f"label: {_quote(words['position'])}}}"
    )
    lines = [
        "record: board_set",
        f'schema_version: "{schema_version("board_set")}"',
        f"id: {case}-c1",
        f"case: {case}",
        f"title: {_quote(title)}",
        f"date: {_quote(today)}",
        "cycle: 1",
        "status: draft",
        f"profile: {profile.id}",
        "sources: [s1]",
    ]
    if profile.templates:
        names = ", ".join(t.id for t in profile.templates)
        lines += [f"# {words['templates']}: {names}", "boards: []"]
    lines += [*_board_lines(profile, lang), "elements:", *elements]
    lines += [f"{key}: []" for key in ("relations", "transitions", "qualifications")]
    lines += ["theses: []", "hypotheses: []"]
    lines += [
        "state:",
        '  version: "1.0"',
        "  accepted: []",
        "  open: []",
        f"  next_move: {_quote(words['next_move'].format(procedure=procedure))}",
    ]
    return "\n".join(lines) + "\n"


def manifest_text(case: str, lang: str) -> str:
    return (
        "\n".join(
            [
                "record: source_manifest",
                f'schema_version: "{schema_version("source_manifest")}"',
                f"case: {case}",
                "location: this folder",
                "sources:",
                "  - id: s1",
                f"    title: {_quote(TEXTS[lang]['source'])}",
                "    kind: team_doc",
                "    origin: team",
                "    file: notes.txt",
                "    clean_room: allow",
            ]
        )
        + "\n"
    )


def scaffold(
    folder: Path,
    profile_id: str = DEFAULT_PROFILE,
    lang: str = "ru",
    case: str | None = None,
    title: str | None = None,
    today: str | None = None,
) -> list[Path]:
    """Write the three files into the folder (made if missing); refuse, writing
    nothing, when one of them exists. Returns the paths written."""
    profile = load_profile(profile_id)  # ProfileError names the known ids
    case = case or case_id(folder)
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", case):
        raise ScaffoldError(
            f"case id '{case}': use lowercase letters, digits, '.', '_' and '-'"
        )
    title = title or case.replace("-", " ").replace("_", " ").capitalize()
    procedure = first_procedure(profile.id)
    board = f"{case}-c1.board.yaml"
    files = {
        folder
        / board: record_text(
            profile, case, title, lang, procedure, today or dt.date.today().isoformat()
        ),
        folder / "sources.yaml": manifest_text(case, lang),
        folder
        / "README.md": TEXTS[lang]["readme"].format(
            title=title,
            profile=profile.id,
            board=board,
            lang=lang,
            procedure=procedure,
            why=TEXTS[lang][
                "why_first" if profile.id == DEFAULT_PROFILE else "why_other"
            ],
        ),
    }
    taken = [str(p) for p in files if p.exists()]
    if taken:
        raise ScaffoldError("not overwriting: " + ", ".join(taken))
    folder.mkdir(parents=True, exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    return list(files)
