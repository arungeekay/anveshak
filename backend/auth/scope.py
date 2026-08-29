"""Role-based scope enforcement (ADR-8, FINALE_PLAN F-09).

An SHO sees their own station, an SP their district, SCRB the whole state, and an
analyst sees statewide data with personal names masked. ADR-8 requires this to be
enforced **server-side in the tool layer** — a frontend that merely hides rows is
not access control.

Two mechanisms:

* `scope_sql()` rewrites a sanitized SELECT with sqlglot, adding a predicate on the
  scoped view's own district/station column. Queries whose tables carry no such
  column (e.g. a pure master-data lookup) are left alone; queries that *should* be
  scopable but cannot be are refused rather than silently returned unscoped.
* `mask_names()` replaces personal names with initials for the ANALYST role.

The demo moment this buys: ask the same question as SP, then as SHO, and watch the
number change on screen — governance you can see, not assert.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

log = logging.getLogger("anveshak.scope")

ROLES = ("SCRB", "SP", "SHO", "ANALYST")

# Seeded demo assignments. Real deployments read these from Catalyst Auth claims;
# the header override exists so a judge can switch roles live.
DEFAULT_UNIT = {"SP": "Bengaluru City", "SHO": "Jayanagar PS"}

# Views that carry their own scope columns, and which column to filter on.
SCOPABLE = {
    "vw_case_360": {"district": "district", "station": "police_station"},
    "vw_accused_history": {"district": "district", "station": "police_station"},
    "vw_station_monthly": {"district": "district", "station": "police_station"},
}

# Columns holding a person's name, masked for the ANALYST role.
NAME_COLUMNS = {
    "full_name", "accusedname", "victimname", "complainantname", "name",
    "person_name", "registering_officer",
}


class ScopeError(ValueError):
    """The query cannot be answered within the caller's scope."""


@dataclass(frozen=True)
class Scope:
    role: str = "SCRB"
    unit: str | None = None          # district name (SP) or station name (SHO)

    @property
    def statewide(self) -> bool:
        return self.role in ("SCRB", "ANALYST")

    @property
    def mask_pii(self) -> bool:
        return self.role == "ANALYST"

    def describe(self) -> str:
        if self.role == "SCRB":
            return "Statewide — State Crime Records Bureau"
        if self.role == "ANALYST":
            return "Statewide, names masked — analyst"
        if self.role == "SP":
            return f"District — {self.unit}"
        return f"Police station — {self.unit}"


def from_headers(headers) -> Scope:
    """Build a Scope from request headers (X-Anveshak-Role / -Unit)."""
    role = (headers.get("x-anveshak-role") or "SCRB").upper().strip()
    if role not in ROLES:
        role = "SCRB"
    unit = (headers.get("x-anveshak-unit") or "").strip() or DEFAULT_UNIT.get(role)
    return Scope(role=role, unit=unit)


def _predicate(scope: Scope, alias: str, cols: dict) -> exp.Expression | None:
    """The WHERE fragment restricting one table reference to the caller's scope."""
    if scope.statewide or not scope.unit:
        return None
    col = cols["district"] if scope.role == "SP" else cols["station"]
    return exp.EQ(
        this=exp.column(col, table=alias) if alias else exp.column(col),
        expression=exp.Literal.string(scope.unit),
    )


def scope_sql(sql: str, scope: Scope) -> str:
    """Return `sql` restricted to the caller's scope.

    Raises ScopeError when a scoped caller asks something that cannot be limited —
    better an honest refusal than data leaking past a role boundary.
    """
    if scope.statewide or not scope.unit:
        return sql
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
    except Exception as exc:  # noqa: BLE001 - guardrails already validated this
        raise ScopeError("could not parse the query for scoping") from exc
    if tree is None:
        raise ScopeError("empty query")

    applied = 0
    for select in tree.find_all(exp.Select):
        preds = []
        for table in select.find_all(exp.Table):
            cols = SCOPABLE.get((table.name or "").lower())
            if not cols:
                continue
            alias = table.alias_or_name
            pred = _predicate(scope, alias, cols)
            if pred is not None:
                preds.append(pred)
        for pred in preds:
            select.where(pred, copy=False)
            applied += 1

    if applied == 0:
        raise ScopeError(
            f"This query cannot be limited to your scope ({scope.describe()}). "
            f"Ask about cases, accused history or station activity, which carry a "
            f"district and station.")
    return tree.sql(dialect="duckdb")


def _mask(value: str) -> str:
    """'Ravi Kumar' -> 'R. K.' — enough to correlate rows, not to identify a person."""
    parts = [p for p in re.split(r"\s+", str(value).strip()) if p]
    if not parts:
        return value
    return " ".join(f"{p[0].upper()}." for p in parts)


def mask_rows(columns: list[str], rows: list, scope: Scope) -> list:
    """Mask name columns in a result set for PII-restricted roles."""
    if not scope.mask_pii or not rows:
        return rows
    idx = [i for i, c in enumerate(columns) if (c or "").lower() in NAME_COLUMNS]
    if not idx:
        return rows
    out = []
    for r in rows:
        r = list(r)
        for i in idx:
            if isinstance(r[i], str):
                r[i] = _mask(r[i])
        out.append(r)
    return out


def mask_name(value: str | None, scope: Scope) -> str | None:
    return _mask(value) if (scope.mask_pii and value) else value


def scope_where(scope: Scope, *, district_col: str = "district",
                station_col: str = "police_station") -> tuple[str, list]:
    """SQL fragment + params for tools that build their own queries.

    Returns ("", []) for statewide roles so callers can concatenate unconditionally.
    """
    if scope.statewide or not scope.unit:
        return "", []
    col = district_col if scope.role == "SP" else station_col
    return f" AND {col} = ?", [scope.unit]
