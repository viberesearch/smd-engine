"""Tags and bound detail columns, checked against the case's taxonomy file."""

from __future__ import annotations

from typing import Any

from smd_engine.validate.context import Ctx, Finding, board_set

# Board-set lists whose items may carry `tags`.
TAGGED = ("elements", "theses", "hypotheses", "ontology")


def taxonomy_values(record: dict[str, Any]) -> dict[str, set[str]]:
    """Taxonomy id to the value ids of a schema-valid taxonomies record."""
    return {
        tax: {v["id"] for v in values} for tax, values in record["taxonomies"].items()
    }


def _value_findings(
    ctx: Ctx, where: str, tax: str, values: list[str], what: str
) -> list[Finding]:
    assert ctx.taxonomies is not None
    if tax not in ctx.taxonomies:
        return [Finding("error", where, f"{what}: unknown taxonomy '{tax}'")]
    return [
        Finding("error", where, f"{what}: '{v}' is not a value of taxonomy '{tax}'")
        for v in values
        if v not in ctx.taxonomies[tax]
    ]


def _detail_findings(ctx: Ctx, el: dict[str, Any]) -> list[Finding]:
    detail = el["detail"]
    out: list[Finding] = []
    for column, tax in detail.get("keys", {}).items():
        if column not in detail["columns"]:
            out.append(
                Finding("error", el["id"], f"detail key '{column}' is not a column")
            )
            continue
        if ctx.taxonomies is None:
            continue
        n = detail["columns"].index(column)
        cells = [row[n] for row in detail["rows"] if n < len(row)]
        values = [v.strip() for cell in cells for v in cell.split(";") if v.strip()]
        out += _value_findings(ctx, el["id"], tax, values, f"detail '{column}'")
    return out


@board_set
def check_tags(ctx: Ctx) -> list[Finding]:
    out: list[Finding] = []
    used = False
    for field in TAGGED:
        for item in ctx.record.get(field, []):
            used = used or bool(item.get("tags"))
            if ctx.taxonomies is not None:
                for tax, values in item.get("tags", {}).items():
                    out += _value_findings(ctx, item["id"], tax, values, "tags")
    for el in ctx.record["elements"]:
        if "detail" in el:
            used = used or bool(el["detail"].get("keys"))
            out += _detail_findings(ctx, el)
    if used and ctx.taxonomies is None:
        out.append(
            Finding(
                "warning",
                "tags",
                "tags or detail keys are used and no taxonomy file is given "
                "(--taxonomies)",
            )
        )
    return out
