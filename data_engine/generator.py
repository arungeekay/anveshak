"""Seeded synthetic FIR generator + planted-pattern hook.

Produces the transactional tables (CaseMaster and children) plus Employee and the
person-identity tables, merged with the masters, as a dict of DataFrames keyed by
schema table name. Deterministic for a fixed seed.

CrimeNo composite (per ER doc): 1-digit category + 4-digit district + 4-digit unit
+ 4-digit year + 5-digit serial, serial monotonic per (unit, category, year).

Every case (background AND planted) is emitted through `emit_case`, so planted
patterns share the exact same schema path. Planting lives in data_engine/planted.py
and is invoked when generate(plant=True); the planted ground truth is returned when
return_truth=True (used by eval/test_planted.py and eval/linkage_test.py).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import h3
import numpy as np
import pandas as pd

from . import masters as M
from . import narratives as N

START = date(2023, 1, 1)
END = date(2026, 7, 20)
N_ACTIVE_OFFENDERS = 800


def crimeno(cat: int, district_id: int, unit_id: int, year: int, serial: int) -> str:
    return f"{cat}{district_id:04d}{unit_id:04d}{year:04d}{serial:05d}"


def caseno(year: int, serial: int) -> str:
    return f"{year}{serial:05d}"


@dataclass
class Ctx:
    """Mutable generation context shared by background + planted builders."""
    rng: random.Random
    np_rng: np.random.Generator
    officers_by_unit: dict[int, list[int]] = field(default_factory=dict)
    serials: dict[tuple[int, int, int], int] = field(default_factory=dict)
    persons: dict[str, dict] = field(default_factory=dict)  # person_key -> record
    accused_map: list[dict] = field(default_factory=list)
    L: dict[str, list] = field(default_factory=dict)  # table_name -> list[row]
    next_case_id: int = 1
    next_accused_id: int = 1
    next_arrest_id: int = 1
    next_comp_id: int = 1
    next_vic_id: int = 1
    next_person_seq: int = 1

    def serial_for(self, cat: int, district_id: int, unit_id: int, year: int) -> int:
        key = (unit_id, cat, year)
        self.serials[key] = self.serials.get(key, 0) + 1
        return self.serials[key]

    def register_person(self, pk: str, name: str, dob: date, home_h3: str, notes: str = "") -> str:
        self.persons[pk] = {"person_key": pk, "full_name": name, "dob": dob,
                            "home_h3": home_h3, "notes": notes}
        return pk

    def new_person(self, home_district: M.DistrictSpec, lang: str = "en") -> str:
        pk = f"P-1{self.next_person_seq:05d}"
        self.next_person_seq += 1
        lat, lon = point_in(self.np_rng, home_district)
        return self.register_person(pk, N.full_name(self.rng, lang), rand_dob(self.rng),
                                    h3.latlng_to_cell(lat, lon, 8))


def point_in(np_rng: np.random.Generator, d: M.DistrictSpec) -> tuple[float, float]:
    lat = d.lat + float(np_rng.uniform(-d.box, d.box))
    lon = d.lon + float(np_rng.uniform(-d.box, d.box))
    return round(lat, 6), round(lon, 6)


def rand_dob(rng: random.Random) -> date:
    age = rng.randint(19, 65)
    return date(2026 - age, rng.randint(1, 12), rng.randint(1, 28))


def _rand_datetime(rng: random.Random, d0: date, d1: date) -> datetime:
    span = (d1 - d0).days
    day = d0 + timedelta(days=rng.randint(0, max(span, 1)))
    return datetime(day.year, day.month, day.day, rng.randint(0, 23), rng.choice([0, 15, 30, 45]))


def _build_employees(rng: random.Random) -> tuple[pd.DataFrame, dict[int, list[int]]]:
    rows: list[dict] = []
    by_unit: dict[int, list[int]] = {}
    uidx = M.unit_index()
    emp_id = 1
    for d in M.DISTRICTS:
        for uid in uidx[d.district_id]:
            officers = [(4, 1)] + [(5, 2)] * rng.randint(1, 2)
            for rank_id, desig_id in officers:
                rows.append({
                    "EmployeeID": emp_id, "DistrictID": d.district_id, "UnitID": uid,
                    "RankID": rank_id, "DesignationID": desig_id, "KGID": f"KG{emp_id:06d}",
                    "FirstName": N.full_name(rng, "en"), "EmployeeDOB": rand_dob(rng),
                    "GenderID": rng.choice([1, 1, 2]), "BloodGroupID": rng.randint(1, 8),
                    "PhysicallyChallenged": False,
                    "AppointmentDate": date(rng.randint(2005, 2020), rng.randint(1, 12), rng.randint(1, 28)),
                })
                by_unit.setdefault(uid, []).append(emp_id)
                emp_id += 1
    return pd.DataFrame(rows), by_unit


def _empty_lists() -> dict[str, list]:
    return {k: [] for k in ("cases", "complainants", "victims", "accused", "sections",
                            "arrests", "arr_junction", "occ", "cs")}


def emit_case(ctx: Ctx, *, d: M.DistrictSpec, unit_id: int, cat: int, sub: M.SubHeadSpec,
              reg_dt: datetime, status: int, lang: str, accused_pks: list[str],
              comp_name: str | None = None, gravity: int | None = None,
              lat: float | None = None, lon: float | None = None,
              incident_from: datetime | None = None, arrest: bool = False,
              arrest_date: date | None = None, cstype: str | None = None,
              brief: str | None = None, add_victim: bool = False) -> int:
    """Emit one full case (+ children) into ctx.L. Returns the CaseMasterID."""
    rng = ctx.rng
    year = reg_dt.year
    serial = ctx.serial_for(cat, d.district_id, unit_id, year)
    case_id = ctx.next_case_id
    ctx.next_case_id += 1
    if gravity is None:
        gravity = 1 if sub.heinous else 2
    if lat is None:
        lat, lon = point_in(ctx.np_rng, d)
    if comp_name is None:
        comp_name = N.full_name(rng, lang)
    if incident_from is None:
        incident_from = reg_dt - timedelta(hours=rng.randint(1, 72))
    incident_to = incident_from + timedelta(minutes=rng.choice([15, 30, 60, 120]))
    officer = rng.choice(ctx.officers_by_unit[unit_id])
    if brief is None:
        brief = N.brief_facts(sub.name, lang, rng, comp_name)

    ctx.L["cases"].append({
        "CaseMasterID": case_id, "CrimeNo": crimeno(cat, d.district_id, unit_id, year, serial),
        "CaseNo": caseno(year, serial), "CrimeRegisteredDate": reg_dt.date(),
        "PolicePersonID": officer, "PoliceStationID": unit_id, "CaseCategoryID": cat,
        "GravityOffenceID": gravity, "CrimeMajorHeadID": sub.head_id,
        "CrimeMinorHeadID": sub.subhead_id, "CaseStatusID": status, "CourtID": d.district_id,
        "IncidentFromDate": incident_from, "IncidentToDate": incident_to,
        "InfoReceivedPSDate": reg_dt, "latitude": lat, "longitude": lon, "BriefFacts": brief,
    })
    ctx.L["complainants"].append({
        "ComplainantID": ctx.next_comp_id, "CaseMasterID": case_id, "ComplainantName": comp_name,
        "AgeYear": rng.randint(19, 70), "OccupationID": rng.randint(1, 10),
        "ReligionID": rng.randint(1, 5), "CasteID": rng.randint(1, 5), "GenderID": rng.choice([1, 2]),
    })
    ctx.next_comp_id += 1

    if add_victim:
        ctx.L["victims"].append({
            "VictimMasterID": ctx.next_vic_id, "CaseMasterID": case_id,
            "VictimName": N.full_name(rng, lang), "AgeYear": rng.randint(5, 80),
            "GenderID": rng.choice([1, 2]), "VictimPolice": "0",
        })
        ctx.next_vic_id += 1

    accused_ids: list[int] = []
    for i, pk in enumerate(accused_pks):
        am_id = ctx.next_accused_id
        ctx.next_accused_id += 1
        ctx.L["accused"].append({
            "AccusedMasterID": am_id, "CaseMasterID": case_id,
            "AccusedName": ctx.persons[pk]["full_name"], "AgeYear": rng.randint(18, 60),
            "GenderID": rng.choice([1, 1, 2]), "PersonID": f"A{i + 1}",
        })
        ctx.accused_map.append({"AccusedMasterID": am_id, "person_key": pk})
        accused_ids.append(am_id)

    order = 1
    for sec in sub.sections:
        ctx.L["sections"].append({"CaseMasterID": case_id, "ActID": sub.act, "SectionID": sec,
                                  "ActOrderID": 1, "SectionOrderID": order})
        order += 1
    for act, sec in sub.extra:
        ctx.L["sections"].append({"CaseMasterID": case_id, "ActID": act, "SectionID": sec,
                                  "ActOrderID": 2, "SectionOrderID": order})
        order += 1

    if accused_ids and arrest:
        adate = arrest_date or (reg_dt.date() + timedelta(days=rng.randint(3, 120)))
        for am_id in accused_ids:
            aid = ctx.next_arrest_id
            ctx.next_arrest_id += 1
            ctx.L["arrests"].append({
                "ArrestSurrenderID": aid, "CaseMasterID": case_id,
                "ArrestSurrenderTypeID": rng.choice([1, 2]), "ArrestSurrenderDate": adate,
                "ArrestSurrenderStateId": 29, "ArrestSurrenderDistrictId": d.district_id,
                "PoliceStationID": unit_id, "IOID": officer, "CourtID": d.district_id,
                "AccusedMasterID": am_id, "IsAccused": True, "IsComplainantAccused": False,
            })
            ctx.L["arr_junction"].append({"ArrestSurrenderID": aid, "AccusedMasterID": am_id})

    eff_cstype = cstype or ("A" if status == 2 else (rng.choice(["B", "C"]) if status == 3 else None))
    if eff_cstype:
        ctx.L["cs"].append({"CSID": case_id, "CaseMasterID": case_id,
                            "csdate": reg_dt + timedelta(days=rng.randint(30, 150)),
                            "cstype": eff_cstype, "PolicePersonID": officer})

    ctx.L["occ"].append({"CaseMasterID": case_id, "OccurrenceFrom": incident_from,
                         "OccurrenceTo": incident_to,
                         "PlaceOfOccurrence": f"Near a public place in {d.name}"})
    return case_id


_CAT_CODES = [1, 3, 4, 8]
_CAT_WEIGHTS = [0.88, 0.06, 0.03, 0.03]


def _assemble(ctx: Ctx, tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    L = ctx.L
    tables["CaseMaster"] = pd.DataFrame(L["cases"])
    tables["ComplainantDetails"] = pd.DataFrame(L["complainants"])
    tables["Victim"] = pd.DataFrame(L["victims"])
    tables["Accused"] = pd.DataFrame(L["accused"])
    tables["ActSectionAssociation"] = pd.DataFrame(L["sections"])
    tables["ArrestSurrender"] = pd.DataFrame(L["arrests"])
    tables["inv_arrestsurrenderaccused"] = pd.DataFrame(L["arr_junction"])
    tables["Inv_OccuranceTime"] = pd.DataFrame(L["occ"])
    tables["ChargesheetDetails"] = pd.DataFrame(L["cs"])
    tables["PersonRegistry"] = pd.DataFrame(list(ctx.persons.values()))
    tables["AccusedPersonMap"] = pd.DataFrame(ctx.accused_map)
    tables["CaseMOVector"] = pd.DataFrame(columns=["CaseMasterID", "embedding", "mo_features", "model"])
    tables["AuditLog"] = pd.DataFrame(columns=["audit_id", "ts", "user_id", "role", "action", "detail"])
    return tables


def generate(seed: int = 42, n_cases: int = 15000, start: date = START, end: date = END,
             plant: bool = False, return_truth: bool = False):
    """Generate the dataset. Returns tables dict, or (tables, truth) if return_truth."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    tables = M.build_masters()
    employees, officers_by_unit = _build_employees(rng)
    tables["Employee"] = employees

    ctx = Ctx(rng=rng, np_rng=np_rng, officers_by_unit=officers_by_unit, L=_empty_lists())

    uidx = M.unit_index()
    dist_weights = np.array([d.weight for d in M.DISTRICTS], dtype=float)
    dist_weights /= dist_weights.sum()

    active: list[str] = []
    for _ in range(N_ACTIVE_OFFENDERS):
        home = rng.choices(M.DISTRICTS, weights=list(dist_weights))[0]
        active.append(ctx.new_person(home, "en"))

    for _ in range(n_cases):
        d = rng.choices(M.DISTRICTS, weights=list(dist_weights))[0]
        unit_id = rng.choice(uidx[d.district_id])
        cat = rng.choices(_CAT_CODES, weights=_CAT_WEIGHTS)[0]
        sub = rng.choices(M.SUBHEADS, weights=[s.weight for s in M.SUBHEADS])[0]
        reg_dt = _rand_datetime(rng, start, end)
        status = rng.choices([1, 2, 3], weights=[0.62, 0.23, 0.15])[0]
        lang = "kn" if rng.random() < 0.30 else "en"

        is_body = sub.head_id == 1
        p_named = 0.70 if is_body else 0.38
        accused_pks: list[str] = []
        if rng.random() < p_named:
            for _ in range(rng.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]):
                accused_pks.append(rng.choice(active) if (active and rng.random() < 0.6)
                                   else ctx.new_person(d, lang))
        arrest = bool(accused_pks) and (status == 2 or rng.random() < (0.70 if is_body else 0.35))
        add_victim = sub.head_id in (1, 4) or rng.random() < 0.25

        emit_case(ctx, d=d, unit_id=unit_id, cat=cat, sub=sub, reg_dt=reg_dt, status=status,
                  lang=lang, accused_pks=accused_pks, arrest=arrest, add_victim=add_victim)

    truth: dict = {}
    if plant:
        from . import planted  # lazy import to avoid a cycle
        truth = planted.plant_all(ctx, tables)

    _assemble(ctx, tables)
    if return_truth:
        return tables, truth
    return tables
