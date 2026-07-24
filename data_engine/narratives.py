"""MO narrative template families (EN + KN) and name pools.

demo_story.md: BriefFacts are 70% English / 30% Kannada, generated from template
families with slot variation (never identical copy-paste). The linkage engine feeds
on these narratives, so MO invariants must survive slot substitution.
"""
from __future__ import annotations

import random

FIRST_NAMES_EN = [
    "Ravi", "Manju", "Suresh", "Prakash", "Lakshmi", "Anitha", "Girish", "Kavya",
    "Naveen", "Deepa", "Shivkumar", "Rekha", "Mahesh", "Sunitha", "Vasanth",
    "Bhavya", "Ramesh", "Nagaraj", "Pooja", "Harish", "Sowmya", "Kiran", "Divya",
    "Manoj", "Chaitra", "Vijay", "Ashwini", "Prashant", "Roopa", "Sandeep",
]
LAST_NAMES_EN = [
    "Kumar", "Gowda", "Reddy", "Shetty", "Rao", "Naik", "Hegde", "Patil", "Murthy",
    "Prasad", "Achar", "Bhat", "Setty", "Poojary", "Desai", "Kulkarni", "Nayak",
]
FIRST_NAMES_KN = [
    "ರವಿ", "ಮಂಜು", "ಸುರೇಶ್", "ಪ್ರಕಾಶ್", "ಲಕ್ಷ್ಮಿ", "ಅನಿತಾ", "ಗಿರೀಶ್", "ಕಾವ್ಯ",
    "ನವೀನ್", "ದೀಪಾ", "ಶಿವಕುಮಾರ್", "ರೇಖಾ", "ಮಹೇಶ್", "ಸುನೀತಾ", "ವಸಂತ್", "ಭವ್ಯ",
    "ರಮೇಶ್", "ನಾಗರಾಜ್", "ಪೂಜಾ", "ಹರೀಶ್", "ಸೌಮ್ಯ", "ಕಿರಣ್", "ದಿವ್ಯಾ", "ಮನೋಜ್",
]
LAST_NAMES_KN = [
    "ಕುಮಾರ್", "ಗೌಡ", "ರೆಡ್ಡಿ", "ಶೆಟ್ಟಿ", "ರಾವ್", "ನಾಯಕ್", "ಹೆಗ್ಡೆ", "ಪಾಟೀಲ್",
    "ಮೂರ್ತಿ", "ಪ್ರಸಾದ್", "ಭಟ್", "ದೇಸಾಯಿ",
]

_AREAS_EN = [
    "the main market", "the bus stand", "the temple street", "the lake road",
    "the ring road junction", "the vegetable market", "the railway gate",
    "the college road", "the bank street", "the arterial road", "the flyover",
]
_AREAS_KN = [
    "ಮುಖ್ಯ ಮಾರುಕಟ್ಟೆ", "ಬಸ್ ನಿಲ್ದಾಣ", "ದೇವಸ್ಥಾನ ರಸ್ತೆ", "ಕೆರೆ ರಸ್ತೆ",
    "ರಿಂಗ್ ರಸ್ತೆ ಜಂಕ್ಷನ್", "ತರಕಾರಿ ಮಾರುಕಟ್ಟೆ", "ಕಾಲೇಜು ರಸ್ತೆ",
]
_BIKES = ["Pulsar", "Splendor", "Apache", "FZ", "Passion", "Duke"]
_DIRECTIONS = ["the highway", "the market lane", "the bypass", "the residential layout"]
_DIRECTIONS_KN = ["ಹೆದ್ದಾರಿ", "ಮಾರುಕಟ್ಟೆ ರಸ್ತೆ", "ಬೈಪಾಸ್", "ವಸತಿ ಪ್ರದೇಶ"]
_APPS = ["QuickWealth", "GrowRupee", "FastProfit", "TradeMax", "GoldenReturns"]
_ITEMS = ["mobile phone", "laptop", "cash", "gold ornaments", "two-wheeler"]
_ITEMS_KN = ["ಮೊಬೈಲ್ ಫೋನ್", "ಲ್ಯಾಪ್‌ಟಾಪ್", "ನಗದು", "ಚಿನ್ನಾಭರಣ", "ದ್ವಿಚಕ್ರ ವಾಹನ"]


def full_name(rng: random.Random, lang: str) -> str:
    if lang == "kn":
        return f"{rng.choice(FIRST_NAMES_KN)} {rng.choice(LAST_NAMES_KN)}"
    return f"{rng.choice(FIRST_NAMES_EN)} {rng.choice(LAST_NAMES_EN)}"


def _time_str(rng: random.Random, lo: int = 6, hi: int = 23) -> str:
    h = rng.randint(lo, hi)
    m = rng.choice([0, 15, 30, 45])
    return f"{h:02d}:{m:02d}"


# EN template families keyed by sub-head. {slots} filled by brief_facts().
_EN: dict[str, list[str]] = {
    "Chain Snatching": [
        ("The complainant, {name}, aged {age}, was walking near {area} at about {time} hrs "
         "when two unknown persons on a black {bike} motorcycle approached from behind. The "
         "pillion rider snatched her gold chain weighing approx. {weight} grams and the riders "
         "sped away towards {direction} against one-way traffic. Both wore helmets with visors down."),
        ("At around {time} hrs, {name} ({age}) was returning home along {area}. Two men riding a "
         "black {bike} came from behind; the person seated behind pulled away her gold chain "
         "(about {weight} g) and they escaped towards {direction}. The riders had covered their "
         "faces with helmets."),
    ],
    "House Burglary (Night)": [
        ("The complainant {name} ({age}) reported that on the intervening night, unknown persons "
         "gained entry into the house at {area} through the rear window while the occupants were "
         "away, and decamped with {item} and cash of approx. Rs. {amount}."),
        ("During the night, the house of {name} near {area} was broken into via the rear window. "
         "The family was away; {item} and jewellery worth about Rs. {amount} were found missing "
         "in the morning."),
    ],
    "Cheating / Online Fraud": [
        ("The complainant {name} ({age}) states that through the '{app}' trading app promising "
         "{pct}% weekly returns, the accused induced investment. After small initial payouts, the "
         "account was blocked and Rs. {amount} transferred via UPI could not be recovered."),
        ("{name} was contacted regarding the '{app}' investment application assuring {pct}% weekly "
         "profit. After transferring Rs. {amount} through UPI, the app stopped payouts and the "
         "operator became unreachable."),
    ],
    "Theft": [
        ("The complainant {name} ({age}) reported that {item} was stolen from near {area} at "
         "about {time} hrs by an unknown person."),
    ],
    "Robbery": [
        ("At about {time} hrs near {area}, the complainant {name} ({age}) was threatened by armed "
         "persons who forcibly took {item} and cash of Rs. {amount} before fleeing."),
    ],
    "Murder": [
        ("The complainant {name} reported that the deceased was found with fatal injuries near "
         "{area}. Investigation into the circumstances is under way."),
    ],
}

_KN: dict[str, list[str]] = {
    "Chain Snatching": [
        ("ದೂರುದಾರರಾದ {name}, ವಯಸ್ಸು {age}, {area} ಬಳಿ {time} ಗಂಟೆಗೆ ನಡೆದುಕೊಂಡು ಹೋಗುತ್ತಿದ್ದಾಗ, "
         "ಕಪ್ಪು ಬಣ್ಣದ {bike} ಮೋಟಾರ್ ಸೈಕಲ್‌ನಲ್ಲಿ ಬಂದ ಇಬ್ಬರು ಅಪರಿಚಿತರು ಹಿಂದಿನಿಂದ ಬಂದು, ಹಿಂಬದಿ ಸವಾರನು "
         "ಸುಮಾರು {weight} ಗ್ರಾಂ ತೂಕದ ಚಿನ್ನದ ಸರವನ್ನು ಕಿತ್ತುಕೊಂಡು {direction} ಕಡೆಗೆ ಪರಾರಿಯಾದರು. "
         "ಇಬ್ಬರೂ ಹೆಲ್ಮೆಟ್ ಧರಿಸಿದ್ದರು."),
    ],
    "House Burglary (Night)": [
        ("ದೂರುದಾರರಾದ {name} ({age}) ರವರ ಪ್ರಕಾರ, ರಾತ್ರಿ ವೇಳೆ ಮನೆಯವರು ಹೊರಗಿದ್ದಾಗ ಅಪರಿಚಿತರು {area} "
         "ಬಳಿಯ ಮನೆಯ ಹಿಂಬದಿ ಕಿಟಕಿಯ ಮೂಲಕ ಒಳಗೆ ನುಗ್ಗಿ, {item} ಹಾಗೂ ಸುಮಾರು ರೂ. {amount} ನಗದನ್ನು "
         "ಕದ್ದೊಯ್ದಿದ್ದಾರೆ."),
    ],
    "Cheating / Online Fraud": [
        ("ದೂರುದಾರರಾದ {name} ({age}) ರವರ ಪ್ರಕಾರ, '{app}' ಟ್ರೇಡಿಂಗ್ ಆಪ್ ವಾರಕ್ಕೆ {pct}% ಲಾಭದ "
         "ಆಮಿಷವೊಡ್ಡಿ ಹೂಡಿಕೆ ಮಾಡಿಸಿ, ಆರಂಭದಲ್ಲಿ ಸಣ್ಣ ಪಾವತಿ ಮಾಡಿ ನಂತರ ಖಾತೆ ನಿರ್ಬಂಧಿಸಿ ರೂ. {amount} "
         "ವಂಚಿಸಲಾಗಿದೆ."),
    ],
    "Theft": [
        ("ದೂರುದಾರರಾದ {name} ({age}) ರವರ {item} ವಸ್ತುವನ್ನು {area} ಬಳಿ {time} ಗಂಟೆಗೆ ಅಪರಿಚಿತರು "
         "ಕಳವು ಮಾಡಿದ್ದಾರೆ."),
    ],
    "Robbery": [
        ("{time} ಗಂಟೆಗೆ {area} ಬಳಿ ದೂರುದಾರರಾದ {name} ({age}) ರವರನ್ನು ಬೆದರಿಸಿ, ಆಯುಧಧಾರಿಗಳು {item} "
         "ಹಾಗೂ ರೂ. {amount} ನಗದನ್ನು ಬಲವಂತವಾಗಿ ಕಸಿದುಕೊಂಡು ಪರಾರಿಯಾದರು."),
    ],
    "Murder": [
        ("ದೂರುದಾರರಾದ {name} ರವರ ಪ್ರಕಾರ, {area} ಬಳಿ ಮೃತದೇಹ ಗಾಯಗಳೊಂದಿಗೆ ಪತ್ತೆಯಾಗಿದೆ. "
         "ಪ್ರಕರಣದ ತನಿಖೆ ನಡೆಯುತ್ತಿದೆ."),
    ],
}

_GENERIC_EN = ("The complainant {name} ({age}) lodged a report regarding an incident near {area} "
               "at about {time} hrs. Investigation is in progress.")
_GENERIC_KN = ("ದೂರುದಾರರಾದ {name} ({age}) ರವರು {area} ಬಳಿ {time} ಗಂಟೆಗೆ ನಡೆದ ಘಟನೆ ಕುರಿತು "
               "ದೂರು ದಾಖಲಿಸಿದ್ದಾರೆ. ತನಿಖೆ ಪ್ರಗತಿಯಲ್ಲಿದೆ.")


def brief_facts(subhead: str, lang: str, rng: random.Random, name: str | None = None) -> str:
    """Render a BriefFacts narrative for a sub-head in the given language."""
    if name is None:
        name = full_name(rng, lang)
    if lang == "kn":
        pool = _KN.get(subhead)
        area = rng.choice(_AREAS_KN)
        direction = rng.choice(_DIRECTIONS_KN)
        item = rng.choice(_ITEMS_KN)
        template = rng.choice(pool) if pool else _GENERIC_KN
    else:
        pool = _EN.get(subhead)
        area = rng.choice(_AREAS_EN)
        direction = rng.choice(_DIRECTIONS)
        item = rng.choice(_ITEMS)
        template = rng.choice(pool) if pool else _GENERIC_EN
    return template.format(
        name=name,
        age=rng.randint(19, 68),
        area=area,
        time=_time_str(rng),
        weight=rng.choice([16, 20, 24, 28, 32, 40]),
        bike=rng.choice(_BIKES),
        direction=direction,
        item=item,
        amount=f"{rng.choice([15, 20, 25, 40, 60, 85, 120])},000",
        app=rng.choice(_APPS),
        pct=rng.choice([5, 8, 10, 12, 15]),
    )
