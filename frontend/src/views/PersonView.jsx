import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiGet } from "../lib/api.js";
import Chart from "../components/Chart.jsx";

const KIND_COLOR = { person: "#3b82f6", case: "#f59e0b", location: "#10b981", ps: "#a78bfa" };

function graphOption(gr) {
  return {
    tooltip: {},
    series: [{
      type: "graph", layout: "force", roam: true,
      label: { show: true, color: "#cbd5e1", fontSize: 9 },
      force: { repulsion: 140, edgeLength: 70 },
      lineStyle: { color: "#475569", opacity: 0.6 },
      data: (gr.nodes || []).map((n) => ({
        id: n.id, name: n.label,
        symbolSize: n.kind === "person" ? 34 : 16,
        itemStyle: { color: KIND_COLOR[n.kind] || "#94a3b8" },
      })),
      links: (gr.edges || []).map((e) => ({ source: e.a, target: e.b })),
    }],
  };
}

function RiskGauge({ risk }) {
  const pct = Math.round((risk?.score || 0) * 100);
  const tone = pct >= 80 ? "text-red-400" : pct >= 60 ? "text-amber-400" : "text-emerald-400";
  return (
    <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
      <div className="flex items-baseline gap-2">
        <span className={`text-3xl font-bold ${tone}`}>{pct}</span>
        <span className="text-xs text-slate-400">/ 100 risk</span>
      </div>
      <div className="mt-3 space-y-1">
        {Object.entries(risk?.components || {}).map(([k, v]) => (
          <div key={k} className="flex items-center gap-2 text-[11px]">
            <span className="w-20 text-slate-400">{k}</span>
            <div className="h-1.5 flex-1 rounded bg-navy-800">
              <div className="h-1.5 rounded bg-accent" style={{ width: `${Math.round(v * 100)}%` }} />
            </div>
            <span className="w-8 text-right text-slate-500">{v.toFixed(2)}</span>
          </div>
        ))}
      </div>
      {risk?.explanation && (
        <p className="mt-3 border-t border-navy-800 pt-2 text-[11px] text-slate-400">{risk.explanation}</p>
      )}
    </div>
  );
}

export default function PersonView() {
  const { personKey } = useParams();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState([]);
  const [p, setP] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!personKey) { setP(null); return; }
    setLoading(true); setErr(null);
    apiGet(`/api/person/${personKey}`)
      .then(setP)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [personKey]);

  async function search(e) {
    e?.preventDefault();
    if (q.trim().length < 2) return;
    setErr(null);
    try {
      setHits(await apiGet(`/api/person?q=${encodeURIComponent(q.trim())}`));
    } catch (e2) { setErr(e2.message); }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h2 className="mb-3 text-lg font-semibold">Person 360</h2>

      <form onSubmit={search} className="mb-4 flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Search a person by name — e.g. Prakash Rao"
          className="flex-1 rounded-lg border border-navy-700 bg-navy-800 px-3 py-2 text-sm outline-none focus:border-accent" />
        <button className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white">Search</button>
      </form>

      {hits.length > 0 && !personKey && (
        <div className="mb-4 divide-y divide-navy-800 rounded-lg border border-navy-700 bg-navy-900">
          {hits.map((h) => (
            <button key={h.person_key} onClick={() => { setHits([]); navigate(`/person/${h.person_key}`); }}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-navy-800">
              <span>{h.name} <span className="ml-2 font-mono text-xs text-slate-500">{h.person_key}</span></span>
              <span className="text-xs text-slate-400">{h.n_cases} cases · last {h.last_seen}</span>
            </button>
          ))}
        </div>
      )}

      {err && <p className="text-red-400">{err}</p>}
      {loading && <p className="text-slate-500">Loading profile…</p>}

      {p && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-[1fr_240px]">
            <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
              <h3 className="text-xl font-semibold text-white">{p.name}</h3>
              <p className="mt-1 font-mono text-xs text-slate-500">{p.person_key}</p>
              <div className="mt-3 grid grid-cols-2 gap-y-1 text-sm md:grid-cols-3">
                <Stat label="Cases" value={p.stats.total_cases} />
                <Stat label="Unsolved" value={p.stats.unsolved} />
                <Stat label="Arrests" value={p.stats.arrests} />
                <Stat label="Districts" value={p.stats.districts.length} />
                <Stat label="DOB" value={p.dob || "—"} />
                <Stat label="Age on FIRs" value={p.age_recorded || "—"} />
              </div>
              {p.aliases?.length > 0 && (
                <p className="mt-2 text-xs text-slate-400">Also recorded as: {p.aliases.join(", ")}</p>
              )}
              <p className="mt-2 text-xs text-slate-400">
                Operates in: {p.stats.districts.join(", ")}
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {p.stats.crime_types.map(([t, n]) => (
                  <span key={t} className="rounded bg-navy-700 px-2 py-0.5 text-[11px] text-slate-300">
                    {t} · {n}
                  </span>
                ))}
              </div>
            </div>
            <RiskGauge risk={p.risk} />
          </div>

          {p.network?.nodes?.length > 0 && (
            <Section title={`Network — ${p.network.nodes.length} nodes`}>
              <Chart option={graphOption(p.network)} height={360} />
              {p.network.narrative && (
                <p className="mt-2 text-sm text-slate-300">{p.network.narrative}</p>
              )}
            </Section>
          )}

          {p.co_accused?.length > 0 && (
            <Section title="Known associates (co-accused)">
              <div className="flex flex-wrap gap-2">
                {p.co_accused.map((c) => (
                  <button key={c.person_key} onClick={() => navigate(`/person/${c.person_key}`)}
                    className="rounded-lg border border-navy-700 px-3 py-1 text-sm hover:bg-navy-800">
                    {c.name} <span className="text-xs text-slate-500">· {c.shared_cases} shared</span>
                  </button>
                ))}
              </div>
            </Section>
          )}

          <Section title={`Case history (${p.cases.length})`}>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-navy-900 text-left text-slate-400">
                  <tr><th className="py-1">date</th><th>case</th><th>offence</th><th>station</th><th>status</th></tr>
                </thead>
                <tbody>
                  {p.cases.map((c) => (
                    <tr key={c.case_id} className="border-t border-navy-800">
                      <td className="py-1 text-slate-400">{c.date}</td>
                      <td className="font-mono text-xs">C-{c.case_id}</td>
                      <td>{c.crime_sub_head}</td>
                      <td className="text-slate-400">{c.police_station}</td>
                      <td className={c.case_status === "Under Investigation" ? "text-amber-400" : "text-emerald-400"}>
                        {c.case_status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-white">{value}</div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="rounded-lg border border-navy-700 bg-navy-900 p-4">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</div>
      {children}
    </div>
  );
}
