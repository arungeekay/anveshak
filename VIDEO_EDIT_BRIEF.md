# Demo video: editing brief

**Source file:** `ANVESHAK_demo.webm` (1600x900, 2 min 43 s, no audio)
**Deliver:** MP4, 1920x1080, H.264, **under 3 minutes** (hard rule, see constraints)

---

## What this is, and who watches it

ANVESHAK is an AI system built for the **Karnataka State Police**, entered in a
national datathon. This is a real screen recording of the working product, not a
mockup.

The judges are **senior police officers and Zoho engineers**. They are sceptical
by profession. The video has to feel like credible evidence, not an advert. Aim
for the tone of a serious product film: confident, clean, quietly impressive.
Nothing jokey, no stock footage, no cheesy transitions, no royalty-free "corporate
uplift" music with a big drop.

The single most important thing: **a viewer who watches once must believe this
software really works.**

---

## Hard constraints (breaking any of these can disqualify the entry)

1. **Under 3:00.** Currently 2:43, so there are about 15 seconds of headroom.
2. **Do not alter anything on screen that states a fact.** Numbers, case IDs,
   confidence percentages, SQL, names. You may zoom, crop, highlight, or slow
   down. You may **not** retouch, retype or "clean up" a value. These are real
   outputs and the judges may check them against the live system.
3. **Do not change the on-screen caption wording.** The claims are deliberately
   precise and legally careful. You may restyle the captions (font, animation,
   position) freely.
4. **No added claims.** Do not write new superlatives ("world's first",
   "99% accurate", "revolutionary"). If you want extra text on screen, take the
   wording from the captions already in the video or from the list at the end.
5. Keep the **Kannada text** intact and legible. It is central to the pitch. Use
   a font that renders Kannada correctly if you retype anything, or just keep the
   original pixels.

---

## Scene map (source timecodes)

| Time | Scene | What is happening | Editing priority |
|---|---|---|---|
| 0:00 - 0:07 | **Title card** | Product name in English and Kannada | Replace with a stronger animated title |
| 0:07 - 0:20 | Night Patrol lead feed | Three AI-generated leads with confidence scores | Trim if needed |
| 0:20 - 0:33 | Patrol plan | Generates tonight's deployment: station, hours, offence | Medium |
| 0:33 - 0:48 | Chat and evidence | Question answered, then the SQL evidence drawer opens | **High: zoom on the evidence** |
| 0:48 - 0:58 | Red-team: prompt injection | An attack is refused, and the blocked statement is shown | **High** |
| 0:58 - 1:02 | Audit chain verify | The tamper-evident log verifies | Medium |
| 0:44 - 0:52 | **Built on Zoho Catalyst** | The platform panel: all twelve services with live status | **High: the sponsor moment** |
| 1:03 - 1:12 | New FIR being filed | An officer's plain-words narrative | Speed up slightly |
| **1:12 - 1:22** | **FIR joins the series** | "now 16 linked cases" appears | **HIGHEST: this is the hero shot** |
| 1:22 - 1:32 | Series and codename | Link explanations, "Operation Gold Chain Black Visor" | High |
| 1:32 - 1:40 | Counterfactual | "Detectable at case 6. Nine further offences over 142 days." | **High: let this land** |
| 1:40 - 1:52 | Series replay | Dots appear in date order, crossing three districts | **High: visually the best moment** |
| 1:52 - 2:05 | Six agents working | Agent cards complete one by one, live | High |
| 2:05 - 2:15 | Investigation pack | Ranked suspects, leads, legal checks, forecast | High |
| 2:15 - 2:25 | Person 360 | One person's full history, risk, network | Medium |
| 2:25 - 2:32 | Kannada question | Asked and answered in Kannada | High |
| 2:32 - 2:36 | Role switch | Same question, different officer, different answer | Medium |
| 2:36 - 2:38 | Closing card | Team and links | Replace with a stronger end card |

---

## The four moments that win this

Give these room. If you need to save time, take it from the medium-priority
scenes, never from these.

1. **The FIR joining the series (1:12)**: a crime report typed in ordinary words
   becomes case 16 of a serial ring, instantly. Punch in on the green result
   panel. Consider a beat of silence or a held frame on "now 16 linked cases".
   This is the moment that proves the product is real.
2. **The counterfactual (1:32)**: "nine further offences over 142 days". This is
   the emotional core: crimes that would have been prevented. Hold it longer than
   feels comfortable. Consider isolating the numbers with a subtle highlight.
3. **The series replay (1:40)**: dots appearing across a map of districts. The
   most cinematic thing in the video. Do not cut away early.
4. **The attack being refused (0:48)**: a hacking attempt is caught and
   explained. Land the "BLOCKED" state clearly.

---

## What would make this stand out

**Visual**
- Punch-ins and slow pushes on the moments above. The raw recording is a static
  1600x900 browser window, so gentle motion will lift it enormously.
- Highlight key numbers as they appear: a soft glow, a box, or a brief
  desaturation of everything else. Especially **16 linked cases**, **142 days**,
  **10/10 blocked**, **47**.
- Cursor is not visible in the recording. If a click is unclear, add a subtle
  tap indicator so the viewer knows an action happened.
- The UI is dark navy. Keep any added graphics in that palette: navy, white,
  a blue accent (#5AB0FF), amber for warnings, green for confirmations.

**Pacing**
- The recording has deliberate pauses so text can be read. Tighten anything that
  feels dead, but never cut a caption before it can be read once at a
  comfortable speed.
- Build rhythm: quicker through the setup scenes, then slow down for the four key
  moments.

**Titles**
- A proper animated opening title would help a lot. Content:
  **ANVESHAK · ಅನ್ವೇಷಕ** with the line *"An AI that does not just answer
  questions. It works cases."* and *KSP Datathon 2026 · Challenge 1*.
- A clean end card: **Team Zen: Hiran Vikraman S R, Arun G K**, plus
  `github.com/arungeekay/anveshak` and *Runs 100% on Zoho Catalyst*.
  (Ask us for the live URL to include if you want it on screen.)
- The in-video captions can be restyled to match your titles. Keep the wording.

**Sound**
- There is no audio. Add restrained, tense-but-hopeful underscore. Think
  documentary or investigative, not tech-startup. Keep it low.
- Small, tasteful UI ticks on key reveals can help, but do not overdo it.
- **No voiceover.** If you think one is essential, ask first; the script would
  have to be approved for factual accuracy.

**Things to avoid**
- Glitch effects, lens flares, fast whip-pans, countdown timers.
- Speeding footage so fast that on-screen text cannot be read.
- Stock footage of police, servers or "hackers in hoodies". Everything on screen
  must be the actual product.

---

## Approved phrases, if you want extra on-screen text

Use these verbatim, or nothing:

- "Every answer shows its SQL, its rows and its case IDs."
- "The AI never invents a number."
- "A new FIR, filed in plain words, joins a serial-crime ring in seconds."
- "Detectable at case 6. Nine further offences followed over 142 days."
- "Serial crime linked across three districts."
- "A court-ready investigation pack in seconds."
- "Ask in Kannada or English."
- "Built for the Karnataka State Police. Runs 100% on Zoho Catalyst."

---

## Deliverables

1. Final cut, **MP4 / H.264 / 1920x1080 / under 3:00**, suitable for YouTube.
2. If convenient, a second version under 90 seconds for social or a lightning
   pitch. Optional.
3. Please keep the project file in case a number needs updating before the final
   round.

Any question about whether a change is factually safe: **ask before changing it.**
Accuracy matters more here than polish, because the judges can and will check.

---

# Exact spec: what to add, and where

The video **already has burned-in captions for every scene**, so it does not need
explanatory text adding. Do not duplicate what a caption already says. The list
below is everything that is actually wanted.

Navigate by the caption text (it is unambiguous); the timecodes are approximate to
within a second or two.

## 1. Opening screen

There is already a title card at 0:00 to 0:07. **Replace it with an animated
version.** Same copy, better execution:

```
KSP DATATHON 2026  ·  CHALLENGE 1
ANVESHAK  ·  ಅನ್ವೇಷಕ
An AI that does not just answer questions. It works cases.
Ask in Kannada or English · every answer backed by evidence · runs 100% on Zoho Catalyst
```

Keep it to about 5 seconds. Dark navy ground, white type, blue accent (#5AB0FF).

## 2. Text to ADD (only these three)

Everything else is already captioned. Add:

**a) At about 2:24, the role-switch moment.** This is the fastest scene and the
point is easy to miss. Both answers are on screen together in the chat thread.
Draw a connector or place two small labels beside them:

```
Statewide officer:  48
Station officer (Jayanagar PS):  11
Same question. The database enforces who sees what.
```

**b) At about 1:14, under the counterfactual.** Optional but strong. A single
line, small, beneath the amber banner:

```
Nine crimes, after the pattern was already visible.
```

**c) End card, replacing 2:33 onward.** Same copy as now, better designed:

```
ANVESHAK  ·  ಅನ್ವೇಷಕ
Faster answers · serial crime caught across districts ·
court-ready packs in minutes · proactive leads every morning

Team Zen: Hiran Vikraman S R · Arun G K
github.com/arungeekay/anveshak
Runs 100% on Zoho Catalyst
```

## 3. Highlights (numbers to emphasise as they appear)

Soft glow, a thin box, or briefly dimming the rest of the frame. Keep it subtle
and consistent. Never cover the number itself.

| Approx. time | Highlight | Why it matters |
|---|---|---|
| 0:09 | `18.3x baseline` and the `94%` confidence | The AI found this on its own, overnight |
| 0:16 | `Whitefield PS` and `00:00-05:00` | Analytics turned into a concrete order |
| 0:24 | The answer `47`, then the SQL in the evidence drawer | Proof it does not invent numbers |
| 0:34 | `BLOCKED` and the extracted `DROP TABLE CaseMaster` | An attack, caught and shown |
| 0:44 | `chain intact` | Tamper-evident audit |
| 0:47 | The green `LIVE` tags beside AppSail, QuickML and API Gateway | Runs entirely on Zoho Catalyst |
| **1:06** | **`now 16 linked cases`** | **The single most important frame in the video** |
| 1:14 | `case #6`, `9 further offences`, `142 days` | The cost of not having this |
| 1:26 | `3 districts` as the replay crosses borders | Cross-district reach |
| 1:44 | `risk 0.731` beside the top suspect | Ranked, explainable output |
| 2:24 | `48` and `11` | Role-based access, visible |

## 4. One thing to point out, not hide

The chain-snatching count is **47 early in the video** and **48 later**. That is
not an error. Partway through, the demo files a **new FIR**, which becomes case
16 of the series and pushes the statewide count up by one. If anything, make this
legible: it is live proof the system ingested a case during the recording.

Do not "fix" either number.

## 5. Voiceover

**Recommendation: no voiceover.** Reasons:

- The captions already carry the narrative, and reading plus listening to
  different words competes for attention.
- Every claim in this video has been checked for accuracy. A new script would
  need the same scrutiny, and a small paraphrase can turn a careful statement
  into an overclaim the judges can challenge.
- Judges often watch entries with the sound off.

If you strongly disagree, say so and we will write the script ourselves so the
wording stays accurate. Do not write and record one unprompted.

**Music: yes.** Restrained, investigative, documentary tone. Low in the mix. Let
it lift slightly at the FIR-joins-the-series moment (1:06) and settle for the
counterfactual (1:14).


---

## Zoho Catalyst (the sponsor platform): please give this a beat

The whole system is required to run on **Zoho Catalyst**, and Zoho engineers are
among the judges, so this scene matters more than its length suggests.

At about **0:44 to 0:52** the app shows a panel titled *Built on Zoho Catalyst*
listing each service it uses, with a status tag against each one. Suggestions:

- Punch in on the panel so the service names and the green `LIVE` tags are
  legible.
- Highlight the `LIVE` tags on **AppSail** and **QuickML** in particular.
- If you add a graphic here, the Zoho logo would be appropriate and welcome.

Approved line if you want text on screen for this scene:

- "Runs entirely on Zoho Catalyst. No external AI service is ever called."

Please do not overstate it beyond that phrasing. The panel deliberately marks some
services as *integrated* or *configured* rather than *live*, and that honesty is
intentional.
