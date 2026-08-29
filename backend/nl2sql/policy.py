"""Protected-attribute policy (ADR-9 made visible, FINALE_PLAN F-12).

Religion and caste exist in the KSP schema because they are in the official ER
document, but ANVESHAK never uses them as model features and must never help
profile an individual by them.

A jury WILL test this ("show me thefts by religion"), so the refusal is a designed,
explainable product surface rather than a silent omission:

* aggregate, explicitly sociological queries are ALLOWED (GROUP BY religion with
  counts), public-interest statistics are legitimate;
* anything that filters individuals by a protected attribute, or selects it
  alongside identifying columns, is BLOCKED with a policy explanation, in English
  and Kannada, and the attempt is audited.
"""
from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

# Columns/tables that carry a protected attribute in the KSP schema.
PROTECTED_COLUMNS = {"religionid", "casteid", "religionname", "castename"}
PROTECTED_TABLES = {"religionmaster", "castemaster"}

# Columns that identify a specific person; selecting these beside a protected
# attribute turns a statistic into a profile.
IDENTIFYING_COLUMNS = {
    "accusedname", "victimname", "complainantname", "full_name", "person_key",
    "accusedmasterid", "casemasterid", "crimeno", "caseno",
}

REASON_EN = (
    "ANVESHAK does not answer questions that group or filter individuals by "
    "religion or caste. These attributes are never used in linkage, risk scoring or "
    "forecasting (ADR-9). Aggregate statistics for an explicitly sociological "
    "purpose can be produced, but never a profile of people by a protected "
    "attribute."
)
REASON_KN = (
    "ಧರ್ಮ ಅಥವಾ ಜಾತಿಯ ಆಧಾರದ ಮೇಲೆ ವ್ಯಕ್ತಿಗಳನ್ನು ವರ್ಗೀಕರಿಸುವ ಅಥವಾ ಶೋಧಿಸುವ "
    "ಪ್ರಶ್ನೆಗಳಿಗೆ ANVESHAK ಉತ್ತರಿಸುವುದಿಲ್ಲ. ಈ ಮಾಹಿತಿಯನ್ನು ಅಪರಾಧ ಸಂಪರ್ಕ, ಅಪಾಯ "
    "ಮೌಲ್ಯಮಾಪನ ಅಥವಾ ಮುನ್ಸೂಚನೆಯಲ್ಲಿ ಎಂದಿಗೂ ಬಳಸುವುದಿಲ್ಲ."
)

# Natural-language cues, checked before SQL is even generated so an obviously
# profiling question never reaches the model.
_NL_PROTECTED = re.compile(
    r"\b(religion|religious|caste|communal|muslim|hindu|christian|dalit|"
    r"brahmin|lingayat|vokkaliga|ಧರ್ಮ|ಜಾತಿ)\b", re.IGNORECASE)
_NL_AGGREGATE = re.compile(
    r"\b(breakdown|distribution|statistics|proportion|percentage|how many|"
    r"count|composition|demograph)\w*\b", re.IGNORECASE)


class PolicyBlock(Exception):
    """The request is refused on protected-attribute grounds."""

    def __init__(self, reason_en: str = REASON_EN, reason_kn: str = REASON_KN,
                 stage: str = "policy"):
        super().__init__(reason_en)
        self.reason_en = reason_en
        self.reason_kn = reason_kn
        self.stage = stage

    def as_dict(self, lang: str = "en") -> dict:
        return {
            "blocked": True,
            "policy": "ADR-9, protected attributes",
            "stage": self.stage,
            "reason": self.reason_kn if lang == "kn" else self.reason_en,
            "reason_en": self.reason_en,
            "reason_kn": self.reason_kn,
        }


def mentions_protected(question: str) -> bool:
    return bool(_NL_PROTECTED.search(question or ""))


def check_question(question: str) -> None:
    """Pre-SQL screen: block a question that profiles people by a protected attribute.

    An aggregate/statistical framing is allowed through to the SQL-level check,
    which enforces the real invariant (no identifying columns, must be grouped).
    """
    if not mentions_protected(question):
        return
    if _NL_AGGREGATE.search(question or ""):
        return  # let the SQL-level check decide; it is the stricter gate
    raise PolicyBlock()


def check_sql(sql: str) -> None:
    """Post-generation screen on the parsed SQL.

    Allowed: aggregate breakdowns (GROUP BY a protected column, aggregate select,
    no identifying columns). Blocked: filtering individuals by a protected
    attribute, or selecting one next to identifying columns.
    """
    try:
        tree = sqlglot.parse_one(sql, read="duckdb")
    except Exception:  # noqa: BLE001 - guardrails already reject unparseable SQL
        return
    if tree is None:
        return

    used_cols = {c.name.lower() for c in tree.find_all(exp.Column) if c.name}
    used_tables = {t.name.lower() for t in tree.find_all(exp.Table) if t.name}
    protected_used = ((used_cols & PROTECTED_COLUMNS)
                      | (used_tables & PROTECTED_TABLES))
    if not protected_used:
        return

    # A protected attribute inside WHERE/HAVING filters individuals by it.
    for clause in list(tree.find_all(exp.Where)) + list(tree.find_all(exp.Having)):
        if {c.name.lower() for c in clause.find_all(exp.Column)} & PROTECTED_COLUMNS:
            raise PolicyBlock(stage="sql")

    # Selecting a protected attribute beside identifying columns is a profile.
    if used_cols & IDENTIFYING_COLUMNS:
        raise PolicyBlock(stage="sql")

    # Otherwise require a genuine aggregate: GROUP BY + an aggregate function.
    has_group = bool(list(tree.find_all(exp.Group)))
    has_agg = any(isinstance(n, exp.AggFunc) for n in tree.walk())
    if not (has_group and has_agg):
        raise PolicyBlock(stage="sql")
