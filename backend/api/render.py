"""Answer narration + render_spec construction for chat responses (contracts.md §2)."""
from __future__ import annotations

import datetime as _dt
import logging

from ..llm import adapter

log = logging.getLogger("anveshak.render")

_TEMPORAL_COLS = {"ym", "yr", "year", "month", "week", "day", "date"}


def _is_temporal(colname: str, sample) -> bool:
    if colname and colname.lower() in _TEMPORAL_COLS:
        return True
    return isinstance(sample, _dt.date)  # datetime subclasses date


def _table_spec(columns, rows, title) -> dict:
    return {"type": "table", "title": title,
            "table": {"columns": columns, "rows": [list(r) for r in rows]}}


def _xy(columns, rows):
    x = [str(r[0]) for r in rows]
    y = [r[1] for r in rows]
    return x, y


def build_render_specs(columns: list[str], rows: list, title: str) -> list[dict]:
    specs: list[dict] = []
    if len(columns) == 2 and len(rows) >= 2 and isinstance(rows[0][1], int | float):
        x, y = _xy(columns, rows)
        if _is_temporal(columns[0], rows[0][0]):
            specs.append({"type": "line", "title": title, "echarts_option": {
                "xAxis": {"type": "category", "data": x},
                "yAxis": {"type": "value"},
                "series": [{"type": "line", "smooth": True, "data": y}],
                "tooltip": {"trigger": "axis"}}})
        else:
            specs.append({"type": "bar", "title": title, "echarts_option": {
                "xAxis": {"type": "category", "data": x},
                "yAxis": {"type": "value"},
                "series": [{"type": "bar", "data": y}],
                "tooltip": {"trigger": "axis"}}})
    specs.append(_table_spec(columns, rows, title))
    return specs


def extract_case_ids(columns: list[str], rows: list, cap: int = 50) -> list[int]:
    for i, c in enumerate(columns):
        if c == "CaseMasterID":
            out = []
            for r in rows[:cap]:
                try:
                    out.append(int(r[i]))
                except (TypeError, ValueError):
                    pass
            return out
    return []


def _fallback(columns, rows, lang: str) -> str:
    if not rows:
        return "ಯಾವುದೇ ದಾಖಲೆ ಸಿಗಲಿಲ್ಲ." if lang == "kn" else "No matching records were found."
    if len(rows) == 1 and len(columns) == 1:
        return f"{rows[0][0]}"
    return (f"{len(rows)} ಸಾಲುಗಳು ಸಿಕ್ಕಿವೆ." if lang == "kn"
            else f"Returned {len(rows)} rows.")


def compose_answer(question: str, columns: list[str], rows: list, lang: str) -> str:
    """Narrate the verified result (LLM composes; numbers come only from `rows`)."""
    if not rows:
        return _fallback(columns, rows, lang)
    lang_name = "Kannada" if lang == "kn" else "English"
    if len(rows) == 1 and len(columns) == 1:
        payload = f"Result value: {rows[0][0]}"
    else:
        preview = "; ".join(str(tuple(r)) for r in rows[:10])
        payload = f"Columns: {columns}\nRows (up to 10): {preview}"
    prompt = (f"Question: {question}\n{payload}\n\n"
              f"Write a concise 1-2 sentence answer in {lang_name}. Use ONLY the values "
              f"above; do not invent numbers.")
    try:
        res = adapter.chat([{"role": "user", "content": prompt}],
                           system="You are a Karnataka State Police crime-data analyst. "
                                  "Answer briefly and factually using only the provided values.",
                           temperature=0.2, max_tokens=140)
        return res.text or _fallback(columns, rows, lang)
    except Exception as exc:  # never surface a stack trace
        log.warning("compose_answer LLM failed: %s", exc)
        return _fallback(columns, rows, lang)
