// Central API client. Dev uses the Vite proxy (/api). Production reads
// VITE_API_BASE (Catalyst API Gateway URL) at build time.
const BASE = import.meta.env.VITE_API_BASE || "";

export async function apiGet(path) {
  const resp = await fetch(`${BASE}${path}`);
  if (!resp.ok) throw new Error(`${path} → ${resp.status}`);
  return resp.json();
}

export async function apiPost(path, body) {
  const resp = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!resp.ok) throw new Error(`${path} → ${resp.status}`);
  return resp.json();
}

// Open an SSE stream for an investigation run. Returns the EventSource.
export function openInvestigationStream(runId, onEvent, onError) {
  const es = new EventSource(`${BASE}/api/investigate/${runId}/stream`);
  const handler = (name) => (e) => {
    try {
      onEvent(name, JSON.parse(e.data));
    } catch {
      /* ignore malformed frame */
    }
  };
  es.addEventListener("agent_step", handler("agent_step"));
  es.addEventListener("pack_ready", (e) => {
    handler("pack_ready")(e);
    es.close();
  });
  es.onerror = () => {
    if (onError) onError();
    es.close();
  };
  return es;
}

export const apiBase = BASE;
