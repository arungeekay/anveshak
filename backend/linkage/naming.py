"""Operation codenames and plain-language link explanations (FINALE_PLAN F-15).

Two small things that change how a series *reads* to a police audience:

* **Codename.** Indian policing runs on operation names. "SH-07 · Operation Black
  Visor" is remembered; "cluster 7" is not. Derived deterministically from the MO
  features the engine already matched on, so the name is evidence-derived rather
  than invented.
* **Link explanation.** A cosine of 0.94 means nothing to an investigating officer.
  "Both: two men, black motorcycle, gold chain, evening" is auditable, it names
  exactly what the engine matched on, turning the linkage from a black box into
  something a court could follow.

Both are template-composed from tool output (ADR-2). No model text.
"""
from __future__ import annotations

# MO feature value -> the evocative word used in a codename.
_CODEWORDS = {
    "vehicle": {"motorcycle": "Black Visor", "car": "Four Wheel", "auto": "Three Wheel"},
    "target": {"gold_chain": "Gold Chain", "cash": "Cash Run", "mobile": "Handset",
               "jewellery": "Ornament", "vehicle": "Wheels"},
    "entry": {"rear_window": "Rear Window", "door_break": "Broken Door",
              "grill_cut": "Cut Grill"},
    "weapon": {"knife": "Blade", "firearm": "Firearm", "sharp_weapon": "Sharp Edge"},
}
_TOD_WORD = {"night": "Night Watch", "morning": "Morning", "afternoon": "Afternoon",
             "evening": "Evening", "late_evening": "Late Hours"}

# Human-readable phrasing for each MO feature value, used in link explanations.
_FEATURE_WORDS = {
    "vehicle": {"motorcycle": "a motorcycle", "car": "a car", "auto": "an auto"},
    "target": {"gold_chain": "a gold chain", "cash": "cash", "mobile": "a mobile phone",
               "jewellery": "jewellery", "vehicle": "a vehicle"},
    "entry": {"rear_window": "entry through a rear window",
              "door_break": "a broken door lock", "grill_cut": "a cut grill"},
    "weapon": {"knife": "a knife", "firearm": "a firearm",
               "sharp_weapon": "a sharp weapon"},
    "tod_bucket": {"night": "at night", "morning": "in the morning",
                   "afternoon": "in the afternoon", "evening": "in the evening",
                   "late_evening": "late in the evening"},
}


def codename(hypothesis: dict, features: dict | None = None) -> str:
    """A short operation name derived from the series' dominant MO features.

    Deterministic: the same series always gets the same name, so it stays stable
    across refreshes and matches whatever an officer wrote down earlier.
    """
    feats = features or {}
    parts: list[str] = []
    # Most distinctive slots first, a motorcycle is common to many series, but the
    # target and the entry method are what actually characterise a ring.
    for slot in ("target", "entry", "weapon", "vehicle"):
        val = feats.get(slot)
        word = _CODEWORDS.get(slot, {}).get(val)
        if word:
            parts.append(word)
        if len(parts) == 2:
            break
    if not parts:
        tod = _TOD_WORD.get(feats.get("tod_bucket"))
        if tod:
            parts.append(tod)
    if not parts:
        # Last resort: the offence itself, so every series still gets a name.
        sub = (hypothesis.get("crime_sub_head") or "Series").split("(")[0].strip()
        parts.append(sub)
    return "Operation " + " ".join(parts[:2])


def assign_codenames(hypotheses: list[dict]) -> None:
    """Give every series a UNIQUE codename, in place.

    MO features repeat across series (many rings use a motorcycle), so the same
    name can be derived twice. A duplicate name is worse than none, officers would
    conflate two operations, so collisions are broken with the series' primary
    district, then with its id. Both are stable, so names never shift between runs.
    """
    used: set[str] = set()
    for h in hypotheses:
        base = codename(h, h.get("mo_features") or {})
        name = base
        if name in used:
            district = (h.get("districts") or [""])[0].split()[0]
            if district:
                name = f"{base} {district}"
        if name in used:
            name = f"{base} {h.get('series_id', '')}".strip()
        used.add(name)
        h["codename"] = name


def explain_link(shared_features: list[str], features: dict | None = None) -> str:
    """Plain-language rendering of what two linked cases actually share."""
    feats = features or {}
    phrases = []
    for f in shared_features or []:
        val = feats.get(f)
        word = _FEATURE_WORDS.get(f, {}).get(val)
        phrases.append(word or str(val or f).replace("_", " "))
    if not phrases:
        return "Both cases share a closely matching narrative."
    return "Both cases involve " + ", ".join(phrases) + "."
