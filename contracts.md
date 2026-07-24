# contracts.md — API & Tool Contracts (FROZEN)

Any change to this file requires human sign-off. Claude Code sessions build
**against** these shapes; they do not invent fields.

Conventions: JSON snake_case; timestamps ISO-8601 IST; all list endpoints accept
`?limit=` (default 50); every authenticated request carries the session user whose
`role` drives scope injection (see RBAC below).

---

## 1. Auth & roles

Three seeded users (Catalyst Authentication):

| user | role | scope |
|---|---|---|
| sho.jayanagar@demo | SHO | PoliceStationID = their station only |
| sp.tumakuru@demo | SP | DistrictID = their district only |
| dir.scrb@demo | SCRB | statewide, full PII |

A fourth mode: role `ANALYST` (statewide, PII masked: names → initials, ages →
bands). Scope enforcement is server-side WHERE injection in the tool layer (ADR-8).

`GET /api/me` → `{user_id, name, role, station_id?, district_id?}`

---

## 2. Chat

`POST /api/chat`
```json
{ "session_id": "s-123", "message": "How many chain snatching cases in Bengaluru City this year?", "lang": "en|kn" }
```
Response:
```json
{
  "answer_text": "...",                      // narrated answer (lang matches input)
  "render_specs": [ { "type": "line|bar|table|map|graph",
                      "title": "...",
                      "echarts_option": {},   // for line/bar/graph
                      "leaflet_spec": {},     // for map: {center,zoom,layers:[{kind:heat|markers, points:[]}]}
                      "table": {"columns": [], "rows": []} } ],
  "evidence": { "tool": "run_sql|hotspots|forecast|network|risk_score|similar_cases|linkage_scan",
                "sql": "SELECT ...",          // when tool = run_sql
                "row_count": 42,
                "case_ids": [101, 102],
                "params": {} },
  "followup_context": "opaque-string",        // client echoes back next turn
  "confidence": "high|medium|low",
  "audit_id": 991
}
```
Errors: `{ "error": "explanation", "suggestion": "rephrase hint" }` — never a stack trace.

`POST /api/chat/export` `{session_id}` → `{pdf_url}` (SmartBrowz → Stratus).

---

## 3. Series (linkage engine)

`GET /api/series` → `[SeriesHypothesis]` (scored desc).
`GET /api/series/{series_id}` → full detail.
`POST /api/series/rescan` → recompute (admin/demo use).

```json
SeriesHypothesis = {
  "series_id": "SH-07",
  "name": "Two-wheeler chain-snatching series — Bengaluru/Tumakuru/Mandya",
  "case_ids": [/* 12-14 ids */],
  "confidence": 0.91,
  "mo_summary": "Two men on motorcycle; pillion snatches gold chain from women walking alone; 18:00-21:00",
  "crime_sub_head": "Chain Snatching",
  "districts": ["Bengaluru City", "Tumakuru", "Mandya"],
  "time_span": {"from": "2026-01-14", "to": "2026-07-05"},
  "links": [ { "case_a": 101, "case_b": 214,
               "cosine": 0.88,
               "shared_features": ["tod_bucket:evening", "vehicle:motorcycle", "target:gold_chain"],
               "evidence_phrases": ["snatched her gold chain", "two persons on a black motorcycle"] } ],
  "linked_person_keys": ["P-004412", "P-004413"],
  "status": "open|confirmed|rejected"
}
```
`POST /api/series/{id}/feedback` `{verdict: "confirm|reject", note}` → stored as label.

---

## 4. Investigation Cell

`POST /api/investigate` `{series_id}` (or `{case_id}`) → `{"run_id": "r-1"}`
`GET /api/investigate/{run_id}/stream` → **SSE**, events in order:

```json
{ "event": "agent_step",
  "data": { "agent": "case_officer|records_analyst|network_specialist|crime_historian|legal_advisor|forecaster",
            "status": "started|tool_call|verified|done",
            "thought_summary": "one line, human-readable",
            "tool_call": {"tool": "run_sql", "params": {}},
            "result_ref": "pack.sections.timeline" } }
{ "event": "pack_ready", "data": { "pack_id": "pk-9", "pdf_url": "https://..." } }
```

```json
InvestigationPack = {
  "pack_id": "pk-9",
  "series_id": "SH-07",
  "summary": "...",
  "timeline": [ {"date": "...", "case_id": 101, "event": "FIR registered — Jayanagar PS"} ],
  "network_exhibit": GraphResult,
  "suspects_ranked": [ { "person_key": "P-004412", "name": "...",
                         "risk": {"score": 0.87,
                                  "components": {"recency": 0.9, "frequency": 0.8, "gravity": 0.7, "centrality": 0.95},
                                  "explanation": "..." },
                         "history_case_ids": [] } ],
  "leads": [ {"rank": 1, "lead": "...", "evidence_case_ids": [], "rationale": "..."} ],
  "legal": { "sections_invoked": [{"act": "BNS", "section": "304(2)", "desc": "..."}],
             "elements_check": [{"section": "...", "element": "...", "status": "present|missing", "source": "..."}] },
  "forecast": {"next_window": "...", "areas": [{"h3": "...", "district": "...", "prob": 0.7}]},
  "generated_at": "...", "generated_by_role": "SP"
}
```

---

## 5. Leads (Night Patrol)

`GET /api/leads` → `[LeadCard]` · `POST /api/leads/run` → run detectors now (demo).
```json
LeadCard = {
  "lead_id": "L-31", "type": "spike|series_growth|repeat_offender",
  "title": "Vehicle theft 3.1x seasonal baseline — Whitefield sub-division",
  "evidence": {"metric": "stl_residual_z", "value": 3.1, "window": "last 14d", "case_ids": []},
  "confidence": 0.84,
  "suggested_action": "Increase night patrols 22:00-02:00 in cells [...]",
  "district": "Bengaluru City", "created_at": "..."
}
```

---

## 6. Graph

`POST /api/graph/query`
```json
{ "type": "path_between|ego_network|community_of",
  "params": { "person_a": "P-004412", "person_b": "P-009001",   // path_between
              "person_key": "P-004412", "depth": 2,             // ego_network
              "case_id": 214 } }                                 // community_of
```
```json
GraphResult = {
  "nodes": [ {"id": "P-004412", "kind": "person|case|location|ps", "label": "...", "meta": {}} ],
  "edges": [ {"a": "P-004412", "b": "C-101", "kind": "accused_in|co_accused|arrested_with|same_address|same_series", "meta": {}} ],
  "highlight_path": ["P-004412", "C-101", "P-004413"],
  "communities": [ {"community_id": 3, "person_keys": [], "label": "candidate ring"} ],
  "narrative": "one-paragraph explanation of what the graph shows"
}
```

---

## 7. Tool contracts (internal — the ONLY way agents/chat touch data)

| tool | params | returns |
|---|---|---|
| run_sql | `{sql}` (SELECT-only; guardrails validate) | `{columns, rows, row_count, truncated}` |
| hotspots | `{crime_sub_head?, district?, date_from, date_to, h3_res:8}` | `{cells:[{h3, count, intensity, lat, lon}]}` |
| forecast | `{district, crime_sub_head, horizon_weeks:8}` | `{history:[{week,count}], forecast:[{week,mean,lo,hi}], backtest_mae, baseline_mae}` |
| risk_score | `{person_key}` | `{score, components{recency,frequency,gravity,centrality}, explanation, history_case_ids}` |
| similar_cases | `{case_id, k:5}` | `[{case_id, similarity, summary}]` |
| network | `{person_key|case_id, depth:2}` | `GraphResult` |
| linkage_scan | `{case_id?}` (absent = full rescan) | `[SeriesHypothesis]` |

Guardrail invariants (nl2sql + run_sql): parse with sqlglot; reject anything but a
single SELECT; auto-append `LIMIT 500` if missing; strip comments; schema-validate
identifiers; inject role scope WHERE; log to audit.

---

## 8. Audit

`GET /api/audit?limit=100` (SCRB only) → `[{ts, user_id, role, action, detail}]`.
Every chat turn, investigation, export and role switch writes one row (DuckDB +
Catalyst NoSQL).

---

## 9. Eval formats

`eval/questions.yaml`:
```yaml
- id: q01
  lang: en
  question: "How many chain snatching cases were registered in Bengaluru City in 2026?"
  gold_sql: "SELECT COUNT(*) FROM vw_case_360 WHERE crime_sub_head='Chain Snatching' AND district='Bengaluru City' AND YEAR(CrimeRegisteredDate)=2026"
  expect: scalar          # scalar | rows | chart
- id: q41
  lang: kn
  question: "ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?"
  gold_sql: "..."
  expect: scalar
```
Scoring: execute generated SQL and gold SQL; compare result sets (order-insensitive,
float tolerance 1e-6). Report per-language accuracy + failure list.

`eval/linkage_test.py`: loads planted truth from demo_story.md tables; reports
precision/recall at hypothesis level and at pair level; asserts precision ≥0.8.
