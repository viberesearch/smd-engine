"""Hints of G.P.'s management scheme, the profile `management-four-boards`
(gate Ш13 В as amended by Ш15 В).

Unlike the hints of hints.py, these name the kinds and relation kinds of that
profile; each hint registers the ids it names (`hint(..., kinds, relations)`),
so a profile that enables it must define them. The boards are found by the
home of a kind, not by id: the upper system is where `ideal_state` lives, the
managed system where `monosystem` lives.

Sources: GP-T5 (т. 5, lectures of 1988) wins over GP-T4 / GP-Guide (1981) and
GP1975a where they disagree. The 1981 hint `manage-without-forecast`
(GP-Guide5 ¶7, «Управлять без прогноза в принципе невозможно») is replaced by
`manage-without-knowledge`: in 1988 forecasting is «форма подмены принципов
оргуправленческой работы сциентистскими принципами» (GP-T5 p. 251).

The Beer layer of the profile (gate Бир3 В) adds three hints from Stafford
Beer, «Мозг фирмы» (BEER1972, cited by chapter): `single-node-metasystem`,
`line-without-recovery` and `absorbed-into-system-1`. They read the field
`vsm_system` (Beer's systems 1-5) of posts and positions, the kind
`algedonic_channel` with `threshold` and `recovery_time` (a stakeholder's red
line is recorded as one), and the relations `escalates` and `captures`.
Gate Г2 В adds `no-model-of-whole` and `model-of-whole-one-filler`: they read
the field `of_whole` of models (the firm's model of itself and its
environment, kept by system 4, Гл. 13) and the relation `uses` from the post
or position that holds such a model.
"""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, hint

KNOWLEDGE = {
    "knowledge_retro": "retrospective",
    "knowledge_projective": "projective",
}
UPPER_KIND = "ideal_state"  # its home is the upper (ОРУ) system
MANAGED_KIND = "monosystem"  # its home is the managed polysystem
MONO_RELATIONS = ("parasitic", "symbiotic", "mechanism_of")  # GP-T5 p. 208
# Beer layer: systems 3, 4 and 5 (Приложение: systems 2-5 form the metasystem;
# system 2 is mostly informal, Гл. 12, so the check asks for 3-5), the kind of a
# red line, and the places an escalation may address.
METASYSTEM = frozenset({3, 4, 5})
CHANNEL = "algedonic_channel"
ADDRESSES = ("post", "position", "place_for_others")

# Gate Ш10 В revised by Ш15 Б: the kinds a position's representation is
# expected among, by `acts_as`. The table is the engine's reading of GP-T5;
# G.P. gives no table. A functionary takes no object (GP-Guide10 ¶7).
FIT: dict[str, tuple[tuple[str, ...], str]] = {
    "organiser": (
        ("post", "functional_place", "mission", "monosystem"),
        "for G.P. организация is constructing an institution from the elements "
        "at hand, people among them: first its mission, then the processes "
        "under it (GP-T5 pp. 175, 213, 242)",
    ),
    # Not `group`: руководство runs only in the administrative structure (p. 254),
    # and the informal group lies outside it (pp. 224-225).
    "leader": (
        ("post",),
        "for G.P. «руководят не люди, а места»: руководство holds the functioning "
        "of places (GP-T5 pp. 242, 244), and its subject is people's live "
        "activity and thinking, not technology (p. 223)",
    ),
    "manager": (
        ("work_process", "trajectory", "self_motion"),
        "for G.P. the working process is the object of управление, and a managed "
        "object has self-motion (GP-T5 pp. 170, 244)",
    ),
    "politician": (
        ("club", "position"),
        "for G.P. politics is done in the club, apart from the administrative "
        "structure, and is built over управление (GP-T5 pp. 253-254)",
    ),
    "functionary": ((), "for G.P. a functionary takes no object (GP-Guide10 ¶7)"),
}


def _rels(ctx: Ctx, kind: str) -> list[dict[str, Any]]:
    return [r for r in ctx.record.get("relations", []) if r["kind"] == kind]


def _where(rel: dict[str, Any]) -> str:
    return f"relation {rel['from']}->{rel['to']}"


def _kind(ctx: Ctx, eid: str) -> str | None:
    return ctx.by_id.get(eid, {}).get("kind")


def _linked(ctx: Ctx, eid: str) -> set[str]:
    """Ids linked to an element by a relation of any kind, either way."""
    out: set[str] = set()
    for r in ctx.record.get("relations", []):
        if eid in (r["from"], r["to"]):
            out |= {r["from"], r["to"]} - {eid}
    return out


def _content(ctx: Ctx, board: str | None) -> list[dict[str, Any]]:
    return [
        e
        for e in ctx.by_id.values()
        if e["board"] == board and e["kind"] not in ("gap", "note")
    ]


def _belonging(ctx: Ctx, eid: str) -> set[str]:
    """An element and what `belongs` to it: a post and the positions filling it."""
    return {eid} | {r["from"] for r in _rels(ctx, "belongs") if r["to"] == eid}


def _posts(ctx: Ctx, eid: str) -> set[str]:
    """The places of an element: itself if a post, or the posts it belongs to."""
    if _kind(ctx, eid) == "post":
        return {eid}
    return {
        r["to"]
        for r in _rels(ctx, "belongs")
        if r["from"] == eid and _kind(ctx, r["to"]) == "post"
    }


@hint("lead-vs-manage", kinds=("goal",), relations=("leads", "belongs"))
def hint_lead_vs_manage(ctx: Ctx) -> list[Finding]:
    """Руководство assumes no own goals below; own goals call for управление."""
    out: list[Finding] = []
    for rel in _rels(ctx, "leads"):
        people = _belonging(ctx, rel["to"])
        own = sorted(
            e["id"]
            for e in ctx.by_id.values()
            if e["kind"] == "goal"
            and e.get("goal_source") == "own"
            and e.get("seen_from") in people
        )
        if own:
            out.append(
                Finding(
                    "hint",
                    _where(rel),
                    f"'{rel['to']}' is led, yet has goals of its own ("
                    + ", ".join(own)
                    + "): management, not leadership? Руководство assumes the "
                    "subordinate has no goals of its own (GP-T5 pp. 169-170; "
                    "GP1975a p. 429)",
                )
            )
    return out


@hint("manage-via-organizedness", relations=("manages", "produces", "uses"))
def hint_manage_via_organizedness(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for rel in _rels(ctx, "manages"):
        made = {r["to"] for r in _rels(ctx, "produces") if r["from"] == rel["from"]}
        used = {r["to"] for r in _rels(ctx, "uses") if r["from"] == rel["to"]}
        if not made & used:
            out.append(
                Finding(
                    "hint",
                    _where(rel),
                    f"managed through nothing: no element that '{rel['from']}' "
                    f"produces and '{rel['to']}' uses. For G.P. one manages through "
                    "organizednesses that then direct the processes (GP-T5 pp. "
                    "199, 222-223; GP-STS, IT p. 441)",
                )
            )
    return out


@hint("manage-without-knowledge", kinds=tuple(KNOWLEDGE), relations=("manages",))
def hint_manage_without_knowledge(ctx: Ctx) -> list[Finding]:
    """A manager with no retrospective or no projective knowledge (GP-T5 p. 241)."""
    out: list[Finding] = []
    for source in dict.fromkeys(r["from"] for r in _rels(ctx, "manages")):
        linked = _linked(ctx, source)
        has = {
            KNOWLEDGE[e["kind"]]
            for e in ctx.by_id.values()
            if e["kind"] in KNOWLEDGE
            and (e.get("seen_from") == source or e["id"] in linked)
        }
        missing = [d for d in KNOWLEDGE.values() if d not in has]
        if missing:
            out.append(
                Finding(
                    "hint",
                    source,
                    f"manages with no {' and no '.join(missing)} knowledge (seen "
                    "from it or linked to it): for G.P. a system of ОРУ manages "
                    "only when served by the organisation of knowledge, "
                    "retrospective and projective; without it «и организация, и "
                    "управление сводятся к руководству» (GP-T5 pp. 240-241)",
                )
            )
    return out


@hint(
    "leads-outside-organisation",
    kinds=("post",),
    relations=("leads", "subordinates", "belongs"),
)
def hint_leads_outside_organisation(ctx: Ctx) -> list[Finding]:
    """`leads` between places joined by a line of `subordinates`, which runs
    from the superior place to the subordinate one."""
    below: dict[str, set[str]] = {}
    for r in _rels(ctx, "subordinates"):
        below.setdefault(r["from"], set()).add(r["to"])

    def reaches(starts: set[str], ends: set[str]) -> bool:
        seen, stack = set(starts), list(starts)
        while stack:
            for nxt in below.get(stack.pop(), set()) - seen:
                seen.add(nxt)
                stack.append(nxt)
        return bool((seen - starts) & ends)

    out: list[Finding] = []
    for rel in _rels(ctx, "leads"):
        top, low = _posts(ctx, rel["from"]), _posts(ctx, rel["to"])
        placeless = [
            end for end, posts in ((rel["from"], top), (rel["to"], low)) if not posts
        ]
        if placeless:
            message = (
                "holds no place (a post, or `belongs` to one): "
                + ", ".join(placeless)
                + ". For G.P. «руководят не люди, а места» (GP-T5 p. 242)"
            )
        elif top & low:
            message = (
                f"'{rel['from']}' and '{rel['to']}' hold the same place: руководство "
                "runs from one place to another (GP-T5 p. 242)"
            )
        elif not reaches(top, low):
            message = (
                f"no line of subordination from the place of '{rel['from']}' to "
                f"that of '{rel['to']}': руководство is possible only within the "
                "administrative structure (GP-T5 pp. 242, 254; GP-Guide4 ¶12)"
            )
        else:
            continue
        out.append(Finding("hint", _where(rel), message))
    return out


@hint(
    "representation-fit",
    kinds=tuple(sorted({k for kinds, _ in FIT.values() for k in kinds})),
    relations=("represents",),
)
def hint_representation_fit(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    for rel in _rels(ctx, "represents"):
        role = ctx.by_id.get(rel["from"], {}).get("acts_as")
        target = _kind(ctx, rel["to"])
        if role not in FIT or target is None or target in FIT[role][0]:
            continue
        expected = FIT[role][0]
        out.append(
            Finding(
                "hint",
                _where(rel),
                f"'{rel['from']}' acts as {role} and represents a {target}"
                + (f", not one of {', '.join(expected)}" if expected else "")
                + f": {FIT[role][1]}",
            )
        )
    return out


@hint(
    "development-step",
    kinds=(UPPER_KIND, MANAGED_KIND, "knowledge_retro"),
    relations=("captures",),
)
def hint_development_step(ctx: Ctx) -> list[Finding]:
    """«Шаг развития»: ОРУ in the present, the object's past, its ideal in the
    future; the upper part alone is not a management system."""
    home = ctx.profile.home_board
    upper, managed = home.get(UPPER_KIND), home.get(MANAGED_KIND)
    if not _content(ctx, upper):
        return []
    els = ctx.by_id.values()
    past = ctx.profile.kinds_where("factual") | {"knowledge_retro"}
    missing = []
    if not any(
        e["kind"] in past or (e["board"] == managed and e.get("modality") == "fact")
        for e in els
    ):
        missing.append("the object's past (facts, retrospective knowledge)")
    if not any(e["kind"] == UPPER_KIND for e in els):
        missing.append(f"its ideal in the future ({UPPER_KIND})")
    if not any(
        _board_of(ctx, r["from"]) == upper and _board_of(ctx, r["to"]) == managed
        for r in _rels(ctx, "captures")
    ):
        missing.append("the managed system it captures (captures)")
    if not missing:
        return []
    return [
        Finding(
            "hint",
            str(upper),
            "шаг развития incomplete: the ОРУ system, in the present, lacks "
            + "; ".join(missing)
            + ". For G.P. the scheme of ОРУ with the past and the future of its "
            "object «есть минимальная единица»: the upper part alone is not a "
            "management system (GP-T5 pp. 229, 232, 238)",
        )
    ]


def _board_of(ctx: Ctx, eid: str) -> str | None:
    return ctx.by_id.get(eid, {}).get("board")


@hint("polysystem", kinds=(MANAGED_KIND,), relations=MONO_RELATIONS)
def hint_polysystem(ctx: Ctx) -> list[Finding]:
    managed = ctx.profile.home_board.get(MANAGED_KIND)
    if not _content(ctx, managed):
        return []
    monos = [e["id"] for e in ctx.by_id.values() if e["kind"] == MANAGED_KIND]
    if len(monos) < 2:
        return [
            Finding(
                "hint",
                str(managed),
                f"{len(monos)} monosystem(s): for G.P. «реально мы имеем дело с "
                "полисистемами»: how many monosystems are there, and in what "
                "relations? (GP-T5 pp. 206, 213)",
            )
        ]
    related = {
        end
        for kind in MONO_RELATIONS
        for r in _rels(ctx, kind)
        for end in (r["from"], r["to"])
    }
    alone = [m for m in monos if m not in related]
    if not alone:
        return []
    return [
        Finding(
            "hint",
            str(managed),
            "monosystems in no relation to another (parasitic, symbiotic, "
            "mechanism_of; GP-T5 p. 208): " + ", ".join(alone),
        )
    ]


# Beer layer (gate Бир3 В): BEER1972, Stafford Beer, «Мозг фирмы».


def _filler(ctx: Ctx, e: dict[str, Any]) -> tuple[str, str] | None:
    """Who fills a post or position: ("filler", name) for one actor in
    `fillers`, ("element", id) when no actor is named, None when several
    share it (a multinode, BEER1972 Гл. 14). A post with no fillers is filled
    by the one position that `belongs` to it; a position with no fillers that
    belongs to posts with one and the same filler is that filler."""
    fillers = e.get("fillers", [])
    if len(fillers) > 1:
        return None
    if fillers:
        return ("filler", fillers[0])
    if e["kind"] == "post":
        members = sorted(
            {
                r["from"]
                for r in _rels(ctx, "belongs")
                if r["to"] == e["id"] and _kind(ctx, r["from"]) == "position"
            }
        )
        if len(members) > 1:
            return None
        return _filler(ctx, ctx.by_id[members[0]]) if members else ("element", e["id"])
    posts = [ctx.by_id[p].get("fillers", []) for p in _posts(ctx, e["id"])]
    names = {f for fs in posts for f in fs}
    if posts and len(names) == 1 and all(len(fs) == 1 for fs in posts):
        return ("filler", names.pop())
    return ("element", e["id"])


@hint("single-node-metasystem", kinds=("post",), relations=("belongs",))
def hint_single_node_metasystem(ctx: Ctx) -> list[Finding]:
    """One filler of posts and positions fills systems 3, 4 and 5."""
    vsm = ctx.profile.kinds_where("vsm")
    systems: dict[tuple[str, str], set[int]] = {}
    carriers: dict[tuple[str, str], list[str]] = {}
    for e in ctx.by_id.values():
        who = _filler(ctx, e) if "vsm_system" in e and e["kind"] in vsm else None
        if who is not None:
            systems.setdefault(who, set()).update(e["vsm_system"])
            carriers.setdefault(who, []).append(e["id"])
    out: list[Finding] = []
    for who, has in systems.items():
        if METASYSTEM <= has:
            name = f"«{who[1]}»" if who[0] == "filler" else f"'{who[1]}'"
            ids = carriers[who]
            out.append(
                Finding(
                    "hint",
                    ids[0],
                    f"{name} alone fills systems 3, 4 and 5 ({', '.join(ids)}): "
                    "the metasystem is one person, and the transfer will remove it "
                    "with the person. For Beer the model of the firm is kept in "
                    "system 4: «Если бы такой модели не было, то высшее руководство не "
                    "имело бы представления о том, какой фирмой оно управляет» "
                    "(BEER1972 Гл. 13)",
                )
            )
    return out


@hint("line-without-recovery", kinds=(CHANNEL, "post"), relations=("escalates",))
def hint_line_without_recovery(ctx: Ctx) -> list[Finding]:
    """A red line (an algedonic channel with a threshold) with no recovery time
    or no escalation address."""
    out: list[Finding] = []
    for e in ctx.by_id.values():
        if e["kind"] != CHANNEL or "threshold" not in e:
            continue
        missing = []
        if "recovery_time" not in e:
            missing.append("no recovery time (recovery_time)")
        if not any(
            r["from"] == e["id"] and _kind(ctx, r["to"]) in ADDRESSES
            for r in _rels(ctx, "escalates")
        ):
            missing.append(
                "no escalation address (escalates to a post, position or place "
                "for others)"
            )
        if missing:
            out.append(
                Finding(
                    "hint",
                    e["id"],
                    "a red line with a threshold and "
                    + " and ".join(missing)
                    + ": for Beer a unit that cannot restore its index «в приемлемое "
                    "время» sends the signal up, and the people of that level set "
                    "the time: «указать физиологически приемлемое время "
                    "восстановления (приведения в норму) каждого индекса» "
                    "(BEER1972 Гл. 17)",
                )
            )
    return out


@hint("absorbed-into-system-1", kinds=("post",), relations=("captures",))
def hint_absorbed_into_system_1(ctx: Ctx) -> list[Finding]:
    """A transfer scenario on the boards: a post or position filling system 5
    `captures` places that fill systems 4 and 5 of the business."""
    vsm = ctx.profile.kinds_where("vsm")

    def systems_of(eid: str) -> set[int]:
        e = ctx.by_id.get(eid, {})
        return set(e.get("vsm_system", [])) if e.get("kind") in vsm else set()

    taken: dict[str, list[str]] = {}
    for r in _rels(ctx, "captures"):
        if (
            r["from"] != r["to"]
            and 5 in systems_of(r["from"])
            and {4, 5} & systems_of(r["to"])
            and r["to"] not in taken.get(r["from"], [])
        ):
            taken.setdefault(r["from"], []).append(r["to"])
    out: list[Finding] = []
    for source, targets in taken.items():
        has = {n for t in targets for n in systems_of(t)}
        if {4, 5} <= has:
            out.append(
                Finding(
                    "hint",
                    source,
                    f"'{source}' fills system 5 and captures systems 4 and 5 of "
                    f"{', '.join(targets)}: the business becomes part of the "
                    "buyer's system 1, and its name and identity are at risk. Beer "
                    "on a firm taken over by a larger one: «Оно должно перестать "
                    "быть директоратом и становится группой управления. Короче "
                    "говоря, фирма становится одним из подразделений нового целого "
                    "— частью системы 1»; its old name «через несколько лет "
                    "исчезает совсем» (BEER1972 Гл. 15)",
                )
            )
    return out


# Model of the whole (gate Г2 В): a model flagged `of_whole` is the firm's
# model of itself and its environment, the model Beer's system 4 keeps
# (BEER1972 Гл. 13). A post or position holds a model when it `uses` it.


def _models_of_whole(ctx: Ctx) -> list[dict[str, Any]]:
    whole = ctx.profile.kinds_where("of_whole")
    return [e for e in ctx.by_id.values() if e["kind"] in whole and e.get("of_whole")]


def _holders(ctx: Ctx, model: str) -> list[str]:
    """What holds a model: the sources of `uses` relations to it."""
    return list(
        dict.fromkeys(r["from"] for r in _rels(ctx, "uses") if r["to"] == model)
    )


@hint("no-model-of-whole", kinds=("post",), relations=("uses", "belongs"))
def hint_no_model_of_whole(ctx: Ctx) -> list[Finding]:
    """A post or position filling system 4 that holds no model of the whole,
    itself or through its place: a position that `belongs` to it, the post it
    belongs to, or another position of that post."""
    vsm = ctx.profile.kinds_where("vsm")
    models = _models_of_whole(ctx)
    held = [set(_holders(ctx, m["id"])) for m in models]
    out: list[Finding] = []
    for e in ctx.by_id.values():
        if e["kind"] not in vsm or 4 not in e.get("vsm_system", []):
            continue
        posts = _posts(ctx, e["id"])
        place = _belonging(ctx, e["id"]) | posts
        place |= set().union(*(_belonging(ctx, p) for p in posts))
        if any(holders & place for holders in held):
            continue
        missing = (
            "neither it nor a position or post of its place uses a model of the "
            "whole (on the boards: " + ", ".join(m["id"] for m in models) + ")"
            if models
            else "no model of the whole (a model with of_whole: true) is on the "
            "boards"
        )
        out.append(
            Finding(
                "hint",
                e["id"],
                f"'{e['id']}' fills system 4, but {missing}: where is the firm's "
                "model of itself and its environment, and who keeps it? For Beer "
                "system 4 keeps a model of the firm: «тем не менее общая модель "
                "должна быть у фирмы. Если бы такой модели не было, то высшее "
                "руководство не имело бы представления о том, какой фирмой оно "
                "управляет» (BEER1972 Гл. 13)",
            )
        )
    return out


@hint("model-of-whole-one-filler", kinds=("post",), relations=("uses", "belongs"))
def hint_model_of_whole_one_filler(ctx: Ctx) -> list[Finding]:
    """A model of the whole whose holders all resolve to one named filler
    (`_filler`); a reflexive position counts by its fillers too; a holder of
    another kind (a group, a place for others), or a shared one, makes it held
    by more than one."""
    out: list[Finding] = []
    for m in _models_of_whole(ctx):
        holders = _holders(ctx, m["id"])
        who = {
            (
                _filler(ctx, ctx.by_id[h])
                if _kind(ctx, h) in ("post", "position", "reflexive_position")
                else None
            )
            for h in holders
        }
        if len(who) != 1:
            continue
        one = who.pop()
        if one is None or one[0] != "filler":
            continue
        out.append(
            Finding(
                "hint",
                m["id"],
                f"the model of the whole '{m['id']}' is held by «{one[1]}» alone "
                f"(used by {', '.join(holders)}): it leaves with the person at "
                "transfer, and whoever takes the place gets the firm's objects "
                "without its model of itself. For Beer the model may be spread over "
                "people: «такая модель может быть скорее распределённой, то есть "
                "отображающей деятельность достаточно больших обособленных групп "
                "людей, чем единой и хорошо сформированной» (BEER1972 Гл. 13)",
            )
        )
    return out
