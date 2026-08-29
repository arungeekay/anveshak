# Demo video: editing brief

**Source file:** `ANVESHAK_demo.webm` (1600x900, 2 min 38 s, no audio)
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

1. **Under 3:00.** Currently 2:38, so there are about 20 seconds of headroom.
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
| 0:58 - 1:03 | Audit chain verify | The tamper-evident log verifies | Medium |
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
