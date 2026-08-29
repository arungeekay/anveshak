"""Morning briefing (contracts.md §9, FINALE_PLAN F-16).

One button produces the ~30-second brief a District SP would want at 7am: what the
overnight sweep found, in Kannada or English. The frontend speaks it with the
browser's kn-IN voice.

Composed from FIXED templates with tool values slotted in — never free-form LLM
Kannada. Two reasons: GLM's unprompted Kannada is unreliable enough to swap a
subject on stage, and ADR-2 says numbers come from tools, not the model.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..db import data_max_date, get_connection
from ..patrol.store import leads_store

router = APIRouter()

# One sentence per detector type, in both languages. {} slots are filled from the
# lead's own evidence — no number here is authored by a model.
_LEAD_TEMPLATES = {
    "spike": {
        "en": "{title} — {value} times the usual level over the {window}, {cases} cases. Suggested action: {action}",
        "kn": "{ps} ಠಾಣಾ ವ್ಯಾಪ್ತಿಯಲ್ಲಿ ಅಪರಾಧ ಪ್ರಮಾಣ ಸಾಮಾನ್ಯಕ್ಕಿಂತ {value} ಪಟ್ಟು ಹೆಚ್ಚಾಗಿದೆ. {cases} ಪ್ರಕರಣಗಳು ದಾಖಲಾಗಿವೆ.",
    },
    "repeat_offender": {
        "en": "{title} — {value} unsolved cases match his pattern within 3 km of his residence.",
        "kn": "ಪುನರಾವರ್ತಿತ ಅಪರಾಧಿಯ ಸುಳಿವು: ಅವರ ನಿವಾಸದ 3 ಕಿ.ಮೀ ವ್ಯಾಪ್ತಿಯಲ್ಲಿ {value} ಬಗೆಹರಿಯದ ಪ್ರಕರಣಗಳು ಅವರ ಮಾದರಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತವೆ.",
    },
    "series_growth": {
        "en": "{title} — the series now spans {cases} linked cases.",
        "kn": "ಸರಣಿ ಅಪರಾಧ ಬೆಳೆಯುತ್ತಿದೆ: ಈಗ {cases} ಪ್ರಕರಣಗಳು ಸಂಪರ್ಕ ಹೊಂದಿವೆ.",
    },
}

_OPENING = {
    "en": "Good morning. Overnight, ANVESHAK reviewed the state crime database and raised {n} leads as of {date}.",
    "kn": "ಶುಭೋದಯ. ನಿನ್ನೆ ರಾತ್ರಿ ANVESHAK ರಾಜ್ಯದ ಅಪರಾಧ ದತ್ತಸಂಚಯವನ್ನು ಪರಿಶೀಲಿಸಿ {n} ಸುಳಿವುಗಳನ್ನು ಗುರುತಿಸಿದೆ. ದಿನಾಂಕ {date}.",
}
_CLOSING = {
    "en": "That is the overnight summary. Full evidence for each lead is in the Lead Feed.",
    "kn": "ಇದು ರಾತ್ರಿಯ ಸಾರಾಂಶ. ಪ್ರತಿ ಸುಳಿವಿನ ಸಂಪೂರ್ಣ ಸಾಕ್ಷ್ಯ ಲೀಡ್ ಫೀಡ್‌ನಲ್ಲಿ ಲಭ್ಯವಿದೆ.",
}
_NO_LEADS = {
    "en": "Good morning. ANVESHAK reviewed the state crime database overnight and found no new leads meeting the alert thresholds.",
    "kn": "ಶುಭೋದಯ. ನಿನ್ನೆ ರಾತ್ರಿ ANVESHAK ಪರಿಶೀಲನೆ ನಡೆಸಿತು; ಎಚ್ಚರಿಕೆ ಮಿತಿಯನ್ನು ಮೀರಿದ ಹೊಸ ಸುಳಿವುಗಳಿಲ್ಲ.",
}


def _sentence(lead: dict, lang: str) -> str:
    ev = lead.get("evidence") or {}
    tpl = _LEAD_TEMPLATES.get(lead.get("type"), {}).get(lang)
    if not tpl:
        return lead.get("title", "")
    title = lead.get("title", "")
    return tpl.format(
        title=title,
        ps=title.split("—")[-1].strip() if "—" in title else lead.get("district", ""),
        value=ev.get("value", ""),
        window=ev.get("window", ""),
        cases=len(ev.get("case_ids") or []),
        action=lead.get("suggested_action", ""),
        district=lead.get("district", ""),
    ).strip()


@router.get("/api/briefing")
def briefing(lang: str = "en", limit: int = 3) -> dict:
    """The spoken morning brief: opening, one sentence per top lead, closing."""
    lang = "kn" if lang == "kn" else "en"
    con = get_connection()
    leads = leads_store.ensure(con)
    top = sorted(leads, key=lambda x: x.get("confidence", 0), reverse=True)[:limit]

    if not top:
        return {"text": _NO_LEADS[lang], "lang": lang, "leads_cited": [],
                "as_of": str(data_max_date(con))}

    parts = [_OPENING[lang].format(n=len(leads), date=data_max_date(con))]
    parts += [_sentence(ld, lang) for ld in top]
    parts.append(_CLOSING[lang])
    return {
        "text": " ".join(p for p in parts if p),
        "lang": lang,
        "leads_cited": [ld.get("lead_id") for ld in top],
        "as_of": str(data_max_date(con)),
        "composed_from": "fixed templates + Night Patrol tool output (no model text)",
    }
