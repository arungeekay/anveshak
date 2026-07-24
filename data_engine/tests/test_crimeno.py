"""T03 verify: CrimeNo composite validity, serial monotonicity, master counts."""
from __future__ import annotations

import pandas as pd
import pytest

from data_engine.generator import generate

VALID_CATEGORY_DIGITS = {1, 3, 4, 8}


@pytest.fixture(scope="module")
def data() -> dict[str, pd.DataFrame]:
    # Smaller n for test speed; invariants are independent of volume.
    return generate(seed=42, n_cases=3000)


def test_master_counts(data):
    assert len(data["District"]) == 31
    assert len(data["Unit"]) >= 240


def test_crimeno_format(data):
    cm = data["CaseMaster"]
    assert len(cm) == 3000
    for crimeno in cm["CrimeNo"]:
        assert len(crimeno) == 18, crimeno
        assert crimeno.isdigit()
        assert int(crimeno[0]) in VALID_CATEGORY_DIGITS
    # CaseNo is the last 9 digits (year + 5-digit serial)
    for cn, crimeno in zip(cm["CaseNo"], cm["CrimeNo"], strict=True):
        assert cn == crimeno[9:]


def test_crimeno_category_matches_column(data):
    cm = data["CaseMaster"]
    for crimeno, cat in zip(cm["CrimeNo"], cm["CaseCategoryID"], strict=True):
        assert int(crimeno[0]) == int(cat)


def test_serial_monotonic_per_ps_category_year(data):
    cm = data["CaseMaster"].copy()
    cm["year"] = cm["CrimeNo"].str[9:13].astype(int)
    cm["serial"] = cm["CrimeNo"].str[13:18].astype(int)
    cm = cm.sort_values("CaseMasterID")
    for (_ps, _cat, _yr), grp in cm.groupby(["PoliceStationID", "CaseCategoryID", "year"]):
        serials = grp["serial"].tolist()
        # Strictly increasing and a gapless 1..k sequence in creation order.
        assert serials == list(range(1, len(serials) + 1)), (_ps, _cat, _yr, serials[:5])


def test_district_ids_are_four_digit_safe(data):
    # District + unit ids must fit the 4-digit CrimeNo fields.
    assert data["District"]["DistrictID"].max() <= 9999
    assert data["Unit"]["UnitID"].max() <= 9999


def test_person_keys_stable_and_mapped(data):
    accused = data["Accused"]
    amap = data["AccusedPersonMap"]
    reg = data["PersonRegistry"]
    # Every mapped person exists in the registry.
    assert set(amap["person_key"]).issubset(set(reg["person_key"]))
    # Every accused row has a person mapping.
    assert set(amap["AccusedMasterID"]) == set(accused["AccusedMasterID"])
