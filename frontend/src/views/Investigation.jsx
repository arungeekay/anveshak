import { useState } from "react";
import { apiBase, apiGet, apiPost, openInvestigationStream } from "../lib/api.js";

const AGENTS = ["case_officer", "records_analyst", "network_specialist",
  "crime_historian", "legal_advisor", "forecaster"];
const LABEL = {
  case_officer: "Case Officer", records_analyst: "Records Analyst",
  network_specialist: "Network Specialist", crime_historian: "Crime Historian",
  legal_advisor: "Legal Advisor", forecaster: "Forecaster",
};

export default function Investigation() {
  const initial = new URLSearchParams(location.hash.split("?")[1] || "").get("series") || "SH-07";
  const [seriesId, setSeriesId] = useState(initial);
  const [steps, setSteps] = useState({});
  const [pack, setPack] = useState(null);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState(null);

  async function start() {
    setSteps({}); setPack(null); setErr(null); setRunning(true);
    const sid = seriesId;
    let run_id;
    try {
      ({ run_id } = await apiPost("/api/investigate", { series_id: sid }));
    } catch (e) {
      setErr(`Could not start investigation: ${e.message}`);
      setRunning(false);
      return;
    }
    const markAllDone = () =>
      setSteps((s) => Object.fromEntries(AGENTS.map((a) => [a, { ...(s[a] || {}), status: "done" }])));
    let gotPack = false;
    const landPack = (data) => { gotPack = true; markAllDone(); setPack(data); setRunning(false); };
    openInvestigationStream(run_id,
      (name, data) => {
        if (name === "agent_step") {
          setSteps((s) => ({ ...s, [data.agent]: { ...(s[data.agent] || {}), status: data.status, thought: data.thought_summary || s[data.agent]?.thought } }));
        } else if (name === "pack_ready" && data.pack) {
          landPack(data);
        }
      },
      // The gateway can cut a long SSE before pack_ready fires; the pack is still
      // being assembled server-side. Poll the cached pack as a fallback.
      async () => {
        if (gotPack) return;
        for (let i = 0; i < 24 && !gotPack; i++) {
          await new Promise((r) => setTimeout(r, 3000));
          try {
            const p = await apiGet(`/api/investigate/${sid}/pack`);
            if (p && p.pack) { landPack(p); return; }
          } catch { /* keep polling */ }
        }
        setRunning(false);
      });
  }

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-4 flex items-center gap-2">
        <h2 className="text-lg font-semibold">Investigation Room</h2>
        <input value={seriesId} onChange={(e) => setSeriesId(e.target.value)}
          className="w-28 rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 font-mono" />
        <button onClick={start} disabled={running}
          className="rounded-lg bg-accent px-3 py-1 text-white disabled:opacity-50">
          {running ? "Streaming…" : "Investigate"}</button>
        {err && <span className="text-sm text-red-400">{err}</span>}
      </div>

      <div className="grid gap-4 md:grid-cols-[300px_1fr]">
        <div className="space-y-2">
          {AGENTS.map((a) => {
            const st = steps[a];
            const done = st?.status === "done";
            const active = st && !done;
            return (
              <div key={a} className={`rounded-lg border p-3 ${done ? "border-emerald-700 bg-emerald-950/30" : active ? "border-accent bg-navy-800" : "border-navy-800 bg-navy-900/40"}`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium">{LABEL[a]}</span>
                  <span className="text-xs">{done ? "✓" : active ? "…" : "•"}</span>
                </div>
                {st?.thought && <p className="mt-1 text-xs text-slate-400">{st.thought}</p>}
              </div>
            );
          })}
        </div>

        <div>
          {pack?.pack ? (
            <PackView pack={pack.pack} pdfUrl={pack.pdf_url} />
          ) : (
            <p className="text-slate-500">The six agents will stream their reasoning here, then assemble the pack.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function PackView({ pack, pdfUrl }) {
  return (
    <div className="space-y-4 rounded-lg border border-navy-700 bg-navy-900 p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">Investigation Pack · {pack.series_id}</h3>
        <div className="flex gap-2">
          {pdfUrl && <a href={`${apiBase}${pdfUrl}`} target="_blank" rel="noreferrer"
            className="rounded-lg bg-accent px-3 py-1 text-sm text-white">Open pack ↗</a>}
          <a href={`${apiBase}/api/investigate/pack/${pack.series_id}.pdf`}
            target="_blank" rel="noreferrer"
            className="rounded-lg border border-navy-700 px-3 py-1 text-sm hover:bg-navy-800">
            Download PDF ⬇
          </a>
        </div>
      </div>
      <p className="text-sm text-slate-300">{pack.summary}</p>

      <Section title="Ranked Suspects">
        {(pack.suspects_ranked || []).slice(0, 5).map((s) => (
          <a key={s.person_key} href={`#/person/${s.person_key}`}
            className="mb-1 flex items-center justify-between rounded px-1 text-sm hover:bg-navy-800">
            <span className="underline decoration-navy-700 underline-offset-2">
              {s.name} <span className="text-xs text-slate-500">{s.person_key}</span>
            </span>
            <span className="font-semibold text-red-400">risk {s.risk?.score}</span>
          </a>
        ))}
      </Section>

      <Section title="Leads">
        <ol className="list-decimal pl-5 text-sm text-slate-300">
          {(pack.leads || []).map((l, i) => <li key={i}>{l.lead}</li>)}
        </ol>
      </Section>

      <Section title="Legal: sections and element checks">
        <p className="text-xs text-slate-400">{(pack.legal?.sections_invoked || []).map((s) => `${s.act} ${s.section}`).join(", ")}</p>
        <ul className="mt-1 text-xs">
          {(pack.legal?.elements_check || []).slice(0, 8).map((e, i) => (
            <li key={i} className={e.status === "missing" ? "text-red-400" : "text-emerald-400"}>
              {e.status === "missing" ? "✗" : "✓"} {e.element}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Forecast">
        <p className="text-sm text-slate-300">Next window: <b>{pack.forecast?.next_window}</b></p>
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="border-t border-navy-800 pt-3">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</div>
      {children}
    </div>
  );
}
