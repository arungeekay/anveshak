"""Render an InvestigationPack to court-style HTML.

This HTML is what Catalyst SmartBrowz will convert to PDF (that conversion is the
deferred Catalyst step); the HTML itself is viewable now.
"""
from __future__ import annotations

import html


def _esc(v) -> str:
    return html.escape(str(v))


def render_pack_html(pack: dict) -> str:
    if not pack:
        return "<h1>Investigation pack unavailable</h1>"
    tl = "".join(f"<tr><td>{_esc(e['date'])}</td><td>{_esc(e['case_id'])}</td>"
                 f"<td>{_esc(e['event'])}</td></tr>" for e in pack.get("timeline", []))
    suspects = ""
    for s in pack.get("suspects_ranked", [])[:6]:
        r = s["risk"]
        comps = "".join(
            f"<span class='bar'><i style='width:{int(v * 100)}%'></i>{_esc(k)}</span>"
            for k, v in r["components"].items())
        suspects += (f"<div class='suspect'><b>{_esc(s['name'])}</b> "
                     f"<span class='pk'>{_esc(s['person_key'])}</span> "
                     f"<span class='score'>risk {r['score']}</span><div>{comps}</div>"
                     f"<div class='muted'>{_esc(r['explanation'])}</div></div>")
    leads = "".join(f"<li><b>#{_esc(ld['rank'])}</b> {_esc(ld['lead'])} "
                    f"<span class='muted'>— {_esc(ld['rationale'])}</span></li>"
                    for ld in pack.get("leads", []))
    legal = pack.get("legal", {})
    sections = ", ".join(f"{_esc(s['act'])} {_esc(s['section'])}"
                         for s in legal.get("sections_invoked", []))
    checks = "".join(
        f"<tr class='{_esc(e['status'])}'><td>{_esc(e['section'])}</td>"
        f"<td>{_esc(e['element'])}</td><td>{_esc(e['status'])}</td>"
        f"<td>{_esc(e['source'])}</td></tr>" for e in legal.get("elements_check", []))
    fc = pack.get("forecast", {})
    areas = ", ".join(_esc(a["h3"]) for a in fc.get("areas", []))

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    body{{font-family:'Segoe UI',Arial,sans-serif;color:#0f1830;margin:32px;font-size:13px}}
    h1{{font-size:20px;border-bottom:3px solid #1e3a5f;padding-bottom:6px}}
    h2{{font-size:15px;color:#1e3a5f;margin-top:22px}}
    .header{{display:flex;justify-content:space-between;align-items:center}}
    .badge{{background:#1e3a5f;color:#fff;padding:4px 10px;border-radius:4px;font-size:11px}}
    table{{width:100%;border-collapse:collapse;margin-top:8px}}
    td,th{{border:1px solid #cbd5e1;padding:5px 8px;text-align:left}}
    .muted{{color:#64748b;font-size:11px}}
    .suspect{{border:1px solid #e2e8f0;border-radius:6px;padding:8px;margin:6px 0}}
    .pk{{color:#64748b;font-size:11px}} .score{{float:right;font-weight:bold;color:#b91c1c}}
    .bar{{display:inline-block;width:120px;font-size:10px;color:#334155;margin:2px 6px 2px 0}}
    .bar i{{display:block;height:5px;background:#3b82f6;border-radius:3px}}
    tr.missing{{background:#fef2f2}} tr.present{{background:#f0fdf4}}
    </style></head><body>
    <div class="header"><h1>ANVESHAK · Investigation Pack</h1>
      <span class="badge">Karnataka State Police · ಕರ್ನಾಟಕ ರಾಜ್ಯ ಪೊಲೀಸ್</span></div>
    <p><b>Series / ಸರಣಿ:</b> {_esc(pack.get('series_id'))} &nbsp;
       <b>Generated:</b> {_esc(pack.get('generated_at', ''))} ({_esc(pack.get('generated_by_role', ''))})</p>
    <h2>Summary / ಸಾರಾಂಶ</h2><p>{_esc(pack.get('summary', ''))}</p>
    <h2>Timeline / ಕಾಲಾನುಕ್ರಮ</h2>
    <table><tr><th>Date</th><th>Case</th><th>Event</th></tr>{tl}</table>
    <h2>Ranked Suspects / ಶಂಕಿತರು</h2>{suspects or '<p class="muted">None identified.</p>'}
    <h2>Leads / ಸುಳಿವುಗಳು</h2><ol>{leads}</ol>
    <h2>Legal / ಕಾನೂನು</h2><p><b>Sections invoked:</b> {sections}</p>
    <table><tr><th>Section</th><th>Ingredient</th><th>Status</th><th>Source</th></tr>{checks}</table>
    <h2>Forecast / ಮುನ್ಸೂಚನೆ</h2>
    <p>Next likely window: <b>{_esc(fc.get('next_window', ''))}</b>. Priority cells: {areas}</p>
    </body></html>"""
