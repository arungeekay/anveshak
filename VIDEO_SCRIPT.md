# ANVESHAK — 3-Minute Demo Video Script (turnkey recording guide)

> This is a shot-by-shot script to **screen-record the live app yourself** (a screen
> recording of the real working prototype is what the judges must see — it can't be
> faked or auto-generated). Follow it top to bottom; it runs ~2:55. Every query and
> every expected result below was verified on the live deployment.

**Live app:** https://anveshak-api-50044329134.development.catalystappsail.in/ui/

---

## Before you hit Record (2-minute prep — important)

1. **Warm the app.** Open the live link and click **Series** and **Lead Feed** once.
   The first load of heavy views takes ~30–60s while caches warm; after that every
   view is instant. Wait until Series shows cards, then you're warm for the whole take.
2. **Browser:** Chrome, full-screen (F11) or a clean window. Zoom to ~110% (Ctrl +) so
   text reads on video. Close unrelated tabs. Hide bookmarks bar.
3. **Voice step (optional):** grant mic permission and have a Kannada/English system
   voice available if you'll demo voice input.
4. **Recorder:** OBS / Loom / Xbox Game Bar (Win+G) at 1080p, 30 fps. Record system
   audio + mic if narrating live (or add voiceover after).
5. **Screenshots for the deck:** while you're here, capture the 6 shots listed in
   deck slide 10.

On-screen captions: burn in the **CAPTION** lines (a lower-third title works well).
Read the **VO** lines as narration. Keep total **under 3:00**.

---

## Scene 1 — Cold open: the AI is already working (0:00–0:20)

- **Screen:** Land on **Lead Feed**. Three Lead Cards are visible: a Whitefield
  **spike**, a **repeat-offender**, and a **series-growth** card.
- **CAPTION:** `ANVESHAK · Autonomous AI Investigation Bureau for Karnataka State Police`
- **VO:** "This is ANVESHAK. Before any officer asks a question, its Night Patrol has
  already swept the state overnight and raised leads — a crime spike in Whitefield, a
  repeat offender back in his old area, and a growing crime series."

## Scene 2 — Ask in plain English, get verified evidence (0:20–0:50)

- **Screen:** Go to **Chat**. Type:
  `How many chain snatching cases were registered in Bengaluru City in 2026?`
  → Answer: **"There were 47 chain snatching cases in Bengaluru City in 2026."**
  Open the **evidence drawer** (SQL + row count + case IDs).
- **CAPTION:** `Every answer is grounded in verified SQL — not a guess`
- **VO:** "Officers just ask. ANVESHAK writes the SQL, runs it, and answers in plain
  language — and every number comes with its evidence: the exact query, the rows, the
  case IDs. The AI never invents a statistic."

## Scene 3 — It understands follow-ups and visualizes (0:50–1:10)

- **Screen:** Type: `Show the monthly trend of chain snatching in Bengaluru City for 2026`
  → a **line chart** renders. Then: `Which police stations are worst affected?`
  → a **ranked bar chart / table** (Jayanagar PS on top).
- **CAPTION:** `Trends, hotspots, rankings — on demand`
- **VO:** "It turns questions into charts and rankings on the fly — the monthly trend,
  then the worst-hit police stations, led by Jayanagar."

## Scene 4 — Serial-crime linkage across districts (1:10–1:35)

- **Screen:** Go to **Series**. Point to **SH-07 — Chain Snatching**, **confidence
  0.88**, **15 linked cases across 3 districts**.
- **CAPTION:** `Serial Crime Linkage — finds MO fingerprints across district lines`
- **VO:** "Here's the flagship. ANVESHAK fingerprints modus operandi from case
  narratives and structured clues — and discovers that fifteen chain-snatchings across
  three different districts are one serial ring. No human connected these; the engine
  found it cold."

## Scene 5 — The AI Investigation Cell (1:35–2:15) — the centerpiece

- **Screen:** Open **Investigation Room** (SH-07 pre-filled) → click **Investigate**.
  Six agent cards stream in order — **Case Officer → Records Analyst → Network
  Specialist → Crime Historian → Legal Advisor → Forecaster** — each showing its
  reasoning. Then the **Investigation Pack** assembles: ranked suspects, leads, legal
  section/element checks, and a forecast. Click **Open pack**.
- **CAPTION:** `Six AI agents work the case → a court-ready Investigation Pack`
- **VO:** "Now watch it work the case. Six specialist agents run in sequence, streaming
  their reasoning live — pulling records, mapping the network, checking legal elements,
  and forecasting the next strike. In under two minutes they assemble a court-ready
  Investigation Pack: ranked suspects, actionable leads, and the legal checklist."

## Scene 6 — CrimeGraph: multi-hop network questions (2:15–2:35)

- **Screen:** Go to **CrimeGraph** (or Chat: `Show Prakash Rao's network`). The
  **Prakash Rao hub** renders — a 29-node investment-fraud web, community highlighted.
- **CAPTION:** `CrimeGraph — multi-hop questions over a crime knowledge graph`
- **VO:** "Ask about a person and ANVESHAK traverses its crime knowledge graph —
  exposing Prakash Rao as the hub of an investment-fraud web linking dozens of cases."

## Scene 7 — Bilingual: Kannada in, Kannada out (2:35–2:48)

- **Screen:** In **Chat**, switch language to **Kannada** and ask (type or voice):
  `ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?`
  → answers with the count (`ಫಲಿತಾಂಶ: 47`). (Optional: use the mic to show voice input.)
- **CAPTION:** `Bilingual — English + ಕನ್ನಡ, by voice or text`
- **VO:** "And it's built for Karnataka's officers — ask in Kannada, by voice or text,
  and get the same verified answer."

## Scene 8 — Governance + close (2:48–2:58)

- **Screen:** Open **Audit** (every action logged: user, role, action). Optionally show
  the **Role** selector.
- **CAPTION:** `Governed by design · runs 100% on Zoho Catalyst`
- **VO:** "Every action is audit-logged, role-based access is built in, and no protected
  attributes ever enter the models. Deterministic tools, verifiable evidence, deployed
  entirely on Zoho Catalyst. ANVESHAK — an AI that doesn't just answer questions, it
  works cases."

- **END CARD (hold 2s):** `ANVESHAK (ಅನ್ವೇಷಕ) · Team Zen · KSP Datathon 2026`
  plus the GitHub + live links.

---

## Exact queries to paste (copy-ready)

```
How many chain snatching cases were registered in Bengaluru City in 2026?
Show the monthly trend of chain snatching in Bengaluru City for 2026
Which police stations are worst affected?
Show Prakash Rao's network
ಈ ವರ್ಷ ಬೆಂಗಳೂರು ನಗರದಲ್ಲಿ ಎಷ್ಟು ಸರಗಳ್ಳತನ ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ?
```

## Notes for an honest, strong cut

- Lead with the **evidence drawer** (Scene 2) and the **Investigation Cell** (Scene 5)
  — they are the differentiators. Give Scene 5 the most time.
- If a heavy view is slow on the first click, you didn't warm it — stop, warm it
  (prep step 1), and restart the take. Warmed, everything is sub-second.
- Route the serial-crime story through the **Series** view (Scene 4), not a
  "are these connected?" chat query — Series shows SH-07 cleanly.
- Keep it **under 3:00**. Upload as an **unlisted YouTube** or **public Google Drive**
  link and paste it into **deck slide 12**.
