"""`pack.md`: the pack as Markdown, to read or to attach to a model. Tables for
the data, the cycle and the ontology relations as Mermaid blocks."""

from __future__ import annotations

from typing import Any

from smd_engine.task.labels import LABELS
from smd_engine.task.refs import ref_groups


def cell(value: Any) -> str:
    """Text for a table cell: no pipes, no line breaks."""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def table(head: list[str], rows: list[list[Any]]) -> list[str]:
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return out + [""]


def mm(text: str) -> str:
    """Text for a Mermaid label."""
    return text.replace('"', "'").replace("\n", " ")


def cycle_block(lang: str) -> list[str]:
    steps = LABELS[lang]["cycle_steps"]
    out = ["```mermaid", "flowchart LR"]
    out += [f'  s{i}["{mm(s)}"]' for i, s in enumerate(steps)]
    out += [f"  s{i} --> s{i + 1}" for i in range(len(steps) - 1)]
    return out + ["```", ""]


def relations_block(ontology: dict[str, Any], lang: str) -> list[str]:
    elements = ontology["elements"]
    index = {e["id"]: f"n{i}" for i, e in enumerate(elements)}
    out = ["```mermaid", "flowchart LR"]
    tiers = sorted({e["tier"] for e in elements if "tier" in e})
    for tier in tiers:
        out.append(f'  subgraph t{tier}["{LABELS[lang]["tier_n"].format(n=tier)}"]')
        out += [
            f'    {index[e["id"]]}["{mm(e["label"])} ({e["id"]})"]'
            for e in elements
            if e.get("tier") == tier
        ]
        out.append("  end")
    out += [
        f'  {index[e["id"]]}["{mm(e["label"])} ({e["id"]})"]'
        for e in elements
        if "tier" not in e
    ]
    out += [
        f"  {index[r['from']]} -->|{mm(r['kind'])}| {index[r['to']]}"
        for r in ontology["relations"]
        if r["from"] in index and r["to"] in index
    ]
    return out + ["```", ""]


def _item(
    item: dict[str, Any], lab: dict[str, Any], no: int, onto: dict[str, Any]
) -> list[str]:
    """One item: its number as the heading, element labels for the refs and
    option labels for the recommendation; the id stays in a comment. The refs
    of an `ids` item are the list to tick, grouped under their question."""
    names = {e["id"]: e["label"] for e in onto["elements"]}
    required = item.get("required", True)
    out = [
        f"#### {no}",
        "",
        f"<!-- id: {item['id']} -->",
        "",
        item["question"],
        "",
        f"- {lab['kind']}: {lab['kinds'][item['kind']]}",
        f"- {lab['required']}: {lab['yes'] if required else lab['no']}",
    ]
    if item.get("refs") and item["kind"] != "ids":
        out.append(
            f"- {lab['refs']}: {'; '.join(names.get(r, r) for r in item['refs'])}"
        )
    rec = item.get("recommendation")
    if rec:
        value = rec["value"]
        opts = {o["id"]: o["label"] for o in item.get("options", [])}
        values = value if isinstance(value, list) else [value]
        shown = ", ".join(opts.get(str(v), str(v)) for v in values)
        reason = f" ({rec['reason']})" if rec.get("reason") else ""
        out.append(f"- {lab['recommendation']}: {shown}{reason}")
    out.append("")
    if item["kind"] == "ids":
        groups = ref_groups(onto, item.get("refs"))
        for heading, members in groups:
            if len(groups) > 1:
                out.append(f"**{heading if heading is not None else lab['no_group']}**")
                out.append("")
            out += [f"- [ ] {label}" for _, label in members]
            out.append("")
    if item.get("options"):
        rows = [[o["id"], o["label"], o.get("context", "")] for o in item["options"]]
        out += table([lab["option"], lab["label"], lab["context"]], rows)
    return out


def render_pack_md(pack: dict[str, Any]) -> str:
    lab = LABELS[pack["lang"]]
    members = ", ".join(m["name"] for m in pack["members"])
    names = {m["id"]: m["name"] for m in pack["members"]}
    facilitator = names.get(pack["facilitator"], pack["facilitator"])
    task = pack["task"]
    onto = pack["ontology"]
    out = [f"# {pack.get('title', pack['id'])}", "", f"_{lab['doc_draft']}_", ""]
    out += table(
        [lab["id"], lab["version"], lab["date"], lab["due"], lab["facilitator"]],
        [[pack["id"], pack["version"], pack["date"], pack["due"], facilitator]],
    )
    out += [f"{lab['members']}: {members}", "", f"## {lab['cycle']}", ""]
    out += cycle_block(pack["lang"])
    feeds = task["feeds"]
    labels = {e["id"]: e["label"] for e in onto["elements"]}
    feed_list = (
        ["", *[f"- {labels.get(i, i)}" for i in feeds["ids"]]]
        if feeds.get("ids")
        else []
    )
    out += [
        f"## {lab['task']}",
        "",
        f"**{lab['what']}.** {task['what']}",
        "",
        f"**{lab['why']}.** {task['why']}",
        "",
        f"**{lab['feeds']}.** {feeds['text']}",
        *feed_list,
        "",
        f"## {lab['term_check']}",
        "",
        lab["term_check_intro"],
        "",
    ]
    out += table(
        ["№", lab["term"], lab["question"]],
        [[n, t["term"], t["question"]] for n, t in enumerate(pack["term_check"], 1)],
    )
    out += [
        f"## {lab['ontology']}",
        "",
        f"### {lab['terms']}",
        "",
    ]
    out += table(
        [lab["term"], lab["definition"], lab["source"]],
        [[t["term"], t["definition"], t["source"]] for t in onto["terms"]],
    )
    out += [f"### {lab['elements']}", ""]
    out += table(
        [lab["id"], lab["label"], lab["tier"], lab["kind"]],
        [
            [e["id"], e["label"], e.get("tier", ""), e.get("kind", "")]
            for e in onto["elements"]
        ],
    )
    out += [f"### {lab['relations']}", ""]
    out += relations_block(onto, pack["lang"])
    out += [f"## {lab['sources']}", ""]
    out += table(
        [lab["id"], lab["address"], lab["note"]],
        [[s["id"], s["address"], s.get("note", "")] for s in pack["sources"]],
    )
    out += [f"## {lab['items']}", ""]
    numbers = {i["id"]: n for n, i in enumerate(pack["items"], 1)}
    for section in dict.fromkeys(i["section"] for i in pack["items"]):
        out += [f"### {section}", ""]
        for item in pack["items"]:
            if item["section"] == section:
                out += _item(item, lab, numbers[item["id"]], onto)
    out += [f"## {lab['how']}", "", lab["how_text"], ""]
    return "\n".join(out).rstrip() + "\n"
