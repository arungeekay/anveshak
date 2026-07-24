"""T04 verify: each planted pattern (SP-1..SP-4) is recoverable via gold SQL.

Builds an in-memory DuckDB from the *planted* dataset and runs the gold queries
(the same shapes demo_story.md freezes). Ground truth comes from generator's
return_truth so we can assert exact membership, not just aggregates.
"""
from __future__ import annotations

import pytest

from data_engine.build import build_duckdb
from data_engine.generator import generate

N_BG = 4000  # background volume for the test (planted patterns are added on top)


@pytest.fixture(scope="module")
def db():
    tables, truth = generate(seed=42, n_cases=N_BG, plant=True, return_truth=True)
    con = build_duckdb(tables)
    yield con, truth
    con.close()


def _scalar(con, sql: str):
    return con.execute(sql).fetchone()[0]


def _ids(seq) -> str:
    return ",".join(str(i) for i in seq)


# ----------------------------- SP-1 / SH-07 -----------------------------
def test_sp1_series_recoverable(db):
    con, truth = db
    sp1 = truth["SP1"]
    assert len(sp1["case_ids"]) == 14

    n_chain = _scalar(con, f"""
        SELECT COUNT(*) FROM vw_case_360
        WHERE CaseMasterID IN ({_ids(sp1['case_ids'])})
          AND crime_sub_head = 'Chain Snatching'
          AND district IN ('Bengaluru City','Tumakuru','Mandya')
    """)
    assert n_chain == 14, "all 14 planted cases must be Chain Snatching in the 3 districts"

    split = dict(con.execute(f"""
        SELECT district, COUNT(*) FROM vw_case_360
        WHERE CaseMasterID IN ({_ids(sp1['case_ids'])})
        GROUP BY district
    """).fetchall())
    assert split == {"Bengaluru City": 8, "Tumakuru": 3, "Mandya": 3}

    # The two "solved" cases are charge-sheeted and have arrests.
    n_solved = _scalar(con, f"""
        SELECT COUNT(*) FROM vw_case_360
        WHERE CaseMasterID IN ({_ids(sp1['solved_case_ids'])})
          AND case_status = 'Charge Sheeted'
    """)
    assert n_solved == 2


def test_sp1_ring_co_accusal_history(db):
    con, truth = db
    ravi, manju, _ = truth["SP1"]["ring"]
    # Ravi & Manju share the two 2024 Ramanagara theft cases (co-accusal edge).
    shared = _scalar(con, f"""
        SELECT COUNT(*) FROM (
          SELECT CaseMasterID FROM vw_accused_history WHERE person_key='{ravi}'
          INTERSECT
          SELECT CaseMasterID FROM vw_accused_history WHERE person_key='{manju}'
        )
    """)
    assert shared >= 2
    # Ravi appears in more cases than Manju (drives risk_score ordering later).
    n_ravi = _scalar(con, f"SELECT COUNT(*) FROM vw_accused_history WHERE person_key='{ravi}'")
    n_manju = _scalar(con, f"SELECT COUNT(*) FROM vw_accused_history WHERE person_key='{manju}'")
    assert n_ravi > n_manju


# ----------------------------- SP-2 / Prakash web -----------------------------
def test_sp2_hub_recoverable(db):
    con, truth = db
    sp2 = truth["SP2"]
    assert len(sp2["case_ids"]) == 22

    n_fraud = _scalar(con, f"""
        SELECT COUNT(*) FROM vw_case_360
        WHERE CaseMasterID IN ({_ids(sp2['case_ids'])})
          AND crime_sub_head = 'Cheating / Online Fraud'
    """)
    assert n_fraud == 22

    n_named = _scalar(con, f"""
        SELECT COUNT(DISTINCT CaseMasterID) FROM vw_accused_history
        WHERE person_key = '{sp2['hub']}'
    """)
    assert n_named == 14, "Prakash is a named accused in exactly 14 cases"

    # The mule phone is embedded in all 22 narratives (graph links the 22-spoke hub).
    n_phone = _scalar(con, f"""
        SELECT COUNT(*) FROM vw_case_360
        WHERE CaseMasterID IN ({_ids(sp2['case_ids'])})
          AND BriefFacts LIKE '%{sp2['mule_phone']}%'
    """)
    assert n_phone == 22


# ----------------------------- SP-3 / burglary wave -----------------------------
def test_sp3_live_spike(db):
    con, truth = db
    sp3 = truth["SP3"]
    n_spike = _scalar(con, """
        SELECT COUNT(*) FROM vw_case_360
        WHERE crime_sub_head = 'House Burglary (Night)'
          AND police_station = 'Whitefield PS'
          AND CrimeRegisteredDate >= DATE '2026-07-07'
    """)
    assert n_spike >= 9, "live Whitefield mini-spike must be present in the last 14 days"
    assert len(sp3["live_spike_case_ids"]) == 9


def test_sp3_seasonal_bump(db):
    con, _ = db
    districts = "'Bengaluru City','Mysuru','Belagavi','Dharwad'"
    festival = _scalar(con, f"""
        SELECT COUNT(*) FROM vw_case_360
        WHERE crime_sub_head='House Burglary (Night)' AND district IN ({districts})
          AND year(CrimeRegisteredDate)=2024 AND month(CrimeRegisteredDate) IN (10,11)
    """)
    off = _scalar(con, f"""
        SELECT COUNT(*) FROM vw_case_360
        WHERE crime_sub_head='House Burglary (Night)' AND district IN ({districts})
          AND year(CrimeRegisteredDate)=2024 AND month(CrimeRegisteredDate) BETWEEN 1 AND 9
    """)
    off_2mo = (off / 9.0) * 2.0
    assert festival > 1.8 * off_2mo, f"Oct-Nov 2024 ({festival}) must exceed baseline ({off_2mo:.1f})"


# ----------------------------- SP-4 / Suresh B -----------------------------
def test_sp4_repeat_offender(db):
    con, truth = db
    sp4 = truth["SP4"]
    rows = con.execute(f"""
        SELECT crime_sub_head FROM vw_accused_history
        WHERE person_key = '{sp4['person']}'
        ORDER BY CrimeRegisteredDate
    """).fetchall()
    subheads = [r[0] for r in rows]
    assert len(subheads) == 5, "5-case escalation history"
    assert {"Theft", "House Burglary (Night)", "Robbery"}.issubset(set(subheads))

    # Fresh cluster: 4 unsolved burglaries, NOT attributed to any accused.
    assert len(sp4["fresh_cluster_case_ids"]) == 4
    n_fresh_unsolved = _scalar(con, f"""
        SELECT COUNT(*) FROM vw_case_360
        WHERE CaseMasterID IN ({_ids(sp4['fresh_cluster_case_ids'])})
          AND case_status = 'Under Investigation' AND accused_count = 0
    """)
    assert n_fresh_unsolved == 4


# ----------------------------- appendix numbers -----------------------------
def test_print_demo_appendix(db, capsys):
    con, truth = db
    d1 = _scalar(con, """
        SELECT COUNT(*) FROM vw_case_360
        WHERE crime_sub_head='Chain Snatching' AND district='Bengaluru City'
          AND year(CrimeRegisteredDate)=2026
    """)
    with capsys.disabled():
        print("\n=== demo_story appendix (measured) ===")
        print(f"D1 scalar (Chain Snatching, Bengaluru City, 2026): {d1}")
        print(f"SH-07 series_id: {truth['SP1']['series_id']}")
        print(f"Prakash hub person_key: {truth['SP2']['hub']}")
        print(f"SP1 case_ids: {truth['SP1']['case_ids']}")
        print(f"SP3 live-spike case_ids: {truth['SP3']['live_spike_case_ids']}")
    assert d1 >= 8
