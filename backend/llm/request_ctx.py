"""Per-request context so the LLM adapter can reach the incoming request's Catalyst
headers (which carry the admin token the SDK uses to authorize QuickML calls)."""
from __future__ import annotations

import contextvars

current_request: contextvars.ContextVar = contextvars.ContextVar("catalyst_request", default=None)
