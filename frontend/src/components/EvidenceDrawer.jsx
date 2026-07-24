import { useState } from "react";

export default function EvidenceDrawer({ evidence }) {
  const [open, setOpen] = useState(false);
  if (!evidence) return null;
  return (
    <div className="mt-2 rounded-lg border border-navy-700 bg-navy-950/60">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs text-slate-400 hover:text-slate-200"
      >
        <span>🔎 Evidence · tool: <b className="text-accent">{evidence.tool}</b>
          {evidence.row_count != null && ` · ${evidence.row_count} rows`}</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-navy-800 px-3 py-2 text-xs">
          {evidence.sql && (
            <pre className="overflow-x-auto rounded bg-black/40 p-2 text-emerald-300">{evidence.sql}</pre>
          )}
          {evidence.params && Object.keys(evidence.params).length > 0 && (
            <div className="text-slate-400">params: {JSON.stringify(evidence.params)}</div>
          )}
          {evidence.case_ids?.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {evidence.case_ids.slice(0, 40).map((id) => (
                <span key={id} className="rounded bg-navy-700 px-1.5 py-0.5 text-slate-300">C-{id}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
