"""Master reference data for ANVESHAK's synthetic KSP crime database.

All IDs are stable and deterministic (no randomness here) so CrimeNo composites and
foreign keys are reproducible. Geography carries approximate district centres and a
bounding box so generated cases fall inside plausible Karnataka coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# ---------------------------------------------------------------------------
# Districts (31), id, name, centre lat/lon, box half-width (deg), pop weight,
# urban %, literacy %, density/km2. Demo-critical names spelled to match
# demo_story.md exactly (Bengaluru City, Tumakuru, Mandya, Mysuru, ...).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DistrictSpec:
    district_id: int
    name: str
    lat: float
    lon: float
    box: float
    weight: float
    urban_pct: float
    literacy_pct: float
    density: int


DISTRICTS: list[DistrictSpec] = [
    DistrictSpec(1, "Bengaluru City", 12.97, 77.59, 0.18, 26.0, 91.0, 88.5, 4381),
    DistrictSpec(2, "Bengaluru Rural", 13.23, 77.58, 0.20, 3.0, 45.0, 77.9, 431),
    DistrictSpec(3, "Ramanagara", 12.72, 77.28, 0.18, 3.2, 35.0, 69.2, 309),
    DistrictSpec(4, "Tumakuru", 13.34, 77.10, 0.35, 5.5, 30.0, 75.1, 253),
    DistrictSpec(5, "Kolar", 13.14, 78.13, 0.22, 3.0, 32.0, 74.4, 386),
    DistrictSpec(6, "Chikkaballapura", 13.43, 77.73, 0.22, 2.6, 26.0, 70.1, 297),
    DistrictSpec(7, "Mandya", 12.52, 76.90, 0.25, 4.2, 16.0, 70.4, 365),
    DistrictSpec(8, "Mysuru", 12.30, 76.64, 0.30, 6.5, 41.0, 72.8, 476),
    DistrictSpec(9, "Chamarajanagara", 11.92, 76.94, 0.28, 2.2, 17.0, 61.4, 189),
    DistrictSpec(10, "Hassan", 13.00, 76.10, 0.30, 3.4, 21.0, 76.1, 262),
    DistrictSpec(11, "Kodagu", 12.42, 75.74, 0.25, 1.4, 14.0, 82.6, 135),
    DistrictSpec(12, "Dakshina Kannada", 12.87, 74.88, 0.28, 4.6, 48.0, 88.6, 457),
    DistrictSpec(13, "Udupi", 13.34, 74.75, 0.30, 3.0, 30.0, 86.2, 329),
    DistrictSpec(14, "Chikkamagaluru", 13.32, 75.77, 0.35, 2.2, 18.0, 79.3, 158),
    DistrictSpec(15, "Shivamogga", 13.93, 75.57, 0.32, 3.6, 35.0, 80.5, 207),
    DistrictSpec(16, "Davanagere", 14.47, 75.92, 0.28, 3.4, 32.0, 75.7, 329),
    DistrictSpec(17, "Chitradurga", 14.23, 76.40, 0.35, 2.8, 20.0, 73.7, 197),
    DistrictSpec(18, "Ballari", 15.14, 76.92, 0.35, 4.0, 38.0, 67.4, 300),
    DistrictSpec(19, "Vijayanagara", 15.34, 76.46, 0.30, 2.6, 25.0, 68.0, 240),
    DistrictSpec(20, "Koppala", 15.35, 76.15, 0.30, 2.2, 17.0, 68.1, 250),
    DistrictSpec(21, "Raichur", 16.21, 77.36, 0.35, 2.8, 23.0, 59.6, 228),
    DistrictSpec(22, "Kalaburagi", 17.33, 76.83, 0.40, 3.6, 28.0, 64.9, 233),
    DistrictSpec(23, "Yadgir", 16.77, 77.14, 0.30, 1.8, 17.0, 51.8, 224),
    DistrictSpec(24, "Bidar", 17.91, 77.52, 0.32, 2.4, 24.0, 70.5, 312),
    DistrictSpec(25, "Vijayapura", 16.83, 75.71, 0.40, 3.0, 23.0, 67.0, 207),
    DistrictSpec(26, "Bagalkote", 16.19, 75.70, 0.32, 2.6, 27.0, 68.8, 288),
    DistrictSpec(27, "Belagavi", 15.85, 74.50, 0.45, 6.0, 25.0, 73.5, 356),
    DistrictSpec(28, "Dharwad", 15.46, 75.01, 0.28, 3.6, 57.0, 80.0, 434),
    DistrictSpec(29, "Gadag", 15.43, 75.63, 0.25, 1.8, 35.0, 75.0, 230),
    DistrictSpec(30, "Haveri", 14.80, 75.40, 0.28, 2.2, 20.0, 77.6, 254),
    DistrictSpec(31, "Uttara Kannada", 14.79, 74.69, 0.45, 2.4, 30.0, 84.1, 140),
]

DISTRICT_BY_NAME: dict[str, DistrictSpec] = {d.name: d for d in DISTRICTS}

# Curated real-ish station names for demo districts; generic elsewhere.
_CURATED_STATIONS: dict[str, list[str]] = {
    "Bengaluru City": [
        "Jayanagar", "Basavanagudi", "J P Nagar", "BTM Layout",
        "Whitefield", "Indiranagar", "Koramangala", "Electronic City",
    ],
    "Tumakuru": [
        "Tumakuru Town", "Tumakuru Rural", "Kyathsandra", "Gubbi",
        "Tiptur", "Sira", "Madhugiri", "Pavagada",
    ],
    "Mandya": [
        "Mandya East", "Mandya West", "Maddur", "Malavalli",
        "Srirangapatna", "Pandavapura", "Nagamangala", "K R Pet",
    ],
    "Mysuru": [
        "Devaraja", "Lashkar", "Krishnaraja", "Nazarbad",
        "V V Puram", "Kuvempunagar", "Vijayanagar Mysuru", "Metagalli",
    ],
    "Ramanagara": [
        "Ramanagara Town", "Channapatna", "Kanakapura", "Magadi",
        "Bidadi", "Harohalli", "Sathanur", "Kudur",
    ],
}
_GENERIC_SUFFIXES = [
    "Town", "Rural", "Market", "Extension", "North", "South", "Industrial", "Lake"
]
STATIONS_PER_DISTRICT = 8


def _station_names(d: DistrictSpec) -> list[str]:
    if d.name in _CURATED_STATIONS:
        base = _CURATED_STATIONS[d.name]
    else:
        base = [f"{d.name} {suf}" for suf in _GENERIC_SUFFIXES]
    return [f"{n} PS" for n in base[:STATIONS_PER_DISTRICT]]


# ---------------------------------------------------------------------------
# Legal masters
# ---------------------------------------------------------------------------
ACTS = [
    ("BNS", "Bharatiya Nyaya Sanhita, 2023", "BNS"),
    ("IPC", "Indian Penal Code, 1860 (legacy)", "IPC"),
    ("NDPS", "Narcotic Drugs and Psychotropic Substances Act, 1985", "NDPS"),
    ("POCSO", "Protection of Children from Sexual Offences Act, 2012", "POCSO"),
    ("ITAct", "Information Technology Act, 2000", "IT Act"),
    ("Arms", "Arms Act, 1959", "Arms Act"),
]

# (ActCode, SectionCode, description)
SECTIONS = [
    ("BNS", "103", "Punishment for murder"),
    ("BNS", "109", "Attempt to murder"),
    ("BNS", "115(2)", "Voluntarily causing hurt"),
    ("BNS", "137(2)", "Kidnapping"),
    ("BNS", "3(5)", "Acts done by several persons in furtherance of common intention"),
    ("BNS", "303(2)", "Theft"),
    ("BNS", "304(2)", "Snatching"),
    ("BNS", "305", "Theft in dwelling house / of property in possession"),
    ("BNS", "309", "Robbery"),
    ("BNS", "318(4)", "Cheating and dishonestly inducing delivery of property"),
    ("BNS", "329(3)", "Criminal trespass / house-trespass"),
    ("BNS", "331(4)", "House-trespass / house-breaking by night"),
    ("BNS", "64", "Punishment for rape"),
    ("BNS", "85", "Cruelty by husband or relatives (dowry harassment)"),
    ("BNS", "191(2)", "Rioting"),
    ("IPC", "302", "Murder (legacy)"),
    ("IPC", "379", "Theft (legacy)"),
    ("IPC", "380", "Theft in dwelling (legacy)"),
    ("IPC", "392", "Robbery (legacy)"),
    ("IPC", "420", "Cheating (legacy)"),
    ("IPC", "457", "House-breaking by night (legacy)"),
    ("NDPS", "8", "Prohibition of certain operations"),
    ("NDPS", "20", "Contravention re cannabis"),
    ("NDPS", "22", "Contravention re psychotropic substances"),
    ("POCSO", "4", "Penetrative sexual assault"),
    ("POCSO", "6", "Aggravated penetrative sexual assault"),
    ("ITAct", "66C", "Identity theft"),
    ("ITAct", "66D", "Cheating by personation using computer resource"),
    ("Arms", "25", "Punishment for certain offences"),
]

# Crime heads (groups)
CRIME_HEADS = [
    (1, "Crimes Against Body"),
    (2, "Property Crimes"),
    (3, "Economic Offences"),
    (4, "Crimes Against Women & Children"),
    (5, "Other IPC / Special Laws"),
]


@dataclass(frozen=True)
class SubHeadSpec:
    subhead_id: int
    head_id: int
    name: str
    heinous: bool
    weight: float
    act: str
    sections: tuple[str, ...]
    extra: tuple[tuple[str, str], ...] = ()  # (act, section) extras


# weight = relative frequency in background data
SUBHEADS: list[SubHeadSpec] = [
    SubHeadSpec(1, 1, "Murder", True, 2.0, "BNS", ("103",)),
    SubHeadSpec(2, 1, "Attempt to Murder", True, 2.5, "BNS", ("109",)),
    SubHeadSpec(3, 1, "Assault", False, 9.0, "BNS", ("115(2)",)),
    SubHeadSpec(4, 1, "Hurt", False, 10.0, "BNS", ("115(2)",)),
    SubHeadSpec(5, 1, "Kidnapping", True, 2.0, "BNS", ("137(2)",)),
    SubHeadSpec(6, 2, "Robbery", True, 5.0, "BNS", ("309", "3(5)")),
    SubHeadSpec(7, 2, "Chain Snatching", False, 6.0, "BNS", ("304(2)", "3(5)")),
    SubHeadSpec(8, 2, "Theft", False, 18.0, "BNS", ("303(2)",)),
    SubHeadSpec(9, 2, "House Burglary (Night)", False, 8.0, "BNS", ("331(4)", "305")),
    SubHeadSpec(10, 2, "Criminal Trespass", False, 4.0, "BNS", ("329(3)",)),
    SubHeadSpec(
        11, 3, "Cheating / Online Fraud", False, 10.0, "BNS", ("318(4)",),
        (("ITAct", "66D"),),
    ),
    SubHeadSpec(12, 4, "Rape", True, 1.2, "BNS", ("64",)),
    SubHeadSpec(13, 4, "Dowry Harassment", False, 3.0, "BNS", ("85",)),
    SubHeadSpec(14, 5, "Rioting", False, 3.0, "BNS", ("191(2)",)),
    SubHeadSpec(15, 5, "NDPS", False, 3.0, "NDPS", ("20",)),
    SubHeadSpec(16, 5, "Missing Person", False, 3.0, "BNS", ("137(2)",)),
]
SUBHEAD_BY_NAME: dict[str, SubHeadSpec] = {s.name: s for s in SUBHEADS}

# Case categories, ID equals the 1-digit CrimeNo category code (FIR=1, UDR=3,
# PAR=4, ZeroFIR=8) so the composite decodes directly.
CASE_CATEGORIES = [(1, "FIR"), (3, "UDR"), (4, "PAR"), (8, "Zero FIR")]
GRAVITY = [(1, "Heinous"), (2, "Non-Heinous")]
CASE_STATUSES = [(1, "Under Investigation"), (2, "Charge Sheeted"), (3, "Closed")]
OCCUPATIONS = [
    (1, "Business"), (2, "Student"), (3, "Homemaker"), (4, "Labourer"),
    (5, "Private Employee"), (6, "Government Employee"), (7, "Agriculture"),
    (8, "Unemployed"), (9, "Retired"), (10, "Other"),
]
RELIGIONS = [(1, "Hindu"), (2, "Muslim"), (3, "Christian"), (4, "Jain"), (5, "Other")]
CASTES = [(1, "General"), (2, "OBC"), (3, "SC"), (4, "ST"), (5, "Other")]
RANKS = [
    (1, "Director General", 1), (2, "Superintendent of Police", 2),
    (3, "Deputy Superintendent", 3), (4, "Inspector", 4),
    (5, "Sub-Inspector", 5), (6, "Assistant Sub-Inspector", 6),
    (7, "Head Constable", 7), (8, "Constable", 8),
]
DESIGNATIONS = [
    (1, "Station House Officer", 1), (2, "Investigating Officer", 2),
    (3, "Superintendent of Police", 3), (4, "Circle Inspector", 4),
    (5, "Writer", 5),
]


def build_masters() -> dict[str, pd.DataFrame]:
    """Return every master table as a DataFrame keyed by schema table name."""
    tables: dict[str, pd.DataFrame] = {}

    tables["State"] = pd.DataFrame(
        [{"StateID": 29, "StateName": "Karnataka", "NationalityID": 1, "Active": True}]
    )

    tables["District"] = pd.DataFrame(
        [{"DistrictID": d.district_id, "DistrictName": d.name, "StateID": 29, "Active": True}
         for d in DISTRICTS]
    )

    tables["UnitType"] = pd.DataFrame([
        {"UnitTypeID": 1, "UnitTypeName": "Police Station", "CityDistState": "District",
         "Hierarchy": 3, "Active": True},
        {"UnitTypeID": 2, "UnitTypeName": "Circle Office", "CityDistState": "District",
         "Hierarchy": 2, "Active": True},
    ])

    # Units (police stations)
    units = []
    unit_id = 1
    for d in DISTRICTS:
        for name in _station_names(d):
            units.append({
                "UnitID": unit_id, "UnitName": name, "TypeID": 1, "ParentUnit": None,
                "NationalityID": 1, "StateID": 29, "DistrictID": d.district_id,
                "Active": True,
            })
            unit_id += 1
    tables["Unit"] = pd.DataFrame(units)

    tables["Rank"] = pd.DataFrame(
        [{"RankID": r[0], "RankName": r[1], "Hierarchy": r[2], "Active": True} for r in RANKS]
    )
    tables["Designation"] = pd.DataFrame(
        [{"DesignationID": x[0], "DesignationName": x[1], "Active": True, "SortOrder": x[2]}
         for x in DESIGNATIONS]
    )

    tables["Court"] = pd.DataFrame(
        [{"CourtID": d.district_id, "CourtName": f"{d.name} District & Sessions Court",
          "DistrictID": d.district_id, "StateID": 29, "Active": True} for d in DISTRICTS]
    )

    tables["Act"] = pd.DataFrame(
        [{"ActCode": a[0], "ActDescription": a[1], "ShortName": a[2], "Active": True}
         for a in ACTS]
    )
    tables["Section"] = pd.DataFrame(
        [{"ActCode": s[0], "SectionCode": s[1], "SectionDescription": s[2], "Active": True}
         for s in SECTIONS]
    )
    tables["CrimeHead"] = pd.DataFrame(
        [{"CrimeHeadID": h[0], "CrimeGroupName": h[1], "Active": True} for h in CRIME_HEADS]
    )
    tables["CrimeSubHead"] = pd.DataFrame(
        [{"CrimeSubHeadID": s.subhead_id, "CrimeHeadID": s.head_id,
          "CrimeHeadName": s.name, "SeqID": s.subhead_id} for s in SUBHEADS]
    )
    che = []
    for s in SUBHEADS:
        for sec in s.sections:
            che.append({"CrimeHeadID": s.head_id, "ActCode": s.act, "SectionCode": sec})
        for act, sec in s.extra:
            che.append({"CrimeHeadID": s.head_id, "ActCode": act, "SectionCode": sec})
    tables["CrimeHeadActSection"] = pd.DataFrame(che)

    tables["CaseCategory"] = pd.DataFrame(
        [{"CaseCategoryID": c[0], "LookupValue": c[1]} for c in CASE_CATEGORIES]
    )
    tables["GravityOffence"] = pd.DataFrame(
        [{"GravityOffenceID": g[0], "LookupValue": g[1]} for g in GRAVITY]
    )
    tables["CaseStatusMaster"] = pd.DataFrame(
        [{"CaseStatusID": s[0], "CaseStatusName": s[1]} for s in CASE_STATUSES]
    )
    tables["OccupationMaster"] = pd.DataFrame(
        [{"OccupationID": o[0], "OccupationName": o[1]} for o in OCCUPATIONS]
    )
    tables["ReligionMaster"] = pd.DataFrame(
        [{"ReligionID": r[0], "ReligionName": r[1]} for r in RELIGIONS]
    )
    tables["CasteMaster"] = pd.DataFrame(
        [{"caste_master_id": c[0], "caste_master_name": c[1]} for c in CASTES]
    )
    tables["DistrictIndicators"] = pd.DataFrame(
        [{"DistrictID": d.district_id, "population": int(d.weight * 250_000),
          "urban_pct": d.urban_pct, "literacy_pct": d.literacy_pct,
          "density_per_km2": d.density} for d in DISTRICTS]
    )
    return tables


def unit_index() -> dict[int, list[int]]:
    """district_id -> ordered list of UnitIDs (stations)."""
    idx: dict[int, list[int]] = {}
    unit_id = 1
    for d in DISTRICTS:
        ids = []
        for _ in _station_names(d):
            ids.append(unit_id)
            unit_id += 1
        idx[d.district_id] = ids
    return idx
