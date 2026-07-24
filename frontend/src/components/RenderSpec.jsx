import Chart from "./Chart.jsx";
import MapView from "./MapView.jsx";

function Table({ table }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-400">
            {table.columns.map((c) => (
              <th key={c} className="border-b border-navy-700 px-2 py-1 font-medium">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r, i) => (
            <tr key={i} className="hover:bg-navy-800">
              {r.map((v, j) => (
                <td key={j} className="border-b border-navy-800 px-2 py-1">{String(v)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function RenderSpec({ spec }) {
  return (
    <div className="my-3 rounded-lg border border-navy-700 bg-navy-900/60 p-3">
      {spec.title && <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{spec.title}</div>}
      {(spec.type === "line" || spec.type === "bar" || spec.type === "graph") && spec.echarts_option && (
        <Chart option={spec.echarts_option} />
      )}
      {spec.type === "map" && spec.leaflet_spec && <MapView spec={spec.leaflet_spec} />}
      {spec.type === "table" && spec.table && <Table table={spec.table} />}
    </div>
  );
}
