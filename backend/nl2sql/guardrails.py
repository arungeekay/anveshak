"""SQL guardrails (contracts.md §7 invariants).

parse with sqlglot; reject anything but a single read-only query; auto-append
LIMIT; strip comments/fences; validate table/view identifiers against the schema
allowlist. Scope WHERE injection (ADR-8) is applied by the tool layer at T21.
"""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

# Schema tables + analyst views (lowercased). NL->SQL should target the views.
ALLOWED_TABLES = {
    "state", "district", "unittype", "unit", "rank", "designation", "employee",
    "court", "act", "section", "crimehead", "crimesubhead", "crimeheadactsection",
    "casecategory", "gravityoffence", "casestatusmaster", "occupationmaster",
    "religionmaster", "castemaster", "casemaster", "complainantdetails", "victim",
    "accused", "actsectionassociation", "arrestsurrender", "inv_arrestsurrenderaccused",
    "inv_occurancetime", "chargesheetdetails", "personregistry", "accusedpersonmap",
    "casemovector", "districtindicators", "auditlog",
    "vw_case_360", "vw_accused_history", "vw_station_monthly", "vw_coaccusal_edges",
}

_FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
              exp.Command, exp.Merge)

DEFAULT_LIMIT = 500


class GuardrailError(ValueError):
    """The SQL violated a read-only / schema invariant."""


def _strip(sql: str) -> str:
    sql = sql.strip()
    # Remove ```sql fences if the model wrapped them.
    sql = re.sub(r"^```(?:sql)?", "", sql, flags=re.IGNORECASE).strip()
    sql = re.sub(r"```$", "", sql).strip()
    return sql.rstrip(";").strip()


def sanitize(sql: str, *, max_limit: int = DEFAULT_LIMIT) -> str:
    """Return a safe, single read-only SELECT (with LIMIT) or raise GuardrailError."""
    cleaned = _strip(sql)
    if not cleaned:
        raise GuardrailError("empty query")
    try:
        statements = [s for s in sqlglot.parse(cleaned, read="duckdb") if s is not None]
    except Exception as exc:
        raise GuardrailError(f"parse error: {exc}") from exc
    if len(statements) != 1:
        raise GuardrailError("exactly one statement is allowed")
    tree = statements[0]

    for node in tree.walk():
        if isinstance(node, _FORBIDDEN):
            raise GuardrailError("only read-only SELECT queries are permitted")

    if not isinstance(tree, exp.Query):  # Select / Union / Intersect / Except
        raise GuardrailError("only SELECT queries are permitted")

    for table in tree.find_all(exp.Table):
        if table.name and table.name.lower() not in ALLOWED_TABLES:
            raise GuardrailError(f"unknown table or view: {table.name}")

    if isinstance(tree, exp.Select) and not tree.args.get("limit"):
        tree = tree.limit(max_limit)

    return tree.sql(dialect="duckdb")


def is_read_only(sql: str) -> bool:
    try:
        sanitize(sql)
        return True
    except GuardrailError:
        return False
