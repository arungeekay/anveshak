"""Export the MO embedding model to ONNX for runtime use (FINALE_PLAN F-05).

The AppSail image deliberately ships no torch (the scientific stack already makes it
1.4GB), so the deployed app cannot embed new text with sentence-transformers. That
is fine for the corpus — CaseMOVector is precomputed at generation time (ADR-5) —
but it blocks anything a *judge* types on stage: a new FIR narrative joining a
series, free-text similarity search, duplicate detection.

ONNX Runtime is a ~15MB CPU dependency and runs the same MiniLM weights, so we
export once here and bundle the artefact into the image.

    python scripts/fetch_onnx_model.py            # export + verify parity
    python scripts/fetch_onnx_model.py --check    # verify an existing export

Output: models/minilm-onnx/{model.onnx, tokenizer files}. The directory is
gitignored (100-450MB); the Dockerfile COPYs it, so run this before docker build.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OUT_DIR = Path("models/minilm-onnx")
# The parity bar: cosine between the ONNX vector and the sentence-transformers
# vector for the same text. Anything below this and linkage results would drift
# from the precomputed CaseMOVector corpus.
PARITY_MIN = 0.99

PROBES = [
    "Two men on a black motorcycle snatched a gold chain from a woman walking alone.",
    "The accused broke the rear window of an unoccupied house and stole jewellery.",
    "ಸರಗಳ್ಳತನ ಪ್ರಕರಣ: ಕಪ್ಪು ಬಣ್ಣದ ಬೈಕಿನಲ್ಲಿ ಬಂದ ಇಬ್ಬರು ಚಿನ್ನದ ಸರವನ್ನು ಕಿತ್ತುಕೊಂಡರು.",
    "Investment fraud: the complainant transferred money to a mule account.",
    "Vehicle theft reported from a parking area near the market at night.",
]


def export() -> None:
    from optimum.onnxruntime import ORTModelForFeatureExtraction
    from transformers import AutoTokenizer

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"exporting {MODEL_ID} -> {OUT_DIR} …")
    model = ORTModelForFeatureExtraction.from_pretrained(MODEL_ID, export=True)
    model.save_pretrained(OUT_DIR)
    AutoTokenizer.from_pretrained(MODEL_ID).save_pretrained(OUT_DIR)
    total = sum(f.stat().st_size for f in OUT_DIR.rglob("*") if f.is_file())
    print(f"exported: {total / 1e6:.0f} MB")
    for f in sorted(OUT_DIR.iterdir()):
        print(f"  {f.name}  {f.stat().st_size / 1e6:.1f} MB")


def check_parity() -> bool:
    """ONNX output must match sentence-transformers on every probe."""
    import numpy as np

    sys.path.insert(0, str(Path.cwd()))
    from backend.embeddings.onnx_embedder import embed as onnx_embed

    print("\nparity check vs sentence-transformers")
    from sentence_transformers import SentenceTransformer
    st = SentenceTransformer(MODEL_ID)
    ref = st.encode(PROBES, batch_size=8, show_progress_bar=False,
                    normalize_embeddings=True)
    got = onnx_embed(PROBES)

    ok = True
    for i, text in enumerate(PROBES):
        cos = float(np.dot(ref[i], got[i]))
        flag = "OK " if cos >= PARITY_MIN else "BAD"
        if cos < PARITY_MIN:
            ok = False
        print(f"  [{flag}] cos={cos:.5f}  {text[:52]}…")
    print(f"\nparity {'PASSED' if ok else 'FAILED'} (min {PARITY_MIN})")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="only verify an existing export")
    args = ap.parse_args()
    if not args.check:
        export()
    if not OUT_DIR.exists():
        print(f"missing {OUT_DIR} — run without --check first")
        return 1
    return 0 if check_parity() else 1


if __name__ == "__main__":
    sys.exit(main())
