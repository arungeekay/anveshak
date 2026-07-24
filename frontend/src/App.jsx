import { useEffect, useState } from "react";
import { apiGet } from "./lib/api.js";

export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet("/api/health").then(setHealth).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
      <header className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-white">
          ANVESHAK <span className="font-kannada text-navy-600">ಅನ್ವೇಷಕ</span>
        </h1>
        <p className="mt-2 text-slate-400">
          Autonomous AI Investigation Bureau · Karnataka State Police
        </p>
      </header>

      <div className="w-full max-w-md rounded-xl border border-navy-700 bg-navy-900 p-6 shadow-lg">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Backend health
        </h2>
        {error && (
          <p className="text-red-400">Cannot reach API: {error}</p>
        )}
        {!error && !health && <p className="text-slate-400">Checking…</p>}
        {health && (
          <pre className="overflow-x-auto rounded-lg bg-navy-950 p-4 text-sm text-emerald-300">
            {JSON.stringify(health, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
