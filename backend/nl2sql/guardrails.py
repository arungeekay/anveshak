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

# DuckDB file/IO table functions would let a crafted query read arbitrary files off
# the server (data-exfiltration). They are not tables, so the identifier allowlist
# misses them, reject them explicitly by name.
_FORBIDDEN_FUNCS = {
    "read_csv", "read_csv_auto", "read_parquet", "parquet_scan", "read_json",
    "read_json_auto", "read_ndjson", "read_ndjson_auto", "read_text", "read_blob",
    "glob", "csv_scan", "iceberg_scan", "delta_scan", "sniff_csv", "read_xlsx",
}
_FORBIDDEN_FUNC_RE = re.compile(
    r"\b(" + "|".join(sorted(_FORBIDDEN_FUNCS)) + r")\s*\(", re.IGNORECASE)

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

    # Reject file/IO table functions regardless of how sqlglot node-types them.
    if _FORBIDDEN_FUNC_RE.search(cleaned):
        raise GuardrailError("file/IO functions are not permitted")

    # CTE aliases are query-local names, not base tables, exclude them from the
    # allowlist check so legitimate WITH ... SELECT queries aren't wrongly rejected.
    cte_names = {c.alias.lower() for c in tree.find_all(exp.CTE) if c.alias}
    for table in tree.find_all(exp.Table):
        name = table.name.lower() if table.name else ""
        if name and name not in ALLOWED_TABLES and name not in cte_names:
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
