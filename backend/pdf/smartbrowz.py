"""Investigation Pack HTML -> PDF via Catalyst SmartBrowz (FINALE_PLAN F-08).

We claim a "court-ready Investigation Pack PDF"; this is what makes the claim
literal. SmartBrowz is the platform's own rendering service, so the pack is
produced entirely on Catalyst (no external PDF service, consistent with ADR-4's
spirit).

Authentication follows the same pattern as the QuickML adapter: the Catalyst SDK is
initialised from the *incoming request's* headers, which is the only context in
which AppSail can authorise a platform call.

Degrades honestly: if SmartBrowz is unavailable the caller falls back to the HTML
pack (which carries print CSS), so the button is never dead in front of a jury.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..llm.request_ctx import current_request

log = logging.getLogger("anveshak.pdf")

CACHE_DIR = Path("/tmp/packs")

PDF_OPTIONS = {
    "format": "A4",
    "print_background": True,
    "display_header_footer": False,
    "landscape": False,
    "scale": 1,
}


class SmartBrowzUnavailable(RuntimeError):
    """SmartBrowz could not be reached or is not configured."""


def _catalyst_app():
    """Initialise the Catalyst SDK from the current request's headers."""
    req = current_request.get()
    if req is None:
        raise SmartBrowzUnavailable(
            "no request context — SmartBrowz needs the incoming Catalyst headers")
    try:
        import zcatalyst_sdk
    except ImportError as exc:  # pragma: no cover - SDK always present in prod
        raise SmartBrowzUnavailable("zcatalyst_sdk not installed") from exc

    class _HeaderReq:
        """Minimal request shim; header CASE must be preserved for the SDK."""

        def __init__(self, raw_headers):
            self.headers = {k.decode("latin-1"): v.decode("latin-1")
                            for k, v in raw_headers}

    try:
        return zcatalyst_sdk.initialize(req=_HeaderReq(req.headers.raw))
    except Exception as exc:  # noqa: BLE001
        raise SmartBrowzUnavailable(f"SDK init failed: {exc}") from exc


def html_to_pdf(html: str) -> bytes:
    """Render an HTML string to PDF bytes via SmartBrowz."""
    app = _catalyst_app()
    try:
        browz = app.smart_browz()
        out = browz.convert_to_pdf(html, pdf_options=PDF_OPTIONS)
    except Exception as exc:  # noqa: BLE001 - surface as a typed failure
        raise SmartBrowzUnavailable(f"convert_to_pdf failed: {exc}") from exc

    data = out if isinstance(out, bytes | bytearray) else getattr(out, "content", None)
    if not data:
        raise SmartBrowzUnavailable("SmartBrowz returned no PDF content")
    if not bytes(data).startswith(b"%PDF"):
        raise SmartBrowzUnavailable("SmartBrowz response was not a PDF")
    return bytes(data)


def pack_pdf(series_id: str, html: str, *, use_cache: bool = True) -> bytes:
    """PDF for one series' pack, cached under /tmp (the only writable path)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{series_id}.pdf"
    if use_cache and path.exists() and path.stat().st_size > 1000:
        return path.read_bytes()
    data = html_to_pdf(html)
    try:
        path.write_bytes(data)
    except Exception as exc:  # noqa: BLE001 - caching is best-effort
        log.warning("could not cache pack pdf: %s", exc)
    return data
