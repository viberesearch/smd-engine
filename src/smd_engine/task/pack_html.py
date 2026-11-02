"""`pack.html`: the pack as one offline page. The ontology slice is a tab with the
relations drawn as inline SVG; the items are a form that saves itself in the
browser, and a button writes `answers_<member>.yaml` for the answers schema."""

from __future__ import annotations

from typing import Any

from smd_engine.render.text import esc
from smd_engine.task.labels import LABELS
from smd_engine.task.refs import ref_groups
from smd_engine.task.svg import ontology_figure
from smd_engine.task.web import page, table as _table

UI_KEYS = (
    "remove",
    "transcript_path",
    "transcript_note",
    "added_text",
    "added_refs",
    "missing_member",
    "missing_required",
    "exported",
    "answered",
    "of",
    "checked",
    "nothing_found",
)


def _checklist(
    item: dict[str, Any], lab: dict[str, Any], onto: dict[str, Any], key: str
) -> str:
    """An `ids` item as a searchable checklist: a filter box, a count, and the
    elements by their labels, grouped under the element their relations lead to.
    The checkboxes carry the ids as values, so the answer stays a list of ids."""
    groups = ref_groups(onto, item.get("refs"))
    total = sum(len(members) for _, members in groups)
    body = ""
    for heading, members in groups:
        title = heading if heading is not None else lab["no_group"]
        head = f"<legend>{esc(title)}</legend>" if len(groups) > 1 else ""
        body += (
            f'<fieldset class="ckg">{head}'
            + "".join(
                f'<label class="opt ckopt"><input type="checkbox" '
                f'data-s="{esc(key)}" value="{esc(i)}"> <span>{esc(name)}</span></label>'
                for i, name in members
            )
            + "</fieldset>"
        )
    return (
        f'<div class="ck" data-total="{total}">'
        f'<div class="bar"><input type="search" class="ckf" '
        f'placeholder="{esc(lab["filter"])}" aria-label="{esc(lab["filter"])}">'
        f'<label class="ckonly"><input type="checkbox" class="cko"> '
        f'{esc(lab["only_checked"])}</label>'
        f'<span class="ckn" role="status"></span></div>{body}'
        f'<p class="meta ckempty hide">{esc(lab["nothing_found"])}</p></div>'
    )


def _input(item: dict[str, Any], lab: dict[str, Any], onto: dict[str, Any]) -> str:
    key = f"v:{item['id']}"
    kind = item["kind"]
    if kind in ("choice", "multi"):
        box = "radio" if kind == "choice" else "checkbox"
        opts = "".join(
            f'<label class="opt"><input type="{box}" name="{esc(key)}" '
            f'data-s="{esc(key)}" value="{esc(o["id"])}"> <b>{esc(o["label"])}</b>'
            + (
                f'<span class="ctx">{esc(o["context"])}</span>'
                if o.get("context")
                else ""
            )
            + "</label>"
            for o in item["options"]
        )
        clear = (
            f'<button type="button" class="link" data-clear="{esc(key)}">'
            f'{esc(lab["clear"])}</button>'
        )
        return opts + (clear if kind == "choice" else "")
    if kind == "number":
        return f'<input type="number" step="any" data-s="{esc(key)}">'
    if kind == "ids":
        return _checklist(item, lab, onto, key)
    rows = 5 if kind == "steps" else 3
    return f'<textarea rows="{rows}" data-s="{esc(key)}"></textarea>'


def _item(
    item: dict[str, Any],
    lab: dict[str, Any],
    no: int,
    onto: dict[str, Any],
) -> str:
    """One item of the form. People see its number, the labels of the elements
    it refers to and the labels of the recommended options; ids stay in the
    files (the answers file keys and `data-s`)."""
    iid = item["id"]
    names = {e["id"]: e["label"] for e in onto["elements"]}
    meta = [lab["kinds"][item["kind"]]]
    if item.get("required", True):
        meta.append(lab["required"])
    if item.get("refs") and item["kind"] != "ids":
        meta.append(
            f"{lab['refs']}: {'; '.join(names.get(r, r) for r in item['refs'])}"
        )
    rec = item.get("recommendation")
    rec_html = ""
    if rec:
        value = rec["value"]
        opts = {o["id"]: o["label"] for o in item.get("options", [])}
        values = value if isinstance(value, list) else [value]
        shown = ", ".join(opts.get(str(v), str(v)) for v in values)
        reason = f" ({rec['reason']})" if rec.get("reason") else ""
        rec_html = f'<div class="rec">{esc(lab["recommendation"])}: {esc(shown + reason)}</div>'
    conf = "".join(
        f'<option value="{c}">{esc(lab[c])}</option>' for c in ("low", "medium", "high")
    )
    more = (
        f'<details><summary>{esc(lab["reason"])}, {esc(lab["src"])}, '
        f'{esc(lab["confidence"])}</summary>'
        f'<label class="f">{esc(lab["reason"])}<textarea rows="2" data-s="r:{esc(iid)}"></textarea></label>'
        f'<label class="f">{esc(lab["src"])}<input type="text" data-s="s:{esc(iid)}"></label>'
        f'<label class="f">{esc(lab["confidence"])}<select data-s="c:{esc(iid)}">'
        f'<option value="">-</option>{conf}</select></label>'
        f'<label class="f">{esc(lab["term_note"])}<input type="text" data-s="t:{esc(iid)}"></label>'
        "</details>"
    )
    return (
        f'<div class="item" id="item-{esc(iid)}"><h4>{no}</h4>'
        f'<p class="q">{esc(item["question"])}</p>'
        f'<p class="meta">{esc("; ".join(meta))}</p>{rec_html}{_input(item, lab, onto)}{more}</div>'
    )


def render_pack_html(pack: dict[str, Any], pack_sha: str) -> str:
    lang = pack["lang"]
    lab = LABELS[lang]
    task, onto = pack["task"], pack["ontology"]
    members = ", ".join(m["name"] for m in pack["members"])
    feeds = task["feeds"]
    names = {e["id"]: e["label"] for e in onto["elements"]}
    feed_list = (
        "<ul>"
        + "".join(f"<li>{esc(names.get(i, i))}</li>" for i in feeds["ids"])
        + "</ul>"
        if feeds.get("ids")
        else ""
    )
    steps = "".join(f"<li>{esc(s)}</li>" for s in lab["cycle_steps"])
    t_task = (
        _table(
            [lab["id"], lab["version"], lab["date"], lab["due"], lab["facilitator"]],
            [
                [
                    esc(x)
                    for x in (
                        pack["id"],
                        pack["version"],
                        pack["date"],
                        pack["due"],
                        {m["id"]: m["name"] for m in pack["members"]}.get(
                            pack["facilitator"], pack["facilitator"]
                        ),
                    )
                ]
            ],
        )
        + f"<p>{esc(lab['members'])}: {esc(members)}</p>"
        + f"<h2>{esc(lab['task'])}</h2><p><b>{esc(lab['what'])}.</b> {esc(task['what'])}</p>"
        + f"<p><b>{esc(lab['why'])}.</b> {esc(task['why'])}</p>"
        + f"<p><b>{esc(lab['feeds'])}.</b> {esc(feeds['text'])}</p>{feed_list}"
        + f"<h2>{esc(lab['sources'])}</h2>"
        + _table(
            [lab["address"], lab["note"]],
            [[esc(s["address"]), esc(s.get("note", ""))] for s in pack["sources"]],
        )
        + f"<h2>{esc(lab['cycle'])}</h2><ol>{steps}</ol>"
        + f"<h2>{esc(lab['how'])}</h2><p>{esc(lab['how_text'].replace('`', ''))}</p>"
    )
    t_onto = (
        f"<h2>{esc(lab['terms'])}</h2>"
        + _table(
            [lab["term"], lab["definition"], lab["source"]],
            [
                [f"<b>{esc(t['term'])}</b>", esc(t["definition"]), esc(t["source"])]
                for t in onto["terms"]
            ],
        )
        + f"<h2>{esc(lab['relations'])}</h2>"
        + ontology_figure(onto, lang, uid=f"onto-{pack['id']}")
        + f"<h2>{esc(lab['elements'])}</h2>"
        + _table(
            [lab["label"], lab["tier"], lab["kind"]],
            [
                [
                    esc(e["label"]),
                    esc(str(e.get("tier", ""))),
                    esc(e.get("kind", "")),
                ]
                for e in onto["elements"]
            ],
        )
    )
    t_term = f"<p>{esc(lab['term_check_intro'])}</p>" + "".join(
        f'<div class="item"><h4>{esc(t["term"])}</h4>'
        f'<p class="q">{esc(t["question"])}</p>'
        f'<textarea rows="3" data-s="tc:{esc(t["id"])}"></textarea></div>'
        for t in pack["term_check"]
    )
    t_items = f'<p class="meta" id="count"></p>'
    numbers = {i["id"]: n for n, i in enumerate(pack["items"], 1)}
    for section in dict.fromkeys(i["section"] for i in pack["items"]):
        t_items += f"<h3>{esc(section)}</h3>"
        t_items += "".join(
            _item(i, lab, numbers[i["id"]], onto)
            for i in pack["items"]
            if i["section"] == section
        )
    member_opts = f'<option value="">{esc(lab["choose"])}</option>' + "".join(
        f'<option value="{esc(m["id"])}">{esc(m["name"])}</option>'
        for m in pack["members"]
    )
    t_export = (
        f'<label class="f">{esc(lab["member"])}<select data-s="member">{member_opts}</select></label>'
        f'<label class="f">{esc(lab["date"])}<input type="date" data-s="date"></label>'
        f'<label class="f">{esc(lab["drafted_by"])}<select data-s="drafted">'
        f'<option value="self">{esc(lab["self"])}</option>'
        f'<option value="model_edited">{esc(lab["model_edited"])}</option></select></label>'
        f"<h3>{esc(lab['transcripts'])}</h3><p class=\"meta\">{esc(lab['transcripts_hint'])}</p>"
        '<div data-rows="transcripts"></div>'
        f'<button type="button" data-add="transcripts">{esc(lab["add_transcript"])}</button>'
        f"<h3>{esc(lab['added'])}</h3><p class=\"meta\">{esc(lab['added_hint'])}</p>"
        '<div data-rows="added"></div>'
        f'<button type="button" data-add="added">{esc(lab["add_point"])}</button>'
        f'<p class="meta">{esc(lab["saved"])}</p>'
        f'<p><button type="button" class="primary" id="export">{esc(lab["export"])}</button></p>'
        '<div id="status" role="status"></div>'
    )
    cfg = {
        "mode": "pack",
        "key": f"{pack['id']}:{pack['version']}",
        "pack": {"id": pack["id"], "version": pack["version"], "sha256": pack_sha},
        "term": [t["id"] for t in pack["term_check"]],
        "items": [
            {
                "id": i["id"],
                "no": n,
                "kind": i["kind"],
                "required": i.get("required", True),
            }
            for n, i in enumerate(pack["items"], 1)
        ],
        "ui": {k: lab[k] for k in UI_KEYS},
    }
    tabs = [
        ("task", lab["tab_task"], t_task),
        ("term", lab["tab_term"], t_term),
        ("ontology", lab["tab_ontology"], t_onto),
        ("items", lab["tab_items"], t_items),
        ("export", lab["tab_export"], t_export),
    ]
    return page(
        pack.get("title", pack["id"]),
        lang,
        f"{pack['id']} {pack['version']}, {lab['due']} {pack['due']}",
        tabs,
        cfg,
    )
