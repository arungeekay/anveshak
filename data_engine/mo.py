"""Shared MO feature extraction + narrative embeddings (ADR-5).

data_engine precomputes CaseMOVector at build time; the linkage engine reuses the
SAME extractor at runtime for new cases so features are consistent. Keeps no
dependency on backend (backend/linkage imports from here).
"""
from __future__ import annotations

import datetime as _dt
import json
from typing import Any

import h3

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Keyword cues (EN + KN) -> structured MO slots.
_VEHICLE = {"motorcycle": ["motorcycle", "motor cycle", "bike", "two-wheeler", "ಮೋಟಾರ್ ಸೈಕಲ್", "ದ್ವಿಚಕ್ರ"],
            "car": ["car", "four-wheeler", "ಕಾರು"],
            "auto": ["auto", "rickshaw", "ಆಟೋ"]}
_TARGET = {"gold_chain": ["gold chain", "chain", "ಚಿನ್ನದ ಸರ", "ಸರ"],
           "cash": ["cash", "rs.", "rupees", "ನಗದು", "ರೂ."],
           "mobile": ["mobile", "phone", "ಮೊಬೈಲ್"],
           "jewellery": ["jewellery", "ornaments", "ಚಿನ್ನಾಭರಣ"],
           "vehicle": ["two-wheeler stolen", "bike stolen", "ವಾಹನ"]}
_ENTRY = {"rear_window": ["rear window", "rear-window", "ಹಿಂಬದಿ ಕಿಟಕಿ"],
          "door_break": ["broke the door", "door lock", "ಬಾಗಿಲು"],
          "grill_cut": ["cut the grill", "grill"]}
_WEAPON = {"knife": ["knife", "ಚಾಕು"], "firearm": ["pistol", "gun", "firearm"],
           "sharp_weapon": ["machete", "sharp weapon", "ಆಯುಧ"]}


def tod_bucket(hour: int) -> str:
    if 0 <= hour <= 5:
        return "night"
    if 6 <= hour <= 11:
        return "morning"
    if 12 <= hour <= 16:
        return "afternoon"
    if 17 <= hour <= 20:
        return "evening"
    return "late_evening"


def _match(text: str, table: dict[str, list[str]]) -> str | None:
    low = text.lower()
    for label, cues in table.items():
        for c in cues:
            if c.lower() in low:
                return label
    return None


def extract_features(brief: str | None, incident: Any, lat: float | None, lon: float | None) -> dict:
    """Structured MO features for one case."""
    brief = brief or ""
    hour, dow = 0, 0
    if isinstance(incident, _dt.datetime):  # pandas Timestamp subclasses datetime too
        hour, dow = int(incident.hour), int(incident.weekday())
    cell = None
    if lat is not None and lon is not None:
        try:
            cell = h3.latlng_to_cell(float(lat), float(lon), 8)
        except Exception:
            cell = None
    return {
        "tod_bucket": tod_bucket(hour),
        "dow": dow,
        "h3": cell,
        "weapon": _match(brief, _WEAPON),
        "vehicle": _match(brief, _VEHICLE),
        "entry": _match(brief, _ENTRY),
        "target": _match(brief, _TARGET),
    }


def features_json(brief, incident, lat, lon) -> str:
    return json.dumps(extract_features(brief, incident, lat, lon))


# --- Embeddings (lazy model load) ---
_model = None


def get_embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed_texts(texts: list[str]):
    """Return L2-normalized embeddings (numpy array) for a list of narratives."""
    model = get_embedder()
    return model.encode(texts, batch_size=64, show_progress_bar=False,
                        normalize_embeddings=True)
