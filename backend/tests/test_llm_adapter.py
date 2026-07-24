"""T08 verify: LLM adapter parsing + backend switching; live Ollama if reachable."""
from __future__ import annotations

import pytest

from backend.llm import adapter


def test_ollama_response_parsing(monkeypatch):
    fake = {"message": {"content": "  SELECT 1  "}, "prompt_eval_count": 12, "eval_count": 3}
    monkeypatch.setattr(adapter, "_post_with_retry", lambda *a, **k: fake)
    res = adapter.chat([{"role": "user", "content": "hi"}], backend="ollama")
    assert res.text == "SELECT 1"
    assert res.backend == "ollama"
    assert res.prompt_tokens == 12 and res.completion_tokens == 3


def test_openai_style_extract(monkeypatch):
    fake = {"choices": [{"message": {"content": "hello"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
    monkeypatch.setattr(adapter.settings, "quickml_endpoint", "https://example.invalid/serve")
    monkeypatch.setattr(adapter, "_post_with_retry", lambda *a, **k: fake)
    res = adapter.chat([{"role": "user", "content": "hi"}], backend="quickml")
    assert res.text == "hello"
    assert res.backend == "quickml"


def test_quickml_not_configured(monkeypatch):
    monkeypatch.setattr(adapter.settings, "quickml_endpoint", "")
    with pytest.raises(adapter.LLMNotConfigured):
        adapter.chat([{"role": "user", "content": "hi"}], backend="quickml")


def test_unknown_backend():
    with pytest.raises(adapter.LLMNotConfigured):
        adapter.chat([{"role": "user", "content": "hi"}], backend="nope")


@pytest.mark.skipif(not adapter.ping("ollama"), reason="Ollama not reachable")
def test_live_ollama_generation():
    res = adapter.chat(
        [{"role": "user", "content": "Reply with the single word: OK"}],
        backend="ollama", max_tokens=8,
    )
    assert res.text  # non-empty
    assert res.backend == "ollama"
