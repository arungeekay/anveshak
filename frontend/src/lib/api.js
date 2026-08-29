// Central API client. When the SPA is served by the AppSail backend itself, BASE
// is empty and calls are same-origin (/api/*). VITE_API_BASE can override at build.
const BASE = import.meta.env.VITE_API_BASE || "";

// The active role travels on every request; the server enforces the scope (ADR-8).
// Hiding rows in the browser would not be access control.
let role = "SCRB";
let unit = null;
export function setRole(r, u = null) { role = r; unit = u; }
function authHeaders() {
  const h = { "X-Anveshak-Role": role };
  if (unit) h["X-Anveshak-Unit"] = unit;
  return h;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Parse a response body tolerantly: an empty body (which can happen on a transient
// blip) becomes null rather than throwing "Unexpected end of JSON input".
async function parseBody(resp, path) {
  if (!resp.ok) throw new Error(`${path} → ${resp.status}`);
  const text = await resp.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${path} → malformed response`);
  }
}

// One quiet retry smooths over transient 5xx / network / empty-body blips so the
// UI never flashes an error for a hiccup a re-fetch would fix. On a persistent
// failure it THROWS (never resolves to null) so callers' .catch handles it and no
// null ever reaches a component's .map().
async function withRetry(fn) {
  try {
    const out = await fn();
    if (out === null) throw new Error("empty");
    return out;
  } catch {
    await sleep(400);
    const out = await fn(); // a second failure/throw propagates to the caller
    if (out === null) throw new Error("empty response");
    return out;
  }
}

export async function apiGet(path) {
  return withRetry(async () =>
    parseBody(await fetch(`${BASE}${path}`, { headers: authHeaders() }), path));
}

export async function apiPost(path, body) {
  const opts = {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body || {}),
  };
  return withRetry(async () => parseBody(await fetch(`${BASE}${path}`, opts), path));
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
