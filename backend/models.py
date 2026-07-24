"""Pydantic request/response models mirroring contracts.md."""
from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str = "s-default"
    message: str
    lang: str = "en"  # en | kn
    followup_context: str | None = None
