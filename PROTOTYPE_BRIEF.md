# ANVESHAK (ಅನ್ವೇಷಕ) — Prototype Brief

**KSP Datathon 2026 · Challenge 1: Intelligent Conversational AI for the KSP Crime Database · Team Zen**

- **Live app:** https://anveshak-api-50044329134.development.catalystappsail.in/ui/
- **GitHub:** https://github.com/arungeekay/anveshak
- **Deployed on:** Zoho Catalyst (exclusively)

---

## Problem statement addressed

Karnataka State Police hold millions of FIR/crime records across 31 districts, but
frontline officers cannot query them easily: the data is siloed by district, locked
behind SQL/CCTNS expertise, and English-only. Answering a simple question — "how many
chain-snatchings this year?", "are these cases connected?", "who's the network behind
this fraud?" — is slow, and cross-district serial crime routinely goes unnoticed.

Challenge 1 asks for an **intelligent conversational AI** over the crime database.
ANVESHAK delivers that — and goes further, turning the database into an autonomous
investigation partner.

## Key features and functionalities

1. **Conversational floor (bilingual, voice + text).** Officers ask in **English or
   Kannada**. ANVESHAK generates guard-railed SQL, runs it, and answers in natural
   language — with an **evidence drawer** (SQL + rows + case IDs) on every answer.
   *Deterministic tools compute; the LLM only narrates — so no number is ever
   hallucinated.*
2. **Serial Crime Linkage Engine.** MO fingerprinting via multilingual narrative
   embeddings + structured features (vehicle, target, time, geo), weighted cosine,
   HDBSCAN, and a 180-day / 120-km spatiotemporal filter — discovers serial crime
   **across district boundaries** (e.g. SH-07: 15 chain-snatchings, 3 districts,
   confidence 0.88).
3. **AI Investigation Cell.** A fixed six-agent pipeline (Case Officer → Records
   Analyst → Network Specialist → Crime Historian → Legal Advisor → Forecaster)
   **streams its reasoning live** and assembles a **court-ready Investigation Pack**:
   ranked suspects, evidence-cited leads, legal element checks, and a next-strike
   forecast.
4. **CrimeGraph.** A knowledge graph over people/cases with Louvain communities —
   multi-hop questions (ego-network, shortest path, community) surface hubs like the
   Prakash Rao investment-fraud web.
5. **Night Patrol.** Autonomous detectors (spike, series-growth, repeat-offender)
   produce ranked **Lead Cards** proactively.
6. **Court-ready outputs & governance.** Investigation Pack + conversation-to-PDF;
   RBAC scopes (SHO/SP/SCRB/analyst), audit logging, and a strict policy that
   **protected attributes (religion/caste) are never features** in any model (ADR-9).

## Technology stack

- **Backend:** Python 3.12, FastAPI, DuckDB (analytical mirror), sqlglot guardrails,
  sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`), scikit-learn /
  HDBSCAN, NetworkX + Louvain, statsmodels SARIMA, sse-starlette.
- **Frontend:** React 18, Vite, Tailwind, ECharts, Leaflet + OpenStreetMap, Web Speech
  API (`kn-IN` voice).
- **LLM:** GLM-4.7-Flash via **Catalyst QuickML LLM Serving** (no external inference
  API is ever called from the deployed app).
- **Platform (Zoho Catalyst):** AppSail (backend, custom Docker runtime), Web Client
  Hosting, QuickML, Data Store, NoSQL, API Gateway, Authentication, SmartBrowz, Cron,
  Signals + Mail, Cache, Stratus.

**Architecture note (ADR-1/2):** Catalyst Data Store is the system of record; on
startup ANVESHAK mirrors core tables into an embedded DuckDB for sub-second analytics.
The LLM routes to typed, deterministic tools and composes their verified outputs, so
every figure traces back to a tool result and a case-ID set.

## Measured results (synthetic dataset, seed 42 — ground truth is public)

| Metric | Result |
|---|---|
| Dataset | 15,405 FIRs · 31 districts · 248 stations · 2023–2026 |
| NL→SQL accuracy | 76.7% overall (EN 82.2%, KN 60.0%) on the local 7B dev model; gold-vs-gold 100% |
| Serial linkage (SH-07) | precision 0.86 · recall 12/14 |
| Forecast (burglary) | backtest MAE 1.83 vs seasonal-naive 1.75 |
| Repeat-offender risk | Suresh B 0.83 (explainable) |
| Robustness | thread-safe analytical layer — 60 concurrent requests, 0 errors |

## Proposed impact and use case

- **Faster, evidence-grounded answers** for any officer — no SQL, no analyst
  bottleneck, in their own language.
- **Cross-district serial-crime detection** that siloed records miss, so linked
  offenders are caught earlier.
- **Investigation acceleration:** a first-draft, court-style Investigation Pack in
  minutes instead of days, with every claim traceable to evidence.
- **Proactive policing:** Night Patrol surfaces spikes and repeat offenders before a
  complaint is even filed.
- **Trustworthy & fair by design:** verifiable evidence on every answer, audit trail,
  and no protected attributes in models — essential for public-sector deployment.

*Prototype uses synthetic data only; the real-world path is CCTNS integration with
identity resolution on name/parentage/DOB.*
