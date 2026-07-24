import { useState } from "react";
import { apiPost } from "../lib/api.js";
import Chart from "../components/Chart.jsx";

const KIND_COLOR = { person: "#3b82f6", case: "#f59e0b", location: "#10b981", ps: "#a78bfa" };

function toOption(gr) {
  return {
    tooltip: {},
    series: [{
      type: "graph", layout: "force", roam: true,
      label: { show: true, color: "#cbd5e1", fontSize: 9 },
      force: { repulsion: 140, edgeLength: 70 },
      lineStyle: { color: "#475569", opacity: 0.6 },
      data: gr.nodes.map((n) => ({
        id: n.id, name: n.label,
        symbolSize: n.kind === "person" ? 34 : 16,
        itemStyle: { color: KIND_COLOR[n.kind] || "#94a3b8" },
      })),
      links: gr.edges.map((e) => ({ source: e.a, target: e.b })),
    }],
  };
}

export default function GraphView() {
  const [gr, setGr] = useState(null);
  const [narrative, setNarrative] = useState("");
  const [err, setErr] = useState(null);

  async function run(type, params) {
    setErr(null);
    try {
      const res = await apiPost("/api/graph/query", { type, params });
      setGr(res);
      setNarrative(res.narrative || "");
    } catch (e) { setErr(e.message); }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h2 className="mb-4 text-lg font-semibold">CrimeGraph</h2>
      <div className="mb-3 flex flex-wrap gap-2">
        <button onClick={() => run("ego_network", { person_key: "P-007001", depth: 1 })}
          className="rounded-lg border border-navy-700 px-3 py-1 text-sm hover:bg-navy-800">Prakash Rao hub</button>
        <button onClick={() => run("ego_network", { person_key: "P-004412", depth: 2 })}
          className="rounded-lg border border-navy-700 px-3 py-1 text-sm hover:bg-navy-800">Ravi K network</button>
        <button onClick={() => run("path_between", { person_a: "P-004412", person_b: "P-004413" })}
          className="rounded-lg border border-navy-700 px-3 py-1 text-sm hover:bg-navy-800">Ravi ↔ Manju path</button>
      </div>
      {err && <p className="text-red-400">{err}</p>}
      {narrative && <p className="mb-2 rounded-lg bg-navy-900 p-3 text-sm text-slate-300">{narrative}</p>}
      {gr && (
        <div className="rounded-lg border border-navy-700 bg-navy-900/60 p-2">
          <Chart option={toOption(gr)} height={460} />
        </div>
      )}
      {!gr && !err && <p className="text-slate-500">Pick a query above to render the network.</p>}
    </div>
  );
}
