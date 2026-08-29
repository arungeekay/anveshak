"""NL->SQL engine: prompt build -> LLM -> guardrails -> execute, with self-repair.

On a parse/guardrail/execution failure the error is fed back to the model (max 2
retries) per contracts.md §7. The LLM only writes SQL; it never computes results.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..llm import adapter
from ..auth.scope import scope_sql
from . import guardrails, policy
from .schema_card import build_prompt

log = logging.getLogger("anveshak.nl2sql")

FEW_SHOTS_PATH = Path(__file__).resolve().parent / "few_shots.yaml"
SYSTEM = ("You are a precise text-to-SQL engine for DuckDB over a police crime "
          "database. Output exactly one read-only SELECT statement and nothing else.")


class EngineError(RuntimeError):
    """NL->SQL failed after all repair attempts."""


@dataclass
class NLResult:
    sql: str
    columns: list[str]
    rows: list[tuple]
    row_count: int
    truncated: bool
    attempts: int
    repaired: bool


def load_few_shots() -> list[dict]:
    return yaml.safe_load(FEW_SHOTS_PATH.read_text(encoding="utf-8"))


def extract_sql(text: str) -> str:
    """Pull a single SQL statement out of a model response."""
    t = (text or "").strip()
    fence = re.search(r"```(?:sql)?\s*(.+?)```", t, re.S | re.I)
    if fence:
        t = fence.group(1).strip()
    m = re.search(r"(?is)\b(WITH|SELECT)\b", t)
    if m:
        t = t[m.start():]
    return t.strip().rstrip(";").strip()


def generate_sql(question: str, few_shots: list[dict] | None = None) -> str:
    """Single-shot generation (no execution) — used by the eval harness."""
    prompt = build_prompt(question, few_shots or load_few_shots())
    res = adapter.chat([{"role": "user", "content": prompt}], system=SYSTEM,
                       temperature=0.0, max_tokens=256)
    return extract_sql(res.text)


def run(con, question: str, *, max_repairs: int = 2, scope=None) -> NLResult:
    """Generate, guardrail, scope, execute — repairing on failure up to max_repairs times."""
    messages = [{"role": "user", "content": build_prompt(question, load_few_shots())}]
    last_err: str | None = None
    for attempt in range(max_repairs + 1):
        res = adapter.chat(messages, system=SYSTEM, temperature=0.0, max_tokens=256)
        raw = extract_sql(res.text)
        safe = None
        try:
            safe = guardrails.sanitize(raw)
            # ADR-9: refuse SQL that profiles people by a protected
            # attribute. Raised past the repair loop deliberately —
            # this is a policy decision, not a syntax error to retry.
            policy.check_sql(safe)
            # ADR-8: role scope is injected server-side, into the SQL that
            # actually runs — never into the prompt, which the model could
            # ignore or the user could talk it out of.
            if scope is not None:
                safe = scope_sql(safe, scope)
            cur = con.execute(safe)
            columns = [d[0] for d in cur.description]
            rows = cur.fetchall()
            return NLResult(sql=safe, columns=columns, rows=rows, row_count=len(rows),
                            truncated=len(rows) >= guardrails.DEFAULT_LIMIT,
                            attempts=attempt + 1, repaired=attempt > 0)
        except guardrails.GuardrailError as exc:
            last_err = f"guardrail rejected: {exc}"
        except Exception as exc:
            last_err = f"execution error: {exc}"
        log.info("nl2sql repair %d: %s", attempt + 1, last_err)
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user",
                         "content": f"That SQL failed ({last_err}). Return ONE corrected "
                                    f"DuckDB SELECT only, no explanation."})
    raise EngineError(last_err or "nl2sql failed to produce valid SQL")
