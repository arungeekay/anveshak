import { useState } from "react";
import { HashRouter, NavLink, Route, Routes } from "react-router-dom";
import Chat from "./views/Chat.jsx";
import Series from "./views/Series.jsx";
import GraphView from "./views/GraphView.jsx";
import Leads from "./views/Leads.jsx";
import Investigation from "./views/Investigation.jsx";
import Audit from "./views/Audit.jsx";

const ROLES = ["SCRB", "SP", "SHO", "ANALYST"];
const NAV = [
  ["/", "Chat", "💬"],
  ["/leads", "Lead Feed", "📡"],
  ["/series", "Series", "🔗"],
  ["/graph", "CrimeGraph", "🕸️"],
  ["/investigate", "Investigation Room", "🗂️"],
  ["/audit", "Audit", "📜"],
];

export default function App() {
  const [role, setRole] = useState("SCRB");
  return (
    <HashRouter>
      <div className="flex min-h-screen">
        <aside className="w-56 shrink-0 border-r border-navy-800 bg-navy-900 p-4">
          <div className="mb-6">
            <h1 className="text-xl font-bold text-white">ANVESHAK</h1>
            <p className="font-kannada text-sm text-navy-600">ಅನ್ವೇಷಕ · KSP</p>
          </div>
          <nav className="space-y-1">
            {NAV.map(([to, label, icon]) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                    isActive ? "bg-navy-700 text-white" : "text-slate-400 hover:bg-navy-800"
                  }`
                }
              >
                <span>{icon}</span>
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <div className="flex flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-navy-800 bg-navy-900/60 px-6 py-3">
            <span className="text-sm text-slate-400">Autonomous AI Investigation Bureau</span>
            <label className="flex items-center gap-2 text-sm" title="Role-based access control (RBAC) scope injection is designed per ADR-8; server-side enforcement lands with Catalyst Auth.">
              <span className="text-slate-400">Role</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="rounded-lg border border-navy-700 bg-navy-800 px-2 py-1 text-white"
              >
                {ROLES.map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
              <span className="rounded bg-navy-700 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">preview</span>
            </label>
          </header>

          <main className="flex-1 overflow-y-auto p-6">
            <Routes>
              <Route path="/" element={<Chat role={role} />} />
              <Route path="/leads" element={<Leads />} />
              <Route path="/series" element={<Series />} />
              <Route path="/graph" element={<GraphView />} />
              <Route path="/investigate" element={<Investigation />} />
              <Route path="/audit" element={<Audit />} />
            </Routes>
          </main>
        </div>
      </div>
    </HashRouter>
  );
}
