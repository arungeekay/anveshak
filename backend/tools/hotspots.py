"""hotspots tool (contracts.md §7): H3 res-8 aggregation of case points + intensity."""
from __future__ import annotations

from collections import defaultdict

import h3

from ..db import get_connection


def hotspots(crime_sub_head: str | None = None, district: str | None = None,
             date_from: str | None = None, date_to: str | None = None,
             h3_res: int = 8, con=None) -> dict:
    con = con or get_connection()
    sql = "SELECT latitude, longitude FROM vw_case_360 WHERE latitude IS NOT NULL"
    params: list = []
    if crime_sub_head:
        sql += " AND crime_sub_head = ?"
        params.append(crime_sub_head)
    if district:
        sql += " AND district = ?"
        params.append(district)
    if date_from:
        sql += " AND CrimeRegisteredDate >= CAST(? AS DATE)"
        params.append(date_from)
    if date_to:
        sql += " AND CrimeRegisteredDate <= CAST(? AS DATE)"
        params.append(date_to)
    rows = con.execute(sql, params).fetchall()

    cells: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for lat, lon in rows:
        cells[h3.latlng_to_cell(float(lat), float(lon), h3_res)].append((float(lat), float(lon)))
    peak = max((len(v) for v in cells.values()), default=1)
    out = []
    for cell, pts in cells.items():
        clat = sum(p[0] for p in pts) / len(pts)
        clon = sum(p[1] for p in pts) / len(pts)
        out.append({"h3": cell, "count": len(pts), "intensity": round(len(pts) / peak, 3),
                    "lat": round(clat, 6), "lon": round(clon, 6)})
    out.sort(key=lambda c: -c["count"])
    return {"cells": out}
