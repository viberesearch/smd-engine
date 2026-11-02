"""What people see in place of ids on the diff and agenda pages: member names,
item numbers and questions, element and option labels. The diff carries them in
its `labels` block (written by `smd task diff` from the pack); a diff without the
block, or an id the block lacks, is shown as written."""

from __future__ import annotations

from typing import Any

from smd_engine.task.deal_items import DEAL_CHOICES
from smd_engine.task.deal_labels import DEAL_LABELS
from smd_engine.task.labels import LABELS
from smd_engine.task.ranges import range_text


def labels_block(pack: dict[str, Any]) -> dict[str, Any]:
    """The `labels` block of a diff: members by id, item numbers, the options of
    choice and multi items, the terms and the elements an answer may point at."""
    items = pack["items"]
    deal: dict[str, Any] = {}
    if pack.get("positions"):
        deal["positions"] = {p["id"]: p["label"] for p in pack["positions"]}
    if any(i["kind"] == "fact" for i in items):
        deal["sources"] = {
            s["id"]: s.get("note") or s["address"] for s in pack["sources"]
        }
    return {
        "members": {m["id"]: m["name"] for m in pack["members"]},
        "numbers": {i["id"]: n for n, i in enumerate(items, 1)},
        "terms": {t["id"]: t["term"] for t in pack["term_check"]},
        "options": {
            i["id"]: {o["id"]: o["label"] for o in i["options"]}
            for i in items
            if i.get("options")
        },
        "elements": {e["id"]: e["label"] for e in pack["ontology"]["elements"]},
        **deal,
    }


class Names:
    def __init__(self, lang: str, labels: dict[str, Any] | None) -> None:
        self.lab = LABELS[lang]
        self.lang = lang
        self.labels = labels or {}

    def member(self, m: str) -> str:
        return str(self.labels.get("members", {}).get(m, m))

    def members(self, ms: list[str]) -> str:
        return ", ".join(self.member(m) for m in ms)

    def element(self, i: str) -> str:
        """An id a member may point at: an element, a term check item or an item."""
        got = self.labels.get("elements", {}).get(i)
        if got is None and i in self.labels.get("terms", {}):
            got = self.lab["term_n"].format(t=self.labels["terms"][i])
        if got is None and i in self.labels.get("numbers", {}):
            got = self.lab["item_n"].format(n=self.labels["numbers"][i])
        return str(got if got is not None else i)

    def one(self, p: dict[str, Any], v: Any) -> str:
        """One answer value of a point: an option or an element by its label."""
        if p["kind"] == "item":
            if p.get("item_kind") in DEAL_CHOICES:
                return str(DEAL_LABELS[self.lang]["choices"].get(str(v), v))
            opts = self.labels.get("options", {}).get(p["id"], {})
            if str(v) in opts:
                return str(opts[str(v)])
            if p.get("item_kind") == "ids":
                return self.element(str(v))
        return str(v)

    def value(self, p: dict[str, Any], value: Any) -> str:
        if isinstance(value, dict):  # a range
            return range_text(value, self.lang)
        if isinstance(value, list):
            return "; ".join(self.one(p, v) for v in value)
        return self.one(p, value)

    def sources(self, answer: dict[str, Any]) -> str:
        """The sources an answer names (`source_ids`) by their notes."""
        names = self.labels.get("sources", {})
        return "; ".join(names.get(i, i) for i in answer.get("source_ids", []))

    def refs(self, p: dict[str, Any]) -> str:
        return "; ".join(self.element(r) for r in p.get("refs", []))

    def heading(self, p: dict[str, Any]) -> tuple[str, str]:
        """(short name, text) of a point, with no id in either."""
        if p["kind"] == "term_check":
            return self.lab["term_n"].format(t=p.get("term", "")), p.get("question", "")
        if p["kind"] == "added":
            who = self.member(p["raised_by"]) if p.get("raised_by") else ""
            return self.lab["added_by"].format(m=who), p.get("text", "")
        no = self.labels.get("numbers", {}).get(p["id"])
        short = self.lab["item_n"].format(n=no) if no else self.lab["items"]
        return short, p.get("question", "")

    def title(self, p: dict[str, Any]) -> str:
        short, text = self.heading(p)
        return f"{short}: {text}"

    def reply(self, text: str) -> str:
        """A reply as agenda.yaml keeps it ("accept ben", "keep", "discuss")."""
        word, _, who = text.partition(" ")
        shown = str(self.lab.get(word, word))
        return f"{shown} {self.member(who)}" if who else shown
