"""LLM adapter (ADR-4): QuickML LLM Serving with an Ollama dev fallback.

Backend is env-switched via LLM_BACKEND (quickml | ollama). The interface is
identical regardless of backend so the rest of the app never branches on it.
One retry on transport error; token counts are logged.

QuickML note: docs/catalyst/quickml.md documents the auth headers and model roster
(Qwen 2.5 14B Instruct is the default), but the concrete request/response JSON must
be copied from the console API Details panel. `_quickml_chat` implements the header
contract and an OpenAI-style body/parse as a starting point and raises a clear error
until QUICKML_ENDPOINT/KEY are configured.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import httpx

from ..config import settings

log = logging.getLogger("anveshak.llm")

Message = dict[str, str]  # {"role": "system|user|assistant", "content": "..."}


@dataclass
class ChatResult:
    text: str
    backend: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMError(RuntimeError):
    """Transport/backend failure after retries."""


class LLMNotConfigured(LLMError):
    """The selected backend is missing required configuration."""


def _post_with_retry(url: str, json: dict, headers: dict | None = None, timeout: float = 120.0) -> dict:
    last: Exception | None = None
    for attempt in range(2):  # one retry
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=json, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last = exc
            log.warning("LLM POST failed (attempt %d/2): %s", attempt + 1, exc)
            time.sleep(0.5)
    raise LLMError(f"LLM request failed after retries: {last}")


def _ollama_chat(msgs: list[Message], temperature: float, max_tokens: int) -> ChatResult:
    url = settings.ollama_host.rstrip("/") + "/api/chat"
    payload = {
        "model": settings.ollama_model, "messages": msgs, "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    data = _post_with_retry(url, payload)
    text = (data.get("message") or {}).get("content", "").strip()
    pt, ct = int(data.get("prompt_eval_count", 0)), int(data.get("eval_count", 0))
    log.info("ollama chat model=%s prompt_tokens=%d completion_tokens=%d",
             settings.ollama_model, pt, ct)
    return ChatResult(text=text, backend="ollama", model=settings.ollama_model,
                      prompt_tokens=pt, completion_tokens=ct)


def _extract_text(data: dict) -> str:
    if isinstance(data, dict):
        if "choices" in data:  # OpenAI-style
            return data["choices"][0]["message"]["content"].strip()
        for k in ("output", "text", "response", "content", "generated_text"):
            if isinstance(data.get(k), str):
                return data[k].strip()
    return str(data)


def _quickml_token() -> str:
    """Zoho OAuth token for QuickML. From env/config, or the AppSail app context (SDK)."""
    if settings.quickml_token:
        return settings.quickml_token
    tok = os.getenv("ZOHO_OAUTH_TOKEN", "")
    if tok:
        return tok
    try:  # inside AppSail the SDK can mint an app-scoped token
        import zcatalyst_sdk

        app = zcatalyst_sdk.initialize()
        cred = app.credential()
        return cred.token() if hasattr(cred, "token") else ""
    except Exception:
        return ""


class _HeaderReq:
    """Minimal request wrapper exposing .headers with the ORIGINAL header case, so the
    SDK's `dict(request.headers)` sees Catalyst's headers exactly as sent."""

    def __init__(self, raw_headers) -> None:
        self.headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in raw_headers}


def _quickml_via_sdk(payload: dict, org: str) -> dict | None:
    """Call the GLM endpoint through the Catalyst SDK's authorized client, which
    injects the admin OAuth token (from the incoming request's Catalyst headers)
    automatically inside AppSail. Returns None if no request context / SDK is present."""
    from .request_ctx import current_request

    req = current_request.get()
    if req is None:
        return None
    try:
        import zcatalyst_sdk
        from zcatalyst_sdk._http_client import AuthorizedHttpClient
        from zcatalyst_sdk.quick_ml import CatalystService, CredentialUser

        app = zcatalyst_sdk.initialize(req=_HeaderReq(req.headers.raw))
        client = AuthorizedHttpClient(app)
        resp = client.request(
            method="POST", url=settings.quickml_endpoint,
            user=CredentialUser.ADMIN, catalyst_service=CatalystService.QUICK_ML,
            external=True, json=payload,
            headers={"Content-Type": "application/json", "CATALYST-ORG": org},
        )
        return resp.response_json
    except Exception as exc:
        log.warning("QuickML SDK path unavailable (%s); trying manual token", exc)
        return None


def _quickml_chat(msgs: list[Message], temperature: float, max_tokens: int) -> ChatResult:
    if not settings.quickml_endpoint:
        raise LLMNotConfigured("QUICKML_ENDPOINT not set. See docs/catalyst/quickml.md.")
    org = settings.quickml_org or settings.catalyst_project_id
    payload = {
        "model": settings.quickml_model, "messages": msgs, "max_tokens": max_tokens,
        "temperature": temperature, "stream": False,
        "chat_template_kwargs": {"enable_thinking": settings.quickml_thinking},
    }
    data = _quickml_via_sdk(payload, org)
    if data is None:  # fallback: explicit token (env / Self-Client)
        token = _quickml_token()
        if not token:
            raise LLMNotConfigured(
                "QuickML auth unavailable: the Catalyst SDK could not supply a token and "
                "QUICKML_TOKEN is unset. Runs automatically inside AppSail."
            )
        data = _post_with_retry(settings.quickml_endpoint, payload, headers={
            "Content-Type": "application/json", "CATALYST-ORG": org,
            "Authorization": f"Zoho-oauthtoken {token}"})
    usage = data.get("usage", {}) if isinstance(data, dict) else {}
    text = _extract_text(data)  # OpenAI-style choices[0].message.content
    log.info("quickml chat model=%s prompt_tokens=%s completion_tokens=%s",
             settings.quickml_model, usage.get("prompt_tokens"), usage.get("completion_tokens"))
    return ChatResult(text=text, backend="quickml", model=settings.quickml_model,
                      prompt_tokens=int(usage.get("prompt_tokens", 0)),
                      completion_tokens=int(usage.get("completion_tokens", 0)))


def chat(messages: list[Message], *, system: str | None = None, temperature: float = 0.0,
         max_tokens: int = 512, backend: str | None = None) -> ChatResult:
    """Send a chat completion request to the configured backend."""
    backend = backend or settings.llm_backend
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    if backend == "ollama":
        return _ollama_chat(msgs, temperature, max_tokens)
    if backend == "quickml":
        return _quickml_chat(msgs, temperature, max_tokens)
    raise LLMNotConfigured(f"unknown LLM backend: {backend!r}")


def ping(backend: str | None = None) -> bool:
    """Cheap reachability check for the selected backend."""
    backend = backend or settings.llm_backend
    try:
        if backend == "ollama":
            with httpx.Client(timeout=5.0) as client:
                return client.get(settings.ollama_host.rstrip("/") + "/api/tags").status_code == 200
        if backend == "quickml":
            return bool(settings.quickml_endpoint)
    except httpx.HTTPError:
        return False
    return False
