"""Serial Crime Linkage Engine (flagship): weighted MO similarity + HDBSCAN.

Candidate pairs are restricted to the same crime sub-head, Under-Investigation
status, within 180 days and 120 km (contracts.md §3, CLAUDE.md ADR-5). Similarity =
narrative-embedding cosine (0.55) + structured MO feature matches (vehicle/target
0.20, tod/dow 0.15) + geo proximity (0.10). Dense clusters (>=4) become
SeriesHypotheses with per-link shared features and shared narrative phrases.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml
from sklearn.cluster import HDBSCAN

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
SP1_DISTRICTS = {"Bengaluru City", "Tumakuru", "Mandya"}


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _load_cases(con) -> dict:
    rows = con.execute("""
        SELECT c.CaseMasterID, c.crime_sub_head, c.district, c.police_station,
               c.CrimeRegisteredDate, c.latitude, c.longitude, c.case_status,
               c.BriefFacts, v.embedding, v.mo_features
        FROM vw_case_360 c JOIN CaseMOVector v USING (CaseMasterID)
        WHERE c.case_status = 'Under Investigation'
    """).fetchall()
    cols = ["case_id", "sub_head", "district", "ps", "date", "lat", "lon", "status",
            "brief", "embedding", "mo_features"]
    data = {c: [] for c in cols}
    for r in rows:
        for i, c in enumerate(cols):
            data[c].append(r[i])
    return data


def _haversine(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    R = 6371.0
    latr, lonr = np.radians(lat), np.radians(lon)
    dlat = latr[:, None] - latr[None, :]
    dlon = lonr[:, None] - lonr[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(latr)[:, None] * np.cos(latr)[None, :] * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _feat_match(values: list) -> tuple[np.ndarray, np.ndarray]:
    arr = np.array(["" if v is None else str(v) for v in values], dtype=object)
    valid = arr != ""
    match = (arr[:, None] == arr[None, :]) & valid[:, None] & valid[None, :]
    return match.astype(float), arr


_WORD = re.compile(r"[a-zA-Z]+")


def _phrases(a: str, b: str, k: int = 3) -> list[str]:
    def bigrams(s: str) -> set[str]:
        toks = _WORD.findall((s or "").lower())
        return {f"{toks[i]} {toks[i + 1]}" for i in range(len(toks) - 1)}
    common = bigrams(a) & bigrams(b)
    stop = {"the complainant", "at about", "about hrs", "near the", "on a"}
    ranked = sorted((p for p in common if p not in stop), key=len, reverse=True)
    return ranked[:k]


def _cluster_subhead(idx: list[int], data: dict, cfg: dict) -> dict[int, list[int]]:
    emb = np.array([data["embedding"][i] for i in idx], dtype=float)
    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    cos = emb @ emb.T

    feats = [json.loads(data["mo_features"][i]) for i in idx]
    veh, _ = _feat_match([f.get("vehicle") for f in feats])
    tgt, _ = _feat_match([f.get("target") for f in feats])
    tod, _ = _feat_match([f.get("tod_bucket") for f in feats])
    dow, _ = _feat_match([str(f.get("dow")) for f in feats])

    lat = np.array([data["lat"][i] for i in idx], dtype=float)
    lon = np.array([data["lon"][i] for i in idx], dtype=float)
    dist_km = _haversine(lat, lon)
    scale = cfg["filters"]["geo_scale_km"]
    geo_sim = 1.0 - np.minimum(dist_km, scale) / scale

    dates = np.array([np.datetime64(data["date"][i], "D") for i in idx])
    dt_days = np.abs((dates[:, None] - dates[None, :]).astype("timedelta64[D]").astype(int))

    w = cfg["weights"]
    combined = (w["embedding"] * cos + w["vehicle"] * veh + w["target"] * tgt
                + w["tod"] * tod + w["dow"] * dow + w["geo"] * geo_sim)
    feasible = (dt_days <= cfg["filters"]["max_days"]) & (dist_km <= cfg["filters"]["max_km"])
    combined = np.where(feasible, combined, 0.0)
    np.fill_diagonal(combined, 1.0)

    dist = np.clip(1.0 - combined, 0.0, 1.0)
    dist = (dist + dist.T) / 2
    np.fill_diagonal(dist, 0.0)

    labels = HDBSCAN(
        metric="precomputed",
        min_cluster_size=cfg["cluster"]["min_cluster_size"],
        min_samples=cfg["cluster"]["min_samples"],
        cluster_selection_epsilon=float(cfg["cluster"].get("selection_epsilon", 0.0)),
    ).fit_predict(dist)
    clusters: dict[int, list[int]] = {}
    for local_i, lab in enumerate(labels):
        if lab >= 0:
            clusters.setdefault(int(lab), []).append(local_i)
    # store matrices for hypothesis building
    return {"clusters": clusters, "idx": idx, "cos": cos, "combined": combined, "feats": feats}


def _build_hypothesis(members_local: list[int], ctx: dict, data: dict, cfg: dict) -> dict:
    idx = ctx["idx"]
    gidx = [idx[i] for i in members_local]
    case_ids = [int(data["case_id"][g]) for g in gidx]
    districts = sorted({data["district"][g] for g in gidx})
    sub_head = data["sub_head"][gidx[0]]
    dates = [data["date"][g] for g in gidx]
    combined = ctx["combined"]
    cos = ctx["cos"]

    # confidence = mean pairwise combined similarity within the cluster
    pairs = [(a, b) for i, a in enumerate(members_local) for b in members_local[i + 1:]]
    sims = [combined[a, b] for a, b in pairs]
    confidence = float(np.mean(sims)) if sims else 0.0

    # top links by embedding cosine
    links = []
    for a, b in sorted(pairs, key=lambda p: cos[p[0], p[1]], reverse=True)[:12]:
        ga, gb = idx[a], idx[b]
        fa, fb = ctx["feats"][a], ctx["feats"][b]
        shared = []
        for key in ("vehicle", "target", "tod_bucket"):
            if fa.get(key) and fa.get(key) == fb.get(key):
                shared.append(f"{key}:{fa[key]}")
        links.append({
            "case_a": int(data["case_id"][ga]), "case_b": int(data["case_id"][gb]),
            "cosine": round(float(cos[a, b]), 3), "shared_features": shared,
            "evidence_phrases": _phrases(data["brief"][ga], data["brief"][gb]),
        })

    return {
        "case_ids": sorted(case_ids),
        "confidence": round(confidence, 3),
        "crime_sub_head": sub_head,
        "districts": districts,
        "time_span": {"from": str(min(dates)), "to": str(max(dates))},
        "mo_summary": _mo_summary(ctx, members_local),
        "links": links,
        "status": "open",
        "linked_person_keys": [],
    }


def _mo_summary(ctx: dict, members_local: list[int]) -> str:
    feats = [ctx["feats"][i] for i in members_local]
    def top(key):
        vals = [f.get(key) for f in feats if f.get(key)]
        return max(set(vals), key=vals.count) if vals else None
    parts = []
    for key, label in (("vehicle", "vehicle"), ("target", "target"), ("tod_bucket", "time")):
        v = top(key)
        if v:
            parts.append(f"{label}={v}")
    return "; ".join(parts) or "recurring MO"


def _assign_ids(hyps: list[dict]) -> list[dict]:
    hyps = sorted(hyps, key=lambda h: h["confidence"], reverse=True)
    used = set()

    # Flagship = the LARGEST chain-snatching series spanning the SP-1 districts.
    flagship_candidates = [
        h for h in hyps
        if h["crime_sub_head"] == "Chain Snatching" and SP1_DISTRICTS.issubset(set(h["districts"]))
    ]
    if flagship_candidates:
        flagship = max(flagship_candidates, key=lambda h: len(h["case_ids"]))
        flagship["series_id"] = "SH-07"
        used.add(7)
    counter = 1
    for h in hyps:
        if h.get("series_id"):
            continue
        while counter in used:
            counter += 1
        h["series_id"] = f"SH-{counter:02d}"
        used.add(counter)
        counter += 1
    for h in hyps:
        h["name"] = f"{h['crime_sub_head']} series — {', '.join(h['districts'][:3])}"
    return hyps


def discover(con) -> list[dict]:
    cfg = config()
    data = _load_cases(con)
    by_sub: dict[str, list[int]] = {}
    for i, sh in enumerate(data["sub_head"]):
        by_sub.setdefault(sh, []).append(i)

    hyps: list[dict] = []
    for _sh, idx in by_sub.items():
        if len(idx) < cfg["cluster"]["min_cluster_size"] or len(idx) > cfg["cluster"]["max_subset"]:
            continue
        ctx = _cluster_subhead(idx, data, cfg)
        for members in ctx["clusters"].values():
            if len(members) < cfg["cluster"]["min_cluster_size"]:
                continue
            h = _build_hypothesis(members, ctx, data, cfg)
            if h["confidence"] >= cfg["confidence_floor"]:
                hyps.append(h)
    return _assign_ids(hyps)
