"""Process-wide cache of the precomputed MO embedding matrix (CaseMOVector).

Loading + L2-normalising all ~15k vectors from DuckDB costs ~1.5s. `similar_cases`
used to pay that on EVERY call, and the Investigation Cell calls it 16 times per
run (~25s), which pushed the SSE run past the AppSail gateway's ~40s cut
(FINALE_PLAN F-03). We load once, normalise once, and reuse.

The cache is also the substrate for text-query search (`/api/similar/by_text`,
FINALE_PLAN F-06): a runtime-embedded narrative is just another query vector.

Thread-safety: built under a lock, then treated as immutable. `add()` appends a
new case (FIR intake) under the same lock by rebuilding the arrays, appends are
rare (one per intake) and this keeps readers lock-free on immutable snapshots.
"""
from __future__ import annotations

import threading

import numpy as np

_lock = threading.Lock()
_ids: np.ndarray | None = None      # shape (n,)   int64  case ids
_mat: np.ndarray | None = None      # shape (n, d) float32, L2-normalised rows
_index: dict[int, int] = {}         # case_id -> row


def _load(con) -> None:
    """Build the normalised matrix from CaseMOVector. Caller holds the lock."""
    global _ids, _mat, _index
    rows = con.execute(
        "SELECT CaseMasterID, embedding FROM CaseMOVector "
        "WHERE embedding IS NOT NULL ORDER BY CaseMasterID"
    ).fetchall()
    if not rows:
        _ids, _mat, _index = np.zeros(0, dtype=np.int64), None, {}
        return
    ids = np.fromiter((int(r[0]) for r in rows), dtype=np.int64, count=len(rows))
    mat = np.asarray([r[1] for r in rows], dtype=np.float32)
    mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
    _ids, _mat = ids, mat
    _index = {int(cid): i for i, cid in enumerate(ids)}


def ensure(con) -> None:
    """Load the matrix once (idempotent, stampede-safe)."""
    if _mat is not None:
        return
    with _lock:
        if _mat is None:
            _load(con)


def reset() -> None:
    """Drop the cache (after a mirror rebuild or in tests)."""
    global _ids, _mat, _index
    with _lock:
        _ids, _mat, _index = None, None, {}


def size() -> int:
    return 0 if _mat is None else int(_mat.shape[0])


def vector_for(con, case_id: int) -> np.ndarray | None:
    """Return the normalised vector for a case, or None if it has no embedding."""
    ensure(con)
    i = _index.get(int(case_id))
    if i is None or _mat is None:
        return None
    return _mat[i]


def search(con, query: np.ndarray, k: int = 5, *, exclude: int | None = None
           ) -> list[tuple[int, float]]:
    """Top-k (case_id, cosine) for a query vector; the vector is normalised here."""
    ensure(con)
    if _mat is None or _ids is None or _mat.shape[0] == 0:
        return []
    q = np.asarray(query, dtype=np.float32).ravel()
    q = q / (np.linalg.norm(q) + 1e-9)
    sims = _mat @ q
    if exclude is not None:
        i = _index.get(int(exclude))
        if i is not None:
            sims[i] = -np.inf
    n = min(k, sims.shape[0])
    # argpartition avoids a full sort of 15k similarities on every call.
    idx = np.argpartition(-sims, n - 1)[:n]
    idx = idx[np.argsort(-sims[idx])]
    return [(int(_ids[i]), float(sims[i])) for i in idx if np.isfinite(sims[i])]


def add(con, case_id: int, embedding) -> None:
    """Append a newly embedded case (FIR intake) to the cached matrix."""
    global _ids, _mat, _index
    ensure(con)
    vec = np.asarray(embedding, dtype=np.float32).ravel()
    vec = vec / (np.linalg.norm(vec) + 1e-9)
    with _lock:
        if _mat is None or _ids is None or _mat.shape[0] == 0:
            _ids = np.array([int(case_id)], dtype=np.int64)
            _mat = vec.reshape(1, -1)
        elif int(case_id) in _index:
            _mat[_index[int(case_id)]] = vec  # re-embed in place
            return
        else:
            _ids = np.append(_ids, np.int64(case_id))
            _mat = np.vstack([_mat, vec])
        _index = {int(cid): i for i, cid in enumerate(_ids)}
