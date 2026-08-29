"""Fill the official KSP Datathon 2026 submission template with ANVESHAK content.

The template has a full-slide BLACK background image + a bold heading text box per
slide (the section prompt). We keep each heading as the slide title and add a light
(readable-on-black) body text box beneath it. All numbers are the measured ones from
README.md / eval / PROGRESS.log — no invented figures.

Run:  python scripts/build_deck.py
Out:  ANVESHAK_KSP_Datathon_2026_Submission.pptx
"""
from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

TEMPLATE = "KSP Datathon 2026 _ Prototype Submission Template (1).pptx"
OUT = "ANVESHAK_KSP_Datathon_2026_Submission.pptx"

LIVE_URL = "https://anveshak-api-50044329134.development.catalystappsail.in/ui/"
API_URL = "https://anveshak-api-50044329134.development.catalystappsail.in"
GITHUB = "https://github.com/arungeekay/anveshak"

# Palette tuned for the template's WHITE content background (dark text on white).
# (Names kept for minimal churn; "WHITE" now means the dark emphasis ink.)
WHITE = RGBColor(0x0B, 0x1F, 0x3A)    # dark navy — headings / emphasis
BODY = RGBColor(0x2B, 0x37, 0x4B)     # dark slate — body copy
ACCENT = RGBColor(0x1D, 0x4E, 0xD8)   # blue-700 — metrics / links / emphasis
MUTED = RGBColor(0x64, 0x74, 0x8B)    # slate-500 — captions / placeholders
GOOD = RGBColor(0x04, 0x78, 0x55)     # emerald-700 — live / confirmed

# body text box geometry (below the heading), in inches
BODY_LEFT, BODY_TOP, BODY_W, BODY_H = 0.55, 1.55, 8.95, 3.75


def add_body(slide):
    # The template's prompt box sometimes carries multi-line guidance (e.g. the
    # Opportunities sub-questions, the Links numbered list) that would sit right where
    # our body goes. Trim that box to just its first line (the section title) so our
    # body never collides with leftover prompt text.
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            for p in list(sh.text_frame.paragraphs)[1:]:
                p._p.getparent().remove(p._p)
            break
    tb = slide.shapes.add_textbox(
        Emu(int(BODY_LEFT * 914400)), Emu(int(BODY_TOP * 914400)),
        Emu(int(BODY_W * 914400)), Emu(int(BODY_H * 914400)))
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def para(tf, text, *, size=12, color=BODY, bold=False, level=0, bullet=False,
         space=4, first=False):
    if first:
        p = tf.paragraphs[0]
        for r in list(p.runs):  # clear any existing runs on the reused paragraph
            r._r.getparent().remove(r._r)
    else:
        p = tf.add_paragraph()
    p.level = level
    p.space_after = Pt(space)
    runs = text if isinstance(text, list) else [(text, color, bold)]
    for i, item in enumerate(runs):
        t, c, b = item if isinstance(item, tuple) else (item, color, bold)
        r = p.add_run()
        r.text = ("• " if bullet and i == 0 else "") + t
        r.font.size = Pt(size)
        r.font.color.rgb = c
        r.font.bold = b
        r.font.name = "Calibri"
    return p


SHOTS = [
    ("video/shots/01_leadfeed.png", "Night Patrol — proactive leads"),
    ("video/shots/02_chat_evidence.png", "Chat — answer + evidence (SQL)"),
    ("video/shots/03_series.png", "Serial linkage — SH-07"),
    ("video/shots/04_pack.png", "Investigation Pack — 6 agents"),
    ("video/shots/05_graph.png", "CrimeGraph — fraud hub"),
    ("video/shots/06_kannada.png", "Bilingual — ಕನ್ನಡ + English"),
]


def _place_shots(slide):
    """Lay the six live-app screenshots in a 3x2 grid with captions under each."""
    import os as _os
    EMU = 914400
    cols, gap = 3, 0.18
    left0, top0 = 0.35, 1.48
    iw = (9.3 - gap * (cols - 1)) / cols          # image width in inches
    ih = iw * 9 / 16                               # 16:9
    cap_h, row_gap = 0.26, 0.16
    for i, (path, caption) in enumerate(SHOTS):
        if not _os.path.exists(path):
            continue
        r, c = divmod(i, cols)
        x = left0 + c * (iw + gap)
        y = top0 + r * (ih + cap_h + row_gap)
        slide.shapes.add_picture(path, Emu(int(x * EMU)), Emu(int(y * EMU)),
                                 Emu(int(iw * EMU)), Emu(int(ih * EMU)))
        tb = slide.shapes.add_textbox(Emu(int(x * EMU)), Emu(int((y + ih + 0.01) * EMU)),
                                      Emu(int(iw * EMU)), Emu(int(cap_h * EMU)))
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r0 = p.add_run()
        r0.text = caption
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = BODY
        r0.font.name = "Calibri"


def _delete_slide_by_text(prs, marker):
    """Remove the first slide whose text equals `marker` (e.g. the 'Blank slide')."""
    for i, s in enumerate(prs.slides):
        if any(sh.has_text_frame and sh.text_frame.text.strip() == marker for sh in s.shapes):
            lst = prs.slides._sldIdLst
            lst.remove(list(lst)[i])
            return True
    return False


def fill_team(slide):
    """Slide 0: replace the Team Details prompt lines with our values."""
    box = next(s for s in slide.shapes if s.has_text_frame and "Team Details" in s.text_frame.text)
    tf = box.text_frame
    lines = [
        ("Team Details", WHITE, True, 17),
        ("", BODY, False, 6),
        ("Team name:  Team Zen", BODY, False, 14),
        ("Team leader name:  Hiran Vikraman S R", BODY, False, 14),
        ("Team size:  2   (Hiran Vikraman S R · Arun G K)", BODY, False, 14),
        ("Problem Statement:  Challenge 1 — Intelligent Conversational AI for the "
         "KSP Crime Database. Enable officers to query the FIR/crime database in "
         "natural language (English & Kannada) and get accurate, evidence-grounded "
         "answers.", BODY, False, 13),
    ]
    tf.clear()  # leaves a single empty paragraph
    for i, (text, color, bold, size) in enumerate(lines):
        para(tf, text, size=size, color=color, bold=bold, first=(i == 0))


def main():
    prs = Presentation(TEMPLATE)
    S = prs.slides

    fill_team(S[0])

    # Slide 1 — Brief about the solution
    tf = add_body(S[1])
    para(tf, [("ANVESHAK (ಅನ್ವೇಷಕ", WHITE, True), (" = “the investigator”) turns the KSP "
              "crime database into an ", BODY, False),
              ("AI investigation partner", WHITE, True),
              (" — not just a chatbot.", BODY, False)], size=13, first=True, space=8)
    para(tf, [("Ask in Kannada or English, by voice or text — get an answer in seconds, ", BODY, False),
              ("with the evidence", WHITE, True), (" (SQL + rows + case IDs) attached. No SQL "
              "skills, no analyst queue.", BODY, False)], bullet=True)
    para(tf, [("Deterministic tools compute; the LLM only narrates", WHITE, True),
              (" — every number traces to a tool result. Zero hallucinated statistics — "
               "essential for policing.", BODY, False)], bullet=True)
    para(tf, "It doesn’t stop at answers — it works cases: links serial crime across "
             "districts, runs a 6-agent cell that assembles court-ready packs, traverses a "
             "crime knowledge graph, and sweeps overnight to raise leads before anyone asks.",
         bullet=True)
    para(tf, [("Impact: minutes instead of days, catches siloed records miss, and "
               "proactive leads every morning. ", WHITE, True),
              ("Runs 100% on Zoho Catalyst.", GOOD, True)], bullet=True, space=2)

    # Slide 2 — Opportunities / differentiation / USP
    tf = add_body(S[2])
    para(tf, "How it is different, and how it solves the problem:", size=12, color=WHITE,
         bold=True, first=True, space=8)
    para(tf, "Most “crime chatbots” stop at NL→SQL. ANVESHAK adds an "
             "investigation layer: cross-district serial linkage, multi-agent case work, "
             "and proactive patrol.", bullet=True)
    para(tf, [("Trust by construction: ", WHITE, True),
              ("the LLM never invents numbers (deterministic tools + evidence drawer), and "
               "the linkage ground truth is public so results are independently verifiable.", BODY, False)],
         bullet=True)
    para(tf, [("Cross-district reach: ", WHITE, True),
              ("MO fingerprinting via multilingual embeddings finds serial offenders that "
               "siloed district records miss.", BODY, False)], bullet=True)
    para(tf, [("Built for real officers: ", WHITE, True),
              ("bilingual (Kannada + English) with browser voice, government-grade UI.", BODY, False)],
         bullet=True)
    para(tf, [("Where it makes a difference: ", WHITE, True),
              ("a constable at a rural station gets a statewide answer in Kannada in "
               "seconds · an SP spots a serial ring crossing Mandya into Bengaluru before "
               "the next strike · an IO gets a first-draft, court-ready pack in minutes · "
               "a control room sees tomorrow’s hotspot tonight.", BODY, False)], size=11, space=6)
    para(tf, [("USP:  ", ACCENT, True),
              ("“Ask a question, get a verified answer with evidence — and let the AI "
               "work the case end-to-end to a court-ready pack.”", WHITE, False)], size=11.5, space=2)

    # Slide 3 — List of features
    tf = add_body(S[3])
    feats = [
        ("Conversational floor", " — bilingual EN + Kannada, voice + text, verified NL→SQL with evidence drawer on every answer."),
        ("Serial Crime Linkage Engine", " — MO fingerprinting (multilingual embeddings + structured features), weighted cosine, HDBSCAN, 180-day / 120-km filter; discovers cross-district series cold."),
        ("AI Investigation Cell", " — 6 agents stream their reasoning over SSE → court-ready Investigation Pack (PDF)."),
        ("CrimeGraph", " — knowledge graph over people/cases; ego-network, shortest path, Louvain communities for multi-hop questions."),
        ("Night Patrol", " — spike / series-growth / repeat-offender detectors → ranked Lead Cards, autonomously."),
        ("Court-ready outputs", " — Investigation Pack + conversation-to-PDF via SmartBrowz."),
        ("Governance", " — RBAC scopes (SHO/SP/SCRB/analyst), audit log, and no protected attributes (religion/caste) in any model (ADR-9)."),
    ]
    for i, (h, rest) in enumerate(feats):
        para(tf, [(f"{i+1}. {h}", WHITE, True), (rest, BODY, False)], size=11.5, space=5,
             first=(i == 0))

    # Slide 4 — Process flow / use-case
    tf = add_body(S[4])
    para(tf, "Officer (EN/KN, voice or text)  →  React SPA  →  FastAPI intent router:",
         size=12, color=WHITE, bold=True, first=True, space=8)
    para(tf, [("NL→SQL path: ", ACCENT, True),
              ("schema card + few-shots → sqlglot guardrails (SELECT-only, auto-LIMIT, "
               "self-repair) → DuckDB → answer + evidence drawer.", BODY, False)], bullet=True)
    para(tf, [("Tool path: ", ACCENT, True),
              ("linkage / graph / forecast / hotspots / risk / similar → DuckDB → "
               "verified result → LLM narrates.", BODY, False)], bullet=True)
    para(tf, [("Investigation: ", ACCENT, True),
              ("“Investigate SH-07” → 6-agent pipeline (SSE) → Investigation "
               "Pack → SmartBrowz PDF.", BODY, False)], bullet=True)
    para(tf, [("Autonomous: ", ACCENT, True),
              ("Cron → Night Patrol detectors → Lead Cards → Signals / Mail digest.", BODY, False)],
         bullet=True)
    para(tf, [("Two data layers (ADR-1): ", WHITE, True),
              ("Catalyst Data Store = system of record; an embedded DuckDB analytical "
               "mirror serves sub-second analytics.", BODY, False)], size=11, space=2)

    # Slide 5 — Wireframes / mock
    tf = add_body(S[5])
    para(tf, "Six views in the live prototype (government-grade dark theme):", size=12,
         color=WHITE, bold=True, first=True, space=8)
    for h, rest in [
        ("Chat", " — bilingual answer + evidence drawer (SQL, rows, case IDs) + voice input."),
        ("Lead Feed", " — ranked Night-Patrol Lead Cards."),
        ("Series", " — discovered serial-crime hypotheses with confidence + linked case IDs."),
        ("CrimeGraph", " — interactive people/case network with community highlighting."),
        ("Investigation Room", " — six agent cards stream live, then the assembled pack."),
        ("Audit", " — every action logged (user, role, action, detail)."),
    ]:
        para(tf, [(h, WHITE, True), (rest, BODY, False)], bullet=True, size=11.5)
    para(tf, f"Live: {LIVE_URL}", size=11, color=ACCENT, space=2)

    # Slide 6 — Architecture
    tf = add_body(S[6])
    flow = [
        "Officer (EN/KN, voice+text)",
        "React SPA  (served on Catalyst)",
        "FastAPI backend on Catalyst AppSail  →  intent router",
        "  ⤷  NL→SQL (guardrails + self-repair)   and   typed tools",
        "        (linkage · graph · forecast · hotspots · risk · similar)",
        "DuckDB analytical mirror  ⟷  Catalyst Data Store (system of record)",
        "LLM adapter  →  Catalyst QuickML  →  GLM-4.7-Flash",
        "6-agent Investigation Cell (SSE)  →  SmartBrowz  →  Pack PDF",
        "Cron  →  Night Patrol detectors  →  Lead Cards",
    ]
    for i, line in enumerate(flow):
        indent = line.startswith(" ")
        para(tf, line.strip(), size=11, color=(MUTED if indent else BODY),
             bold=False, first=(i == 0), space=3)
    para(tf, [("Deterministic tools, LLM narrates (ADR-2). ", WHITE, True),
              ("No external inference API is ever called from the deployed app (ADR-4).", BODY, False)],
         size=10.5, space=2)

    # Slide 7 — Technologies
    tf = add_body(S[7])
    for h, rest in [
        ("Backend", "Python 3.12, FastAPI, DuckDB, sqlglot, sentence-transformers "
                    "(paraphrase-multilingual-MiniLM-L12-v2), scikit-learn / HDBSCAN, "
                    "NetworkX + Louvain, statsmodels SARIMA, sse-starlette."),
        ("Frontend", "React 18, Vite, Tailwind CSS, ECharts (charts + network graph), "
                     "Leaflet + OpenStreetMap, Web Speech API (kn-IN voice)."),
        ("LLM", "GLM-4.7-Flash served via Catalyst QuickML LLM Serving."),
        ("Packaging", "Docker (custom AppSail runtime — bakes the scientific stack)."),
        ("Quality", "pytest suite (46 tests), bilingual eval harness (60 questions), "
                    "public linkage ground truth."),
    ]:
        para(tf, [(f"{h}:  ", WHITE, True), (rest, BODY, False)], size=11.5, space=6,
             first=(h == "Backend"))

    # Slide 8 — Catalyst services
    tf = add_body(S[8])
    para(tf, [("Live now:  ", GOOD, True),
              ("AppSail (FastAPI, custom Docker runtime)  ·  QuickML LLM Serving "
               "(GLM-4.7-Flash)  ·  Web Client Hosting  ·  Authentication  ·  API Gateway.", BODY, False)],
         size=11.5, first=True, space=8)
    para(tf, [("In the architecture / provisioned:  ", ACCENT, True),
              ("Data Store (system of record)  ·  NoSQL (graph snapshots)  ·  SmartBrowz "
               "(pack PDF)  ·  Cron (Night Patrol)  ·  Signals + Mail (lead digests)  ·  "
               "Cache  ·  Stratus (pack storage).", BODY, False)], size=11.5, space=8)
    para(tf, "Deployment is exclusively on Zoho Catalyst, per the competition mandate.",
         size=11, color=WHITE, bold=True, space=2)

    # Slide 9 — Estimated cost (optional)
    tf = add_body(S[9])
    para(tf, "The prototype runs within the Catalyst development tier.", size=12,
         color=WHITE, bold=True, first=True, space=8)
    para(tf, "AppSail: 1 GB memory, single instance (custom Docker runtime).", bullet=True)
    para(tf, "QuickML: GLM-4.7-Flash is a Zoho-hosted shared model — no per-model "
             "deployment cost; billed per token at production scale.", bullet=True)
    para(tf, "Web Client Hosting + Data Store + Cron: serverless, usage-based.", bullet=True)
    para(tf, "Embeddings are precomputed at data-generation time, so runtime needs no "
             "GPU / heavy inference for search.", bullet=True)

    # Slide 10 — Snapshots (real screenshots of the live app in a 3x2 grid)
    _place_shots(S[10])

    # Slide 11 — Performance / benchmarking
    tf = add_body(S[11])
    rows = [
        ("Dataset", "15,405 FIRs · 31 districts · 248 stations · 2023–2026 (synthetic, seed 42)."),
        ("NL→SQL accuracy", "76.7% overall (EN 82.2%, KN 60.0%) on the local 7B dev model; gold-vs-gold 100%. Production GLM-4.7-Flash is expected higher."),
        ("Serial linkage (SH-07)", "precision 0.86 · recall 12/14; the disjoint SP-2 series correctly not merged."),
        ("Forecast (burglary)", "backtest MAE 1.83 vs seasonal-naive 1.75 — competitive and honestly reported."),
        ("Repeat-offender risk", "Suresh B scores 0.83 (recency / frequency / gravity / centrality)."),
        ("Night Patrol", "Whitefield spike + repeat-offender cluster fire on the planted anomalies."),
        ("Robustness", "thread-safe analytical layer — 60 concurrent requests, 0 errors; caches pre-warmed at startup."),
    ]
    for i, (h, rest) in enumerate(rows):
        para(tf, [(f"{h}:  ", WHITE, True), (rest, BODY, False)], size=11, space=5,
             first=(i == 0))
    para(tf, "Linkage ground truth is public (data_engine/planted/*.yaml) — numbers are "
             "independently verifiable.", size=10, color=MUTED, space=2)

    # Slide 12 — Links
    tf = add_body(S[12])
    para(tf, [("GitHub (public):  ", WHITE, True), (GITHUB, ACCENT, False)], size=13,
         first=True, space=10)
    para(tf, [("Deployed link (Catalyst):  ", WHITE, True), (LIVE_URL, ACCENT, False)],
         size=13, space=10)
    para(tf, [("Demo video (3 min):  ", WHITE, True), ("(add your public YouTube / Drive link)", MUTED, False)],
         size=13, space=10)
    para(tf, f"API base: {API_URL}", size=10, color=MUTED, space=2)

    # Slide 13 — Additional / future development
    tf = add_body(S[13])
    para(tf, "Roadmap to production:", size=12, color=WHITE, bold=True, first=True, space=8)
    for line in [
        "RBAC server-side scope injection (designed, ADR-8) → full enforcement via Catalyst Auth.",
        "Live Data Store loader + FIR-intake write-back; NoSQL graph persistence.",
        "SmartBrowz pack PDF, Cron schedule, and Signals / Mail digests fully wired end-to-end.",
        "Real CCTNS identity resolution (name / parentage / DOB) replacing the synthetic person_key.",
        "Kannada NL→SQL tuning (hand-curated few-shots) to lift KN accuracy toward the EN level.",
        "Human-in-the-loop feedback on linkage / leads to continuously improve precision.",
    ]:
        para(tf, line, bullet=True, size=11.5, color=BODY)

    removed = _delete_slide_by_text(prs, "Blank slide")
    prs.save(OUT)
    print(f"wrote {OUT}  ({len(prs.slides)} slides, blank removed={removed})")


if __name__ == "__main__":
    main()
