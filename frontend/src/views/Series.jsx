import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api.js";

export default function Series() {
  const [series, setSeries] = useState([]);
  const [open, setOpen] = useState(null);
  const [err, setErr] = useState(null);

  const load = () => apiGet("/api/series").then(setSeries).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Detected Series</h2>
        <button onClick={() => apiPost("/api/series/rescan").then(load)}
          className="rounded-lg border border-navy-700 px-3 py-1 text-sm hover:bg-navy-800">Rescan</button>
      </div>
      {err && <p className="text-red-400">{err}</p>}
      <div className="space-y-3">
        {series.map((s) => (
          <div key={s.series_id} className="rounded-lg border border-navy-700 bg-navy-900 p-4">
            <div className="flex cursor-pointer items-center justify-between"
              onClick={() => setOpen(open === s.series_id ? null : s.series_id)}>
              <div>
                <span className="font-mono text-accent">{s.series_id}</span>{" "}
                {s.codename && <span className="font-semibold text-white">{s.codename}</span>}{" "}
                <span className="font-medium text-slate-300">{s.crime_sub_head}</span>
                <span className="ml-2 text-sm text-slate-400">{s.districts.join(", ")}</span>
              </div>
              <div className="text-right text-sm">
                <div>{s.case_ids.length} cases</div>
                <div className={`font-semibold ${s.confidence >= 0.8 ? "text-emerald-400" : "text-amber-400"}`}>
                  {(s.confidence * 100).toFixed(0)}% conf
                </div>
              </div>
            </div>
            {open === s.series_id && (
              <div className="mt-3 border-t border-navy-800 pt-3 text-sm">
                <p className="mb-2 text-slate-300">{s.mo_summary}</p>
                <table className="w-full">
                  <thead><tr className="text-left text-slate-400">
                    <th className="py-1">A</th><th>B</th><th>cosine</th><th>why these are linked</th></tr></thead>
                  <tbody>
                    {(s.links || []).slice(0, 8).map((l, i) => (
                      <tr key={i} className="border-t border-navy-800">
                        <td className="py-1">C-{l.case_a}</td><td>C-{l.case_b}</td>
                        <td>{l.cosine}</td>
                        <td className="text-slate-300">
                          {l.explanation || (l.shared_features || []).join(", ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <Counterfactual seriesId={s.series_id} />
                <Replay seriesId={s.series_id} />
                <Verdict series={s} onDone={load} />
                <a href={`#/investigate?series=${s.series_id}`}
                  className="mt-3 inline-block rounded-lg bg-accent px-3 py-1 text-white">Investigate {s.series_id} →</a>
              </div>
            )}
          </div>
        ))}
        {series.length === 0 && !err && <p className="text-slate-500">Loading series…</p>}
      </div>
    </div>
  );
}

// The counterfactual: when the engine would first have flagged this series, and
// what happened afterwards. Precomputed by eval/counterfactual.py; absent for most
// series, in which case nothing is shown.
function Counterfactual({ seriesId }) {
  const [cf, setCf] = useState(null);
  useEffect(() => {
    apiGet(`/api/series/${seriesId}/counterfactual`).then(setCf).catch(() => setCf(null));
  }, [seriesId]);
  if (!cf) return null;
  return (
    <div className="mt-3 rounded-lg border border-amber-700 bg-amber-950/25 p-3">
      <div className="text-sm text-amber-200">
        ⏱ ANVESHAK would have flagged this series at{" "}
        <b className="text-white">case #{cf.detectable_at_case}</b> ({cf.detected_on}).
      </div>
      <div className="mt-1 text-sm text-slate-300">
        <b className="text-white">{cf.cases_after_detection} further offences</b> across{" "}
        {cf.districts_after_detection.join(", ")} followed over the next{" "}
        <b className="text-white">{cf.days_of_exposure} days</b>, after the pattern
        was already visible.
      </div>
      <details className="mt-2">
        <summary className="cursor-pointer text-[11px] text-slate-500">method</summary>
        <p className="mt-1 text-[11px] text-slate-500">{cf.method}</p>
      </details>
    </div>
  );
}

// Chronological replay: the dots appear in order and hop district borders, you
// see the exact moment human coordination would have lost the thread.
function Replay({ seriesId }) {
  const [frames, setFrames] = useState(null);
  const [meta, setMeta] = useState(null);
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);

  async function start() {
    let f = frames;
    if (!f) {
      const d = await apiGet(`/api/series/${seriesId}/replay`);
      f = d.frames; setFrames(f); setMeta(d);
    }
    setI(0); setPlaying(true);
  }

  useEffect(() => {
    if (!playing || !frames) return;
    if (i >= frames.length) { setPlaying(false); return; }
    const t = setTimeout(() => setI((n) => n + 1), 600);
    return () => clearTimeout(t);
  }, [playing, i, frames]);

  const shown = frames ? frames.slice(0, i) : [];
  const districts = [...new Set(shown.map((f) => f.district))];

  return (
    <div className="mt-3">
      <button onClick={start}
        className="rounded-lg border border-navy-700 px-3 py-1 text-xs hover:bg-navy-800">
        ▶ Replay the series
      </button>
      {frames && (
        <div className="mt-2 rounded-lg border border-navy-800 bg-navy-950/40 p-3">
          <div className="flex flex-wrap gap-1">
            {frames.map((f, n) => (
              <span key={f.case_id}
                title={`C-${f.case_id} · ${f.date} · ${f.police_station}`}
                className={`h-3 w-3 rounded-full transition-opacity ${
                  n < i ? "opacity-100" : "opacity-15"} ${
                  f.district === "Bengaluru City" ? "bg-blue-400"
                    : f.district === "Mandya" ? "bg-amber-400" : "bg-emerald-400"}`} />
            ))}
          </div>
          <div className="mt-2 text-xs text-slate-300">
            {shown.length > 0 ? (
              <>
                {shown.length} of {frames.length} cases ·{" "}
                {shown[shown.length - 1].date} ·{" "}
                {shown[shown.length - 1].police_station} ·{" "}
                <b className="text-white">{districts.length} district{districts.length > 1 ? "s" : ""}</b>
              </>
            ) : "press play"}
          </div>
          {!playing && i >= frames.length && meta && (
            <div className="mt-1 text-xs text-amber-300">
              {frames.length} offences · {meta.districts.length} districts ·{" "}
              {meta.span_days} days · {meta.district_hops} border crossings
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Human-in-the-loop: the analyst's verdict is recorded, so the AI never acts alone.
function Verdict({ series, onDone }) {
  const [busy, setBusy] = useState(false);
  const status = series.status || "open";

  async function send(verdict) {
    setBusy(true);
    try { await apiPost(`/api/series/${series.series_id}/feedback`, { verdict }); onDone?.(); }
    finally { setBusy(false); }
  }

  if (status !== "open") {
    return (
      <div className="mt-3 text-xs">
        <span className={status === "confirmed" ? "text-emerald-400" : "text-red-400"}>
          {status === "confirmed" ? "✓ Confirmed by analyst" : "✗ Rejected by analyst"}
        </span>
      </div>
    );
  }
  return (
    <div className="mt-3 flex items-center gap-2">
      <span className="text-xs text-slate-500">Analyst verdict:</span>
      <button disabled={busy} onClick={() => send("confirm")}
        className="rounded-lg border border-emerald-700 px-3 py-1 text-xs text-emerald-300 hover:bg-emerald-950/40 disabled:opacity-50">
        Confirm series
      </button>
      <button disabled={busy} onClick={() => send("reject")}
        className="rounded-lg border border-red-800 px-3 py-1 text-xs text-red-300 hover:bg-red-950/30 disabled:opacity-50">
        Reject
      </button>
    </div>
  );
}
