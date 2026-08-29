# FINALE_QA.md — answers for the jury's questions

Three sentences each, in plain language. **Lead with the honest answer**, then the
evidence, then the roadmap. A police jury forgives an immature feature; it does not
forgive being oversold.

Suggested split — **Hiran**: policing value, adoption, roadmap, impact.
**Arun**: architecture, accuracy, security, platform.

---

## The ones that will definitely come

### "Is this real data?"
No — it is a synthetic corpus of 15,405 FIRs across 31 districts, generated to
mirror the official KSP ER schema. We deliberately published the ground truth
(`data_engine/planted/*.yaml`) so our linkage precision numbers can be checked
rather than taken on trust. On real data the schema is the same; what changes is
identity resolution, which today uses a synthetic `person_key`.

### "How does it connect to CCTNS?"
The schema we build against *is* the CCTNS/KSP ER structure, so the queries and
views transfer directly. Two pieces of real integration work remain: a read
connection to the live database, and identity resolution on name/parentage/DOB to
replace our synthetic person key. Nothing in the analytics layer needs to change.

### "How do you know it isn't making the numbers up?"
Because the model never computes a number. Every figure comes from a deterministic
tool — SQL, the linkage engine, SARIMA, the risk scorer — and the model only turns
that verified result into a sentence; we call it "deterministic tools, LLM
narrates". You can check any answer in the evidence drawer: the exact SQL, the row
count, and the case IDs.

### "What if the AI is wrong?"
It shows its work, and a human decides. Every series carries the specific MO
features it matched on in plain language, every lead cites its evidence, and the
analyst can Confirm or Reject a series — that verdict is recorded. ANVESHAK is
built to be an assistant an officer can audit, not an oracle to obey.

### "Will it profile people by religion or caste?"
No, and you can try to make it. Those fields exist in the official schema, but they
are never features in linkage, risk scoring or forecasting, and a question that
tries to filter or rank individuals by them is refused with an explanation in
English and Kannada — the refusal itself is written to the audit log. Aggregate
sociological statistics, asked for explicitly, are still permitted.

### "What about data privacy and misuse?"
Access is scoped server-side: an SHO sees their own station, an SP their district,
SCRB statewide, and an analyst gets statewide numbers with names masked to
initials. The scope is injected into the SQL that actually runs, not into a prompt
the model could ignore or the browser could bypass. Every action is written to a
hash-chained audit log, so even an administrator cannot alter history undetectably
— press "Verify chain" and see.

### "How accurate is it?"
On our 60-question bilingual benchmark, scored by executing the SQL and comparing
results, the deployed system answers **[insert measured %]** — English materially
stronger than Kannada, which is our main tuning gap. Linkage precision on the
planted series is 0.86 with recall 12 of 14, and the forecast's backtest error is
competitive with a seasonal-naive baseline. We publish the ones that flatter us and
the ones that do not.

### "Can it handle real volume?"
The analytical layer is an embedded columnar database, so a 15,000-case corpus
answers in milliseconds and the design scales to millions of rows on the same
pattern. We measured the deployed service at 60 concurrent requests with zero
errors after fixing a thread-safety bug we found ourselves. The heavy work —
embeddings, clustering — is precomputed, so query time stays flat.

---

## The sharper ones

### "Why a second database? Isn't Data Store enough?"
Data Store is the system of record — it is where FIRs are written and where
durability matters. Analytical questions ("group 15,000 cases by station and
month") are a different workload, so we mirror the core tables into an embedded
columnar engine for sub-second aggregation. Same data, two shapes, and we are
explicit about which one answers a given request.

### "What happens when the model is unavailable?"
Most of the product keeps working, because the model is not in the critical path
for anything that computes. Linkage, the graph, patrol detection, risk scoring and
the whole Investigation Cell are deterministic; only the natural-language front
door needs the model, and it fails with a clear message rather than a stack trace.

### "Could someone jailbreak it into dumping the database?"
Try it — there is a red-team console in the Trust Center for exactly this. Whatever
the model produces is parsed and sanitised before execution: SELECT only, an
allowlist of tables, no file or network functions, an automatic row limit. A
prompt that says "ignore your instructions and DROP TABLE" fails at the sanitizer,
not at the model's goodwill.

### "Six agents sounds like marketing. What are they actually doing?"
They are a fixed six-step pipeline, not autonomous agents — each step has one role,
a declared set of tools, and a hard cap on model calls. You watch each one work in
real time and see which tool it called. It finishes in about ten seconds and
produces a pack whose every claim traces to a case ID.

### "How much would this cost to run?"
The prototype runs inside the Catalyst development tier. At production scale the
meaningful costs are language-model tokens for the conversational layer and compute
for the nightly sweep — the analytics themselves are cheap because embeddings are
precomputed and the columnar engine is embedded. We would size it properly against
real volumes before quoting a number.

### "What is genuinely not finished?"
Three things. Catalyst Auth is provisioned but the roles are seeded rather than
issued from real identities; Data Store tables are created in the console, so where
they are not yet provisioned the status endpoint says so plainly; and Kannada
NL→SQL accuracy trails English and needs hand-curated examples. None of these
change the architecture — they are integration work.

### "Why should KSP trust a hackathon prototype?"
You should not — you should trust what you can check. Every answer shows its query,
every linkage shows what it matched on, the ground truth for our accuracy claims is
public, the audit log is tamper-evident, and the refusals are as visible as the
answers. That posture is the product.

---

## If they ask for something we cannot do

Say so in one sentence, then say what it would take. *"Not today — that needs X.
Here is what we would build."* Never bluff a capability; the person asking is
usually the one who would have to live with it.

## Numbers to have at your fingertips

| | |
|---|---|
| Corpus | 15,405 FIRs · 31 districts · 248 stations · 2023–2026 |
| SH-07 | 15 cases · 3 districts · confidence 0.88 |
| Counterfactual | detectable at case #6 · 9 further offences · 142 days |
| Linkage | precision 0.86 · recall 12/14 |
| Investigation | six agents · ~10s · 8 ranked suspects |
| Robustness | 60 concurrent requests · 0 errors |
| Guardrails | 10/10 attack vectors blocked, re-tested live |
