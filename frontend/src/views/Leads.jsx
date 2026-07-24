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
        <h2 className="text-lg font-semibold">Night Patrol — Lead Feed</h2>
        <button onClick={run} disabled={busy}
          className="rounded-lg bg-accent px-3 py-1 text-sm text-white disabled:opacity-50">
          {busy ? "Running…" : "Run detectors"}</button>
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
        {leads.length === 0 && <p className="text-slate-500">No leads yet — run the detectors.</p>}
      </div>
    </div>
  );
}
