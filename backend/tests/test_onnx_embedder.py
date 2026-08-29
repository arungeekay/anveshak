"""Runtime ONNX embedding (FINALE_PLAN F-05).

The deployed image has no torch, so ONNX Runtime is what lets the live app embed
text a judge types on stage. Its output must be interchangeable with the
precomputed CaseMOVector corpus (built with sentence-transformers, ADR-5) — if the
pooling drifts, linkage on new FIRs silently degrades.

Skipped when models/minilm-onnx is absent (produce it with
`python scripts/fetch_onnx_model.py`).
"""
from __future__ import annotations

import numpy as np
import pytest

from backend.embeddings.onnx_embedder import MODEL_DIR, embed, embed_one

pytestmark = pytest.mark.skipif(
    not MODEL_DIR.exists(),
    reason=f"{MODEL_DIR} not built — run scripts/fetch_onnx_model.py")

CHAIN_SNATCH = ("Two men on a black motorcycle snatched a gold chain from a woman "
                "walking alone; the pillion rider grabbed it and they escaped "
                "against one-way traffic with their visors down.")
BURGLARY = ("The complainant's house was unoccupied; the accused entered through "
            "the rear window and took gold ornaments.")
KANNADA = "ಕಪ್ಪು ಬಣ್ಣದ ಬೈಕಿನಲ್ಲಿ ಬಂದ ಇಬ್ಬರು ಚಿನ್ನದ ಸರವನ್ನು ಕಿತ್ತುಕೊಂಡು ಪರಾರಿಯಾದರು."


def test_shape_and_normalisation():
    v = embed([CHAIN_SNATCH, BURGLARY])
    assert v.shape == (2, 384)
    assert v.dtype == np.float32
    norms = np.linalg.norm(v, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4), norms


def test_similar_texts_score_higher_than_unrelated():
    """Semantics survive the ONNX round-trip."""
    a = embed_one(CHAIN_SNATCH)
    b = embed_one("Two persons on a motorcycle pulled a gold chain off a lady "
                  "walking by herself and sped away.")
    c = embed_one(BURGLARY)
    assert float(a @ b) > float(a @ c) + 0.1, "paraphrase must beat an unrelated MO"


def test_kannada_is_embedded_meaningfully():
    """The model is multilingual — the KN chain-snatching text must sit closer to
    the EN chain-snatching text than to an unrelated burglary."""
    kn = embed_one(KANNADA)
    assert float(kn @ embed_one(CHAIN_SNATCH)) > float(kn @ embed_one(BURGLARY))


def test_matches_the_precomputed_corpus():
    """A near-verbatim planted narrative must retrieve its own case.

    This is the real contract: runtime vectors and the CaseMOVector corpus (built
    by a different library) must live in the same space.
    """
    from backend.db import get_connection
    from backend.embeddings import matrix

    con = get_connection()
    matrix.ensure(con)
    row = con.execute(
        "SELECT CaseMasterID, BriefFacts FROM CaseMaster WHERE CaseMasterID = 4001"
    ).fetchone()
    assert row, "planted SH-07 case 4001 missing"
    case_id, narrative = int(row[0]), row[1]

    hits = matrix.search(con, embed_one(narrative), k=3)
    assert hits, "no matches for a corpus narrative"
    top_id, top_cos = hits[0]
    assert top_id == case_id, f"expected case {case_id} first, got {hits}"
    assert top_cos > 0.99, f"cosine {top_cos:.4f} — runtime/corpus spaces disagree"


def test_empty_input_is_safe():
    assert embed([]).shape == (0, 384)
