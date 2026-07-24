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
                <span className="font-medium">{s.crime_sub_head}</span>
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
                    <th className="py-1">A</th><th>B</th><th>cosine</th><th>shared MO</th></tr></thead>
                  <tbody>
                    {(s.links || []).slice(0, 8).map((l, i) => (
                      <tr key={i} className="border-t border-navy-800">
                        <td className="py-1">C-{l.case_a}</td><td>C-{l.case_b}</td>
                        <td>{l.cosine}</td>
                        <td className="text-slate-400">{(l.shared_features || []).join(", ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
