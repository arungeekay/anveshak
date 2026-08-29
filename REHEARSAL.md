# REHEARSAL.md — finale-week checklist

Everything below is mechanical. Do it in order; do not improvise on the day.

---

## Assets (all in the repo root)

| File | Purpose |
|---|---|
| `demo_path.md` | The 18-step golden path — the script you actually drive |
| `ANVESHAK_Finale_Pitch.pptx` / `.pdf` | 9-slide pitch deck (the demo is slide 4) |
| `FINALE_QA.md` | 3-sentence answers to the questions that will come |
| `ANVESHAK_demo.webm` | Recorded demo — the last-resort fallback |
| `ANVESHAK_KSP_Datathon_2026_Submission.pptx` | The Stage-1 submission deck |

Regenerate the pitch deck after any change: `python scripts/build_finale_deck.py`

---

## Three dry runs (do not skip the third)

**Run 1 — correctness.** Walk `demo_path.md` slowly. Tick every "expect" value.
Note anything that differs; fix it that day, not on the morning.

**Run 2 — timing.** Same path with a stopwatch, aiming for **6:00**. If you are
over, cut the patrol plan (step 15) and the graph — not the intake or the pack.

**Run 3 — hostile.** Someone plays a sceptical DGP: interrupt mid-demo, grab the
keyboard, type a hostile prompt into the Trust Center, ask two questions from
`FINALE_QA.md`. This is the run that decides whether you are ready.

Also run once on a **phone hotspot** — venue Wi-Fi is unpredictable, and you should
know how the app behaves on a weak connection before you find out live.

---

## Day-before

- [ ] `python scripts/verify_live.py` → all 11 checks pass
- [ ] `python -m eval.live_harness` → record the measured accuracy, put it on the Trust slide and in `FINALE_QA.md`
- [ ] Kannada TTS voice installed on the demo laptop and heard out loud
- [ ] Mic permission granted in Chrome for the live URL
- [ ] Deck exported fresh to PDF (screenshots current)
- [ ] Laptop charged; charger, HDMI adapter and a spare USB-C cable packed
- [ ] `ANVESHAK_demo.webm` copied **locally** (do not rely on streaming it)
- [ ] Confirm from the Hack2skill dashboard: time, venue, pitch length, who may attend

## Morning-of

- [ ] `curl -X POST $BASE/api/intake/reset` — clears rehearsal FIRs so SH-07 reads **15**
- [ ] `curl $BASE/api/warm` until it reports `warm` with `packs: ['SH-07']`
- [ ] `python scripts/verify_live.py` one final time
- [ ] Open all needed tabs; close everything else; notifications off; zoom 110%

## T-10 minutes

- [ ] `curl $BASE/api/warm` once more (the container idles out — this is the single most common failure)
- [ ] Lead Feed open on screen, ready to start

---

## Division of labour

- **One person drives, one person talks.** Never both.
- The talker never says "let me just…" — if something stalls, they keep talking
  about *what the audience already saw* while the driver recovers.
- Agree in advance who answers what (see the split at the top of `FINALE_QA.md`).

## The fallback ladder

1. Something looks slow → **warm it** (`/api/warm`) and keep talking.
2. A view breaks → skip it, move on; the story survives losing any single step.
3. Network fails → local frontend against the live API:
   `cd frontend && VITE_API_BASE=$BASE npm run dev`
4. Everything fails → play `ANVESHAK_demo.webm` and narrate over it.

**Never debug on stage.** A confident move to the next step costs nothing; a
two-minute silence costs the pitch.

## Last thing

The strongest moments are the **live FIR joining SH-07**, the **red-team console
refusing a judge's own attack**, and the **counterfactual**. If time collapses,
those three plus the pack are the demo.
