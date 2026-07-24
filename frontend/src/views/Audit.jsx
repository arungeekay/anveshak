import { useEffect, useState } from "react";
import { apiGet } from "../lib/api.js";

export default function Audit() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState(null);
  useEffect(() => {
    apiGet("/api/audit?limit=100").then(setRows).catch((e) => setErr(e.message));
  }, []);
  return (
    <div className="mx-auto max-w-4xl">
      <h2 className="mb-4 text-lg font-semibold">Audit Log</h2>
      {err && <p className="text-red-400">{err}</p>}
      <div className="overflow-x-auto rounded-lg border border-navy-700">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-slate-400">
            <th className="px-3 py-2">ts</th><th>user</th><th>role</th><th>action</th><th>detail</th></tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-t border-navy-800">
                <td className="px-3 py-1 text-slate-400">{String(r.ts)}</td>
                <td>{r.user_id}</td><td>{r.role}</td><td className="text-accent">{r.action}</td>
                <td className="max-w-md truncate text-xs text-slate-400">{typeof r.detail === "string" ? r.detail : JSON.stringify(r.detail)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && !err && <p className="text-slate-500">No audit rows yet.</p>}
    </div>
  );
}
