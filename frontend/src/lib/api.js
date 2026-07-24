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
    body: JSON.stringify(body),
  });
  if (!resp.ok) throw new Error(`${path} → ${resp.status}`);
  return resp.json();
}
