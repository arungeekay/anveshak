"""Runtime text embedding via ONNX Runtime (FINALE_PLAN F-05).

The deployed image ships no torch, so this is how the live app turns *new* text —
an FIR narrative a judge types or dictates on stage — into an MO vector comparable
with the precomputed CaseMOVector corpus (ADR-5).

It must reproduce `sentence_transformers.encode(..., normalize_embeddings=True)`
exactly: mean-pool the token embeddings using the attention mask, then L2-normalise.
`scripts/fetch_onnx_model.py --check` asserts cosine >= 0.99 against the real model
on EN and KN probes; if that ever fails, linkage would drift from the corpus.

Model files live in models/minilm-onnx (gitignored, COPYed into the image). If they
are absent the embedder falls back to sentence-transformers when installed (dev
machines), and otherwise raises a clear error rather than silently degrading.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import numpy as np

log = logging.getLogger("anveshak.embeddings")

MODEL_DIR = Path(os.getenv("ONNX_MODEL_DIR", "models/minilm-onnx"))
MAX_TOKENS = 256  # narratives are short; keeps latency ~30ms/text on CPU

_lock = threading.Lock()
_session = None
_tokenizer = None
_st_model = None  # dev fallback


class EmbedderUnavailable(RuntimeError):
    """No embedding backend is available in this process."""


def _load_onnx():
    """Load the ONNX session + tokenizer once (thread-safe, lazy ~2s)."""
    global _session, _tokenizer
    if _session is not None:
        return _session, _tokenizer
    with _lock:
        if _session is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer

            onnx_file = next(MODEL_DIR.glob("*.onnx"), None)
            if onnx_file is None:
                raise EmbedderUnavailable(f"no .onnx file in {MODEL_DIR}")
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2  # AppSail containers are small
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess = ort.InferenceSession(str(onnx_file), opts,
                                        providers=["CPUExecutionProvider"])
            tok = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
            tok.enable_truncation(max_length=MAX_TOKENS)
            tok.enable_padding()
            _session, _tokenizer = sess, tok
            log.info("onnx embedder ready (%s)", onnx_file.name)
    return _session, _tokenizer


def available() -> bool:
    """True if some embedding backend can serve a request."""
    try:
        _load_onnx()
        return True
    except Exception:  # noqa: BLE001 - probe only
        try:
            return _load_sentence_transformers() is not None
        except Exception:  # noqa: BLE001
            return False


def _load_sentence_transformers():
    """Dev-machine fallback: the real model, when torch is installed."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return _st_model


def _mean_pool(last_hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Mask-aware mean pooling — the pooling sentence-transformers uses here."""
    m = mask[..., None].astype(np.float32)
    summed = (last_hidden * m).sum(axis=1)
    counts = np.clip(m.sum(axis=1), 1e-9, None)
    return summed / counts


def embed(texts: list[str]) -> np.ndarray:
    """L2-normalised embeddings, shape (len(texts), dim), float32."""
    if isinstance(texts, str):
        texts = [texts]
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)

    try:
        sess, tok = _load_onnx()
    except Exception as exc:  # noqa: BLE001 - fall back on dev machines
        log.info("onnx unavailable (%s); trying sentence-transformers", exc)
        model = _load_sentence_transformers()
        if model is None:
            raise EmbedderUnavailable(
                "no ONNX model and no sentence-transformers") from exc
        return np.asarray(
            model.encode(texts, batch_size=16, show_progress_bar=False,
                         normalize_embeddings=True), dtype=np.float32)

    encs = tok.encode_batch(texts)
    ids = np.array([e.ids for e in encs], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
    feed = {"input_ids": ids, "attention_mask": mask}
    # This checkpoint's graph also takes token_type_ids; supply zeros when required.
    names = {i.name for i in sess.get_inputs()}
    if "token_type_ids" in names:
        feed["token_type_ids"] = np.zeros_like(ids)
    feed = {k: v for k, v in feed.items() if k in names}

    last_hidden = sess.run(None, feed)[0]
    vecs = _mean_pool(np.asarray(last_hidden, dtype=np.float32), mask)
    vecs /= (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
    return vecs.astype(np.float32)


def embed_one(text: str) -> np.ndarray:
    return embed([text])[0]
