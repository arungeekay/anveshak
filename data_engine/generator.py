"""Seeded synthetic FIR generator (background data; planted patterns added in T04).

Produces the transactional tables (CaseMaster and children) plus Employee and the
person-identity tables, merged with the masters, as a dict of DataFrames keyed by
schema table name. Deterministic for a fixed seed.

CrimeNo composite (per ER doc): 1-digit category + 4-digit district + 4-digit unit
+ 4-digit year + 5-digit serial, serial monotonic per (unit, category, year).
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
    serials: dict[tuple[int, int, int], int] = field(default_factory=dict)
    persons: dict[str, dict] = field(default_factory=dict)  # person_key -> record
    accused_map: list[dict] = field(default_factory=list)   # AccusedMasterID -> person_key
    next_case_id: int = 1
    next_accused_id: int = 1
    next_arrest_id: int = 1
    next_person_seq: int = 1

    def serial_for(self, cat: int, district_id: int, unit_id: int, year: int) -> int:
        key = (unit_id, cat, year)
        self.serials[key] = self.serials.get(key, 0) + 1
        return self.serials[key]

    def new_person(self, home_district: M.DistrictSpec, lang: str = "en") -> str:
        pk = f"P-1{self.next_person_seq:05d}"
        self.next_person_seq += 1
        lat, lon = _point_in(self.np_rng, home_district)
        self.persons[pk] = {
            "person_key": pk,
            "full_name": N.full_name(self.rng, lang),
            "dob": _rand_dob(self.rng),
            "home_h3": h3.latlng_to_cell(lat, lon, 8),
            "notes": "",
        }
        return pk


def _point_in(np_rng: np.random.Generator, d: M.DistrictSpec) -> tuple[float, float]:
    lat = d.lat + float(np_rng.uniform(-d.box, d.box))
    lon = d.lon + float(np_rng.uniform(-d.box, d.box))
    return round(lat, 6), round(lon, 6)


def _rand_dob(rng: random.Random) -> date:
    age = rng.randint(19, 65)
    y = 2026 - age
    return date(y, rng.randint(1, 12), rng.randint(1, 28))


def _rand_datetime(rng: random.Random, d0: date, d1: date) -> datetime:
    span = (d1 - d0).days
    day = d0 + timedelta(days=rng.randint(0, max(span, 1)))
    return datetime(day.year, day.month, day.day, rng.randint(0, 23), rng.choice([0, 15, 30, 45]))


def _build_employees(rng: random.Random) -> tuple[pd.DataFrame, dict[int, list[int]]]:
    """~600 employees: each station gets 1 SHO + 1-2 IOs."""
    rows = []
    by_unit: dict[int, list[int]] = {}
    uidx = M.unit_index()
    emp_id = 1
    for d in M.DISTRICTS:
        for uid in uidx[d.district_id]:
            officers = [(4, 1)] + [(5, 2)] * rng.randint(1, 2)  # (RankID, DesignationID)
            for rank_id, desig_id in officers:
                rows.append({
                    "EmployeeID": emp_id, "DistrictID": d.district_id, "UnitID": uid,
                    "RankID": rank_id, "DesignationID": desig_id,
                    "KGID": f"KG{emp_id:06d}", "FirstName": N.full_name(rng, "en"),
                    "EmployeeDOB": _rand_dob(rng),
                    "GenderID": rng.choice([1, 1, 2]),
                    "BloodGroupID": rng.randint(1, 8), "PhysicallyChallenged": False,
                    "AppointmentDate": date(rng.randint(2005, 2020), rng.randint(1, 12), rng.randint(1, 28)),
                })
                by_unit.setdefault(uid, []).append(emp_id)
                emp_id += 1
    return pd.DataFrame(rows), by_unit


# Sampling weights
_CAT_CODES = [1, 3, 4, 8]
_CAT_WEIGHTS = [0.88, 0.06, 0.03, 0.03]


def generate(seed: int = 42, n_cases: int = 15000,
             start: date = START, end: date = END) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    ctx = Ctx(rng=rng, np_rng=np_rng)

    tables = M.build_masters()
    employees, officers_by_unit = _build_employees(rng)
    tables["Employee"] = employees

    uidx = M.unit_index()
    dist_weights = np.array([d.weight for d in M.DISTRICTS], dtype=float)
    dist_weights /= dist_weights.sum()

    # Pre-create a pool of active offenders (reused -> repeat offenders + co-accusal).
    active: list[str] = []
    for _ in range(N_ACTIVE_OFFENDERS):
        home = rng.choices(M.DISTRICTS, weights=list(dist_weights))[0]
        active.append(ctx.new_person(home, "en"))

    cases, complainants, victims, accused_rows = [], [], [], []
    sections, arrests, arr_junction, occ_rows, cs_rows = [], [], [], [], []
    comp_id = vic_id = 1

    for _ in range(n_cases):
        d = rng.choices(M.DISTRICTS, weights=list(dist_weights))[0]
        unit_id = rng.choice(uidx[d.district_id])
        cat = rng.choices(_CAT_CODES, weights=_CAT_WEIGHTS)[0]
        sub = rng.choices(M.SUBHEADS, weights=[s.weight for s in M.SUBHEADS])[0]
        reg_dt = _rand_datetime(rng, start, end)
        reg_date = reg_dt.date()
        year = reg_date.year
        serial = ctx.serial_for(cat, d.district_id, unit_id, year)
        case_id = ctx.next_case_id
        ctx.next_case_id += 1

        gravity = 1 if sub.heinous else 2
        status = rng.choices([1, 2, 3], weights=[0.62, 0.23, 0.15])[0]
        lat, lon = _point_in(np_rng, d)
        lang = "kn" if rng.random() < 0.30 else "en"
        comp_name = N.full_name(rng, lang)
        incident_from = reg_dt - timedelta(hours=rng.randint(1, 72))
        incident_to = incident_from + timedelta(minutes=rng.choice([15, 30, 60, 120]))
        officer = rng.choice(officers_by_unit[unit_id])

        cases.append({
            "CaseMasterID": case_id,
            "CrimeNo": crimeno(cat, d.district_id, unit_id, year, serial),
            "CaseNo": caseno(year, serial),
            "CrimeRegisteredDate": reg_date,
            "PolicePersonID": officer, "PoliceStationID": unit_id,
            "CaseCategoryID": cat, "GravityOffenceID": gravity,
            "CrimeMajorHeadID": sub.head_id, "CrimeMinorHeadID": sub.subhead_id,
            "CaseStatusID": status, "CourtID": d.district_id,
            "IncidentFromDate": incident_from, "IncidentToDate": incident_to,
            "InfoReceivedPSDate": reg_dt, "latitude": lat, "longitude": lon,
            "BriefFacts": N.brief_facts(sub.name, lang, rng, comp_name),
        })

        complainants.append({
            "ComplainantID": comp_id, "CaseMasterID": case_id, "ComplainantName": comp_name,
            "AgeYear": rng.randint(19, 70), "OccupationID": rng.randint(1, 10),
            "ReligionID": rng.randint(1, 5), "CasteID": rng.randint(1, 5),
            "GenderID": rng.choice([1, 2]),
        })
        comp_id += 1

        # Victims (body/women crimes usually have a distinct victim)
        if sub.head_id in (1, 4) or rng.random() < 0.25:
            victims.append({
                "VictimMasterID": vic_id, "CaseMasterID": case_id,
                "VictimName": N.full_name(rng, lang), "AgeYear": rng.randint(5, 80),
                "GenderID": rng.choice([1, 2]), "VictimPolice": "0",
            })
            vic_id += 1

        # Accused + person identity
        is_body = sub.head_id == 1
        p_named = 0.70 if is_body else 0.38
        n_acc = 0
        if rng.random() < p_named:
            n_acc = rng.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        case_accused_ids: list[int] = []
        for i in range(n_acc):
            if active and rng.random() < 0.6:
                pk = rng.choice(active)
            else:
                pk = ctx.new_person(d, lang)
            am_id = ctx.next_accused_id
            ctx.next_accused_id += 1
            accused_rows.append({
                "AccusedMasterID": am_id, "CaseMasterID": case_id,
                "AccusedName": ctx.persons[pk]["full_name"], "AgeYear": rng.randint(18, 60),
                "GenderID": rng.choice([1, 1, 2]), "PersonID": f"A{i + 1}",
            })
            ctx.accused_map.append({"AccusedMasterID": am_id, "person_key": pk})
            case_accused_ids.append(am_id)

        # Act/Section associations
        order = 1
        for sec in sub.sections:
            sections.append({"CaseMasterID": case_id, "ActID": sub.act, "SectionID": sec,
                             "ActOrderID": 1, "SectionOrderID": order})
            order += 1
        for act, sec in sub.extra:
            sections.append({"CaseMasterID": case_id, "ActID": act, "SectionID": sec,
                             "ActOrderID": 2, "SectionOrderID": order})
            order += 1

        # Arrests (only if named accused). Property ~35%, body ~70%.
        arrest_prob = 0.70 if is_body else 0.35
        if case_accused_ids and (status == 2 or rng.random() < arrest_prob):
            arr_date = reg_date + timedelta(days=rng.randint(3, 120))
            for am_id in case_accused_ids:
                aid = ctx.next_arrest_id
                ctx.next_arrest_id += 1
                arrests.append({
                    "ArrestSurrenderID": aid, "CaseMasterID": case_id,
                    "ArrestSurrenderTypeID": rng.choice([1, 2]), "ArrestSurrenderDate": arr_date,
                    "ArrestSurrenderStateId": 29, "ArrestSurrenderDistrictId": d.district_id,
                    "PoliceStationID": unit_id, "IOID": officer, "CourtID": d.district_id,
                    "AccusedMasterID": am_id, "IsAccused": True, "IsComplainantAccused": False,
                })
                arr_junction.append({"ArrestSurrenderID": aid, "AccusedMasterID": am_id})

        # Chargesheet / final report
        if status == 2:
            cs_rows.append({"CSID": case_id, "CaseMasterID": case_id,
                            "csdate": reg_dt + timedelta(days=rng.randint(30, 150)),
                            "cstype": "A", "PolicePersonID": officer})
        elif status == 3:
            cs_rows.append({"CSID": case_id, "CaseMasterID": case_id,
                            "csdate": reg_dt + timedelta(days=rng.randint(30, 200)),
                            "cstype": rng.choice(["B", "C"]), "PolicePersonID": officer})

        occ_rows.append({"CaseMasterID": case_id,
                         "OccurrenceFrom": incident_from, "OccurrenceTo": incident_to,
                         "PlaceOfOccurrence": f"Near a public place in {d.name}"})

    tables["CaseMaster"] = pd.DataFrame(cases)
    tables["ComplainantDetails"] = pd.DataFrame(complainants)
    tables["Victim"] = pd.DataFrame(victims)
    tables["Accused"] = pd.DataFrame(accused_rows)
    tables["ActSectionAssociation"] = pd.DataFrame(sections)
    tables["ArrestSurrender"] = pd.DataFrame(arrests)
    tables["inv_arrestsurrenderaccused"] = pd.DataFrame(arr_junction)
    tables["Inv_OccuranceTime"] = pd.DataFrame(occ_rows)
    tables["ChargesheetDetails"] = pd.DataFrame(cs_rows)
    tables["PersonRegistry"] = pd.DataFrame(list(ctx.persons.values()))
    tables["AccusedPersonMap"] = pd.DataFrame(ctx.accused_map)
    # Empty aux tables filled later (T05 embeddings).
    tables["CaseMOVector"] = pd.DataFrame(
        columns=["CaseMasterID", "embedding", "mo_features", "model"]
    )
    tables["AuditLog"] = pd.DataFrame(
        columns=["audit_id", "ts", "user_id", "role", "action", "detail"]
    )
    return tables
