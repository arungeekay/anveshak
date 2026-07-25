"""Answer narration + render_spec construction for chat responses (contracts.md §2)."""
from __future__ import annotations

import datetime as _dt
import logging
import re

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


def graph_spec(gr: dict, title: str = "Network") -> dict:
    kind_color = {"person": "#3b82f6", "case": "#f59e0b", "location": "#10b981", "ps": "#a78bfa"}
    nodes = [{"id": n["id"], "name": n["label"],
              "itemStyle": {"color": kind_color.get(n["kind"], "#94a3b8")},
              "symbolSize": 30 if n["kind"] == "person" else 14}
             for n in gr["nodes"]]
    links = [{"source": e["a"], "target": e["b"]} for e in gr["edges"]]
    return {"type": "graph", "title": title, "echarts_option": {
        "tooltip": {}, "series": [{"type": "graph", "layout": "force", "roam": True,
                                   "label": {"show": True, "fontSize": 9},
                                   "force": {"repulsion": 120, "edgeLength": 60},
                                   "data": nodes, "links": links}]}}


def map_spec(cells: list[dict], title: str = "Hotspots") -> dict:
    points = [[c["lat"], c["lon"], c["intensity"]] for c in cells]
    center = ([sum(p[0] for p in points) / len(points),
               sum(p[1] for p in points) / len(points)] if points else [12.97, 77.59])
    return {"type": "map", "title": title,
            "leaflet_spec": {"center": center, "zoom": 11,
                             "layers": [{"kind": "heat", "points": points}]}}


def forecast_spec(fc: dict, title: str = "Forecast") -> dict:
    hist = fc.get("history", [])[-26:]
    fut = fc.get("forecast", [])
    x = [h["week"] for h in hist] + [f["week"] for f in fut]
    hist_y = [h["count"] for h in hist] + [None] * len(fut)
    fut_y = [None] * len(hist) + [f["mean"] for f in fut]
    return {"type": "line", "title": title, "echarts_option": {
        "tooltip": {"trigger": "axis"}, "legend": {"data": ["history", "forecast"]},
        "xAxis": {"type": "category", "data": x}, "yAxis": {"type": "value"},
        "series": [{"name": "history", "type": "line", "data": hist_y},
                   {"name": "forecast", "type": "line", "smooth": True, "data": fut_y,
                    "lineStyle": {"type": "dashed"}}]}}


def _no_invented_numbers(text: str, value, question: str) -> bool:
    """True if every numeric token in `text` is the tool value or already appears in the
    question (e.g. a year) — i.e. the narration invented no figures (ADR-2)."""
    allowed = {str(value).replace(",", "")}
    allowed |= {t.replace(",", "") for t in re.findall(r"\d[\d,]*", question)}
    for tok in re.findall(r"\d[\d,]*", text):
        if tok.replace(",", "") not in allowed:
            return False
    return True


def compose_answer(question: str, columns: list[str], rows: list, lang: str) -> str:
    """Narrate the verified result. Numbers come ONLY from `rows`; a scalar answer is
    guarded so the LLM cannot introduce any figure other than the tool's value."""
    if not rows:
        return _fallback(columns, rows, lang)
    lang_name = "Kannada" if lang == "kn" else "English"
    scalar = len(rows) == 1 and len(columns) == 1
    if scalar and lang == "kn":
        # GLM's Kannada free-form narration is unreliable (can swap the subject); use a
        # safe template. The evidence drawer + chart carry the full context.
        return f"ಫಲಿತಾಂಶ: {rows[0][0]}"
    if scalar:
        value = rows[0][0]
        payload = f"The answer is exactly: {value}"
        rule = (f"Write ONE short factual sentence in {lang_name} answering the question, "
                f"containing the number {value}. Do NOT include any other number, "
                f"percentage, rate, per-lakh/per-capita figure, or population — only {value}.")
    else:
        preview = "; ".join(str(tuple(r)) for r in rows[:10])
        payload = f"Columns: {columns}\nRows (up to 10): {preview}"
        rule = (f"Write a concise 1-2 sentence answer in {lang_name} using ONLY the values "
                f"above. Do not invent numbers.")
    try:
        res = adapter.chat(
            [{"role": "user", "content": f"Question: {question}\n{payload}\n\n{rule}"}],
            system="You are a Karnataka State Police crime-data analyst. Use only the "
                   "provided values; never invent statistics.",
            temperature=0.0, max_tokens=140)
        text = (res.text or "").strip()
        if not text:
            return _fallback(columns, rows, lang)
        if scalar and not _no_invented_numbers(text, rows[0][0], question):
            log.warning("scalar narration introduced extra numbers; using template")
            return _fallback(columns, rows, lang)
        return text
    except Exception as exc:  # never surface a stack trace
        log.warning("compose_answer LLM failed: %s", exc)
        return _fallback(columns, rows, lang)
