"""Plant SP-1..SP-4 exactly per demo_story.md, driven by planted/*.yaml.

Called from generator.generate(plant=True) AFTER background generation, so planted
cases share id/serial counters and the same emit_case schema path. Returns a
ground-truth dict consumed by eval/test_planted.py and eval/linkage_test.py.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import h3
import yaml

from . import masters as M
from . import narratives as N
from .generator import Ctx, emit_case

PLANTED_DIR = Path(__file__).parent / "planted"

# Distinctive SP-1/SH-07 serial MO (varied slots, invariant signature) — kept separate
# from the generic background chain-snatching narratives so linkage can isolate it.
_SP1_EN = (
    "The complainant, {name}, aged {age}, was walking alone near {area} at about {time} hrs "
    "when two men on a black motorcycle approached from behind. The pillion rider snatched her "
    "gold chain weighing approx. {weight} grams and they sped away against one-way traffic. "
    "Both wore full-face helmets with visors down."
)
_SP1_KN = (
    "ದೂರುದಾರರಾದ {name}, ವಯಸ್ಸು {age}, {area} ಬಳಿ {time} ಗಂಟೆಗೆ ಒಬ್ಬಂಟಿಯಾಗಿ ನಡೆದುಕೊಂಡು "
    "ಹೋಗುತ್ತಿದ್ದಾಗ, ಕಪ್ಪು ಬಣ್ಣದ ಮೋಟಾರ್ ಸೈಕಲ್‌ನಲ್ಲಿ ಬಂದ ಇಬ್ಬರು ವ್ಯಕ್ತಿಗಳಲ್ಲಿ ಹಿಂಬದಿ ಸವಾರನು ಸುಮಾರು "
    "{weight} ಗ್ರಾಂ ತೂಕದ ಚಿನ್ನದ ಸರವನ್ನು ಕಿತ್ತುಕೊಂಡು ಏಕಮುಖ ಸಂಚಾರದ ವಿರುದ್ಧ ಪರಾರಿಯಾದರು. "
    "ಇಬ್ಬರೂ ವೈಸರ್ ಇಳಿಸಿದ ಹೆಲ್ಮೆಟ್ ಧರಿಸಿದ್ದರು."
)


def _sp1_brief(ctx: Ctx, lang: str, name: str) -> str:
    tmpl = _SP1_KN if lang == "kn" else _SP1_EN
    return tmpl.format(name=name, age=ctx.rng.randint(22, 62),
                       area=(ctx.rng.choice(N._AREAS_KN) if lang == "kn" else ctx.rng.choice(N._AREAS_EN)),
                       time=f"{ctx.rng.randint(18, 20):02d}:{ctx.rng.choice([0, 15, 30, 45]):02d}",
                       weight=ctx.rng.choice([16, 20, 24, 28, 32, 40]))

# Approx coords for the 3 southern Bengaluru PS jurisdictions (arterial-adjacent).
_SOUTH_BLR = {
    "Jayanagar PS": (12.930, 77.583),
    "Basavanagudi PS": (12.941, 77.573),
    "J P Nagar PS": (12.906, 77.585),
}


def _load(name: str) -> dict:
    return yaml.safe_load((PLANTED_DIR / name).read_text(encoding="utf-8"))


def _lookups(tables) -> tuple[dict, dict]:
    unit = tables["Unit"]
    dist = tables["District"]
    id2name = dict(zip(dist["DistrictID"], dist["DistrictName"], strict=True))
    by_name: dict[tuple[str, str], int] = {}
    by_district: dict[str, list[int]] = {}
    for _, r in unit.iterrows():
        dn = id2name[r["DistrictID"]]
        by_name[(dn, r["UnitName"])] = int(r["UnitID"])
        by_district.setdefault(dn, []).append(int(r["UnitID"]))
    return by_name, by_district


def _dob(age: int) -> date:
    return date(2026 - age, 6, 15)


def _near(ctx: Ctx, lat: float, lon: float, km: float) -> tuple[float, float]:
    deg = km / 111.0
    return (round(lat + float(ctx.np_rng.uniform(-deg, deg)), 6),
            round(lon + float(ctx.np_rng.uniform(-deg, deg)), 6))


def _dt(d: date, ctx: Ctx, lo: int = 18, hi: int = 21) -> datetime:
    return datetime(d.year, d.month, d.day, ctx.rng.randint(lo, hi - 1),
                    ctx.rng.choice([0, 15, 30, 45]))


def plant_all(ctx: Ctx, tables) -> dict:
    by_name, by_district = _lookups(tables)
    truth: dict = {}
    truth["SP1"] = _plant_sp1(ctx, by_name, by_district)
    truth["SP2"] = _plant_sp2(ctx, by_name, by_district)
    truth["SP3"] = _plant_sp3(ctx, by_name, by_district)
    truth["SP4"] = _plant_sp4(ctx, by_name, by_district)
    return truth


# ---------------------------------------------------------------------------
# SP-1 / SH-07 — chain-snatching serial
# ---------------------------------------------------------------------------
def _plant_sp1(ctx: Ctx, by_name, by_district) -> dict:
    cfg = _load("sp1.yaml")
    sub = M.SUBHEAD_BY_NAME[cfg["subhead"]]

    # Register the ring with fixed keys + Bengaluru-south homes.
    for m in cfg["ring"]:
        lat, lon = _SOUTH_BLR["Jayanagar PS"]
        ctx.register_person(m["key"], m["name"], _dob(m["age"]),
                            h3.latlng_to_cell(lat, lon, 8), notes="SH-07 ring")
    ravi, manju, third = (m["key"] for m in cfg["ring"])

    # Explicit 14-case schedule honouring 8/3/3 split, 5 KN, solved seq 4 & 9.
    plan = [
        (1, "Bengaluru City", "Jayanagar PS", "en", None),
        (2, "Bengaluru City", "Basavanagudi PS", "en", None),
        (3, "Bengaluru City", "J P Nagar PS", "kn", None),
        (4, "Tumakuru", "Tumakuru Town PS", "en", ravi),      # SP1-04 solved (Feb)
        (5, "Bengaluru City", "Jayanagar PS", "en", None),
        (6, "Mandya", "Mandya East PS", "kn", None),
        (7, "Bengaluru City", "Basavanagudi PS", "en", None),
        (8, "Tumakuru", "Tumakuru Town PS", "kn", None),
        (9, "Bengaluru City", "J P Nagar PS", "en", manju),   # SP1-09 solved (Apr)
        (10, "Mandya", "Mandya East PS", "en", None),
        (11, "Bengaluru City", "Jayanagar PS", "kn", None),
        (12, "Tumakuru", "Tumakuru Town PS", "en", None),
        (13, "Bengaluru City", "Basavanagudi PS", "en", None),
        (14, "Mandya", "Mandya East PS", "kn", None),
    ]
    base = date.fromisoformat(cfg["window"]["from"])
    case_ids, solved_ids = [], []
    for seq, dname, psname, lang, arrested in plan:
        d = M.DISTRICT_BY_NAME[dname]
        unit_id = by_name.get((dname, psname), by_district[dname][0])
        day = base + timedelta(days=13 * (seq - 1))
        while day.weekday() not in (1, 2, 3, 4, 5):  # Tue..Sat
            day += timedelta(days=1)
        reg_dt = _dt(day, ctx)
        if psname in _SOUTH_BLR:
            lat, lon = _near(ctx, *_SOUTH_BLR[psname], 0.4)
        else:
            lat, lon = _near(ctx, d.lat, d.lon, 3.0)
        victim = N.full_name(ctx.rng, lang)
        brief = _sp1_brief(ctx, lang, victim)
        status = 2 if arrested else 1
        cid = emit_case(
            ctx, d=d, unit_id=unit_id, cat=1, sub=sub, reg_dt=reg_dt, status=status,
            lang=lang, accused_pks=[arrested] if arrested else [], comp_name=victim,
            lat=lat, lon=lon, incident_from=reg_dt,  # incident IS the evening crime time
            arrest=bool(arrested),
            arrest_date=reg_dt.date() + timedelta(days=ctx.rng.randint(10, 45)),
            brief=brief, add_victim=True,
        )
        case_ids.append(cid)
        if arrested:
            solved_ids.append(cid)

    # Priors: two 2024 Ramanagara thefts (Ravi+Manju co-accused) + one 2023 Ravi arrest.
    theft = M.SUBHEAD_BY_NAME["Theft"]
    rmn = M.DISTRICT_BY_NAME["Ramanagara"]
    rmn_ps = by_name.get(("Ramanagara", "Ramanagara Town PS"), by_district["Ramanagara"][0])
    prior_ids = []
    for i in range(cfg["priors"]["ramanagara_theft_2024"]):
        reg = datetime(2024, 3 + i * 2, 12, 21, 0)
        prior_ids.append(emit_case(
            ctx, d=rmn, unit_id=rmn_ps, cat=1, sub=theft, reg_dt=reg, status=2,
            lang="en", accused_pks=[ravi, manju], arrest=True,
            arrest_date=reg.date() + timedelta(days=20)))
    if cfg["priors"].get("ravi_arrest_2023"):
        reg = datetime(2023, 7, 18, 20, 0)
        prior_ids.append(emit_case(
            ctx, d=rmn, unit_id=rmn_ps, cat=1, sub=theft, reg_dt=reg, status=2,
            lang="en", accused_pks=[ravi], arrest=True,
            arrest_date=reg.date() + timedelta(days=15)))

    return {"series_id": cfg["series_id"], "subhead": cfg["subhead"], "case_ids": case_ids,
            "solved_case_ids": solved_ids, "ring": [ravi, manju, third],
            "prior_case_ids": prior_ids, "districts": cfg["distribution"]}


# ---------------------------------------------------------------------------
# SP-2 / Prakash web — investment-fraud hub
# ---------------------------------------------------------------------------
def _plant_sp2(ctx: Ctx, by_name, by_district) -> dict:
    cfg = _load("sp2.yaml")
    sub = M.SUBHEAD_BY_NAME[cfg["subhead"]]
    hub = cfg["hub"]
    ctx.register_person(hub["key"], hub["name"], _dob(hub["age"]),
                        h3.latlng_to_cell(12.97, 77.60, 8), notes="fraud hub")
    phone = cfg["mule_phone"]

    districts: list[str] = []
    for dname, n in cfg["distribution"].items():
        districts += [dname] * int(n)
    total = len(districts)
    ctx.rng.shuffle(districts)
    start = date.fromisoformat(cfg["window"]["from"])
    end = date.fromisoformat(cfg["window"]["to"])
    span = (end - start).days

    case_ids, named_ids, phone_ids = [], [], []
    loss_target = cfg["aggregate_loss_cr"] * 1_00_00_000  # crore -> rupees
    per = int(loss_target / total)
    for i, dname in enumerate(districts):
        d = M.DISTRICT_BY_NAME[dname]
        unit_id = ctx.rng.choice(by_district[dname])
        reg = start + timedelta(days=ctx.rng.randint(0, span))
        reg_dt = datetime(reg.year, reg.month, reg.day, ctx.rng.randint(9, 20), 0)
        named = i < cfg["named_in"]
        app = ctx.rng.choice(cfg["app_names"])
        amt = per + ctx.rng.randint(-200000, 200000)
        lang = "kn" if ctx.rng.random() < 0.25 else "en"
        brief = (f"The complainant reported that through the '{app}' trading app promising "
                 f"high weekly returns, an amount of Rs. {amt:,} was invested via UPI. After "
                 f"small initial payouts the account was blocked. Payments were routed to a "
                 f"mule account linked to phone {phone}.")
        cid = emit_case(ctx, d=d, unit_id=unit_id, cat=1, sub=sub, reg_dt=reg_dt,
                        status=ctx.rng.choices([1, 2], weights=[0.8, 0.2])[0], lang=lang,
                        accused_pks=[hub["key"]] if named else [], brief=brief)
        case_ids.append(cid)
        (named_ids if named else phone_ids).append(cid)

    return {"hub": hub["key"], "case_ids": case_ids, "named_case_ids": named_ids,
            "phone_case_ids": phone_ids, "mule_phone": phone}


# ---------------------------------------------------------------------------
# SP-3 — festival burglary wave + live Whitefield spike
# ---------------------------------------------------------------------------
def _plant_sp3(ctx: Ctx, by_name, by_district) -> dict:
    cfg = _load("sp3.yaml")
    sub = M.SUBHEAD_BY_NAME[cfg["subhead"]]
    seasonal_ids, live_ids = [], []

    # Seasonal Oct-Nov bumps in 4 districts across 3 years.
    per_dy = round(cfg["baseline_per_week"] * (cfg["seasonal"]["multiplier"][1] - 1)
                   * cfg["seasonal"]["weeks"])  # extra cases per district-year
    for dname in cfg["districts"]:
        d = M.DISTRICT_BY_NAME[dname]
        for yr in cfg["seasonal"]["years"]:
            for _ in range(per_dy):
                unit_id = ctx.rng.choice(by_district[dname])
                day = date(yr, 10, 1) + timedelta(days=ctx.rng.randint(0, 45))
                reg_dt = datetime(day.year, day.month, day.day, ctx.rng.randint(22, 23), 0)
                seasonal_ids.append(emit_case(
                    ctx, d=d, unit_id=unit_id, cat=1, sub=sub, reg_dt=reg_dt,
                    status=ctx.rng.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0],
                    lang="en", accused_pks=[]))

    # Live spike: last 14 days, Whitefield.
    ls = cfg["live_spike"]
    d = M.DISTRICT_BY_NAME[ls["district"]]
    unit_id = by_name.get((ls["district"], ls["station"]), by_district[ls["district"]][0])
    end = date.fromisoformat(ls["end"])
    for _ in range(ls["extra_cases"]):
        day = end - timedelta(days=ctx.rng.randint(0, ls["window_days"] - 1))
        reg_dt = datetime(day.year, day.month, day.day, ctx.rng.randint(1, 4), 0)
        brief = ("Unknown persons entered the house through the rear window while the "
                 "occupants were away and decamped with cash and jewellery. Empty-house "
                 "burglary; pre-dawn entry.")
        live_ids.append(emit_case(ctx, d=d, unit_id=unit_id, cat=1, sub=sub, reg_dt=reg_dt,
                                  status=1, lang="en", accused_pks=[], brief=brief))

    return {"district": ls["district"], "station": ls["station"],
            "live_spike_case_ids": live_ids, "seasonal_case_ids": seasonal_ids}


# ---------------------------------------------------------------------------
# SP-4 — Suresh B escalating repeat offender
# ---------------------------------------------------------------------------
def _plant_sp4(ctx: Ctx, by_name, by_district) -> dict:
    cfg = _load("sp4.yaml")
    p = cfg["person"]
    home = cfg["home"]
    home_h3 = h3.latlng_to_cell(home["lat"], home["lon"], 8)
    ctx.register_person(p["key"], p["name"], _dob(p["age"]), home_h3, notes="repeat offender")
    blr = M.DISTRICT_BY_NAME[home["district"]]
    # Peenya falls under a Bengaluru City PS; use Whitefield-independent generic pick.
    unit_id = by_district[home["district"]][0]

    history_ids = []
    for step in cfg["trajectory"]:
        sub = M.SUBHEAD_BY_NAME[step["subhead"]]
        month = step.get("arrest_month", ctx.rng.randint(2, 11))
        reg_dt = datetime(step["year"], month, ctx.rng.randint(1, 28), ctx.rng.randint(20, 23), 0)
        lat, lon = _near(ctx, home["lat"], home["lon"], 2.0)
        arr_date = (date(2025, 11, 20) if step.get("arrest_month")
                    else reg_dt.date() + timedelta(days=ctx.rng.randint(10, 40)))
        history_ids.append(emit_case(
            ctx, d=blr, unit_id=unit_id, cat=1, sub=sub, reg_dt=reg_dt, status=step["status"],
            lang="en", accused_pks=[p["key"]], lat=lat, lon=lon, arrest=True, arrest_date=arr_date))

    # Fresh unsolved cluster near home after release.
    fc = cfg["fresh_cluster"]
    sub = M.SUBHEAD_BY_NAME[fc["subhead"]]
    fstart = date.fromisoformat(fc["window"]["from"])
    fspan = (date.fromisoformat(fc["window"]["to"]) - fstart).days
    fresh_ids = []
    for _ in range(fc["count"]):
        day = fstart + timedelta(days=ctx.rng.randint(0, fspan))
        reg_dt = datetime(day.year, day.month, day.day, ctx.rng.randint(22, 23), 0)
        lat, lon = _near(ctx, home["lat"], home["lon"], fc["radius_km"])
        brief = ("House burgled via the rear window while occupants were away; pre-midnight "
                 "entry. Matches earlier empty-house burglaries in the locality.")
        fresh_ids.append(emit_case(ctx, d=blr, unit_id=unit_id, cat=1, sub=sub, reg_dt=reg_dt,
                                   status=fc["status"], lang="en", accused_pks=[], lat=lat,
                                   lon=lon, brief=brief))

    return {"person": p["key"], "history_case_ids": history_ids,
            "fresh_cluster_case_ids": fresh_ids, "home_h3": home_h3}
