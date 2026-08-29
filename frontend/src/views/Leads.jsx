import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api.js";

const TYPE_ICON = { spike: "📈", series_growth: "🔗", repeat_offender: "👤" };

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = () => apiGet("/api/leads").then(setLeads).catch(() => {});
  useEffect(() => { load(); }, []);

  async function run() {
    setBusy(true);
    try { const r = await apiPost("/api/leads/run"); setLeads(r.leads); }
    finally { setBusy(false); }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Night Patrol: Lead Feed</h2>
        <div className="relative flex items-center gap-2">
          <Briefing />
          <button onClick={run} disabled={busy}
            className="rounded-lg bg-accent px-3 py-1 text-sm text-white disabled:opacity-50">
            {busy ? "Running…" : "Run detectors"}</button>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {leads.map((l) => (
          <div key={l.lead_id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
            <div className="flex items-start justify-between">
              <span className="text-2xl">{TYPE_ICON[l.type] || "🚨"}</span>
              <span className={`text-sm font-semibold ${l.confidence >= 0.8 ? "text-emerald-400" : "text-amber-400"}`}>
                {(l.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <h3 className="mt-1 font-medium">{l.title}</h3>
            <p className="mt-1 text-xs text-slate-400">
              {l.evidence.metric}: <b>{l.evidence.value}</b> · {l.evidence.window} ·{" "}
              {l.evidence.case_ids?.length || 0} cases · {l.district}
            </p>
            <p className="mt-2 rounded bg-navy-950/60 p-2 text-xs text-slate-300">➡️ {l.suggested_action}</p>
          </div>
        ))}
        {leads.length === 0 && <p className="text-slate-500">No leads yet, run the detectors.</p>}
      </div>
      <PatrolPlan />
    </div>
  );
}

// Turns the signals above into tonight's deployment: which station, which window,
// which offence, and the tools each recommendation came from.
function PatrolPlan() {
  const [district, setDistrict] = useState("Bengaluru City");
  const [districts, setDistricts] = useState([]);
  const [plan, setPlan] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet("/api/masters").then((m) => setDistricts(m.districts || [])).catch(() => {});
  }, []);

  async function generate() {
    setBusy(true);
    try { setPlan(await apiGet(`/api/patrol/plan?district=${encodeURIComponent(district)}`)); }
    catch { setPlan(null); } finally { setBusy(false); }
  }

  return (
    <div className="mt-6 rounded-lg border border-navy-700 bg-navy-900 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold">🗺 Patrol plan</h3>
        <select value={district} onChange={(e) => setDistrict(e.target.value)}
          className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 text-xs">
          {(districts.length ? districts : [district]).map((d) => <option key={d}>{d}</option>)}
        </select>
        <button onClick={generate} disabled={busy}
          className="rounded-lg bg-accent px-3 py-1 text-xs text-white disabled:opacity-50">
          {busy ? "Composing…" : "Generate"}
        </button>
      </div>

      {plan && plan.items?.length > 0 && (
        <>
          <ol className="space-y-2">
            {plan.items.map((it, i) => (
              <li key={it.police_station} className="rounded-lg border border-navy-800 bg-navy-950/40 p-3">
                <div className="flex items-baseline justify-between">
                  <span className="font-medium text-white">
                    {i + 1}. {it.police_station}
                  </span>
                  <span className="font-mono text-sm text-accent">{it.window}</span>
                </div>
                <div className="mt-1 text-xs text-slate-300">
                  Focus: {it.focus.join(", ")}
                </div>
                <ul className="mt-1 list-disc pl-4 text-xs text-slate-400">
                  {it.reasons.slice(0, 3).map((r, j) => <li key={j}>{r}</li>)}
                </ul>
                <div className="mt-1 text-[10px] text-slate-600">
                  from {it.sources.join(" · ")}
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-2 text-[11px] text-slate-500">{plan.method}</p>
        </>
      )}
      {plan && !plan.items?.length && (
        <p className="text-sm text-slate-500">{plan.note || "No active signals."}</p>
      )}
    </div>
  );
}

// The 7am brief an SP would want, spoken aloud. Text comes from fixed templates
// filled with detector output (no model-authored numbers); the browser speaks it
// with a kn-IN / en-IN voice. Captions are shown too, demo halls are loud.
function Briefing() {
  const [lang, setLang] = useState("kn");
  const [text, setText] = useState(null);
  const [speaking, setSpeaking] = useState(false);

  async function play() {
    if (speaking) { window.speechSynthesis?.cancel(); setSpeaking(false); return; }
    try {
      const d = await apiGet(`/api/briefing?lang=${lang}`);
      setText(d.text);
      const synth = window.speechSynthesis;
      if (!synth) return;
      synth.cancel();
      const u = new SpeechSynthesisUtterance(d.text);
      u.lang = lang === "kn" ? "kn-IN" : "en-IN";
      u.rate = 0.95;
      u.onend = () => setSpeaking(false);
      u.onerror = () => setSpeaking(false);
      setSpeaking(true);
      synth.speak(u);
    } catch { setSpeaking(false); }
  }

  return (
    <>
      <select value={lang} onChange={(e) => setLang(e.target.value)}
        className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 text-xs">
        <option value="kn">ಕನ್</option>
        <option value="en">EN</option>
      </select>
      <button onClick={play}
        className="rounded-lg border border-navy-700 px-3 py-1 text-sm hover:bg-navy-800">
        {speaking ? "■ Stop" : "🔊 Morning briefing"}
      </button>
      {text && (
        <div className="absolute left-0 right-0 top-full z-10 mt-2 rounded-lg border border-navy-700 bg-navy-900 p-3 text-sm text-slate-300 shadow-lg">
          <p className="font-kannada">{text}</p>
          <button onClick={() => setText(null)}
            className="mt-2 text-[11px] text-slate-500 hover:text-slate-300">dismiss</button>
        </div>
      )}
    </>
  );
}
