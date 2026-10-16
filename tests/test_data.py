import numpy as np
import pandas as pd
import pytest

from src.data import (
    MAIN_SPLIT,
    PAPER_SPLIT,
    age_group,
    apply_sentinels,
    split_by_month,
    stratified_sample,
)


def test_sentinels_become_nan_only_where_documented():
    df = pd.DataFrame(
        {
            "prev_address_months_count": [-1, 0, 5],
            "intended_balcon_amount": [-0.5, -16.0, 3.0],
            "velocity_6h": [-10.0, 1.0, 2.0],  # negative but not documented as missing
        }
    )
    out = apply_sentinels(df)
    assert out["prev_address_months_count"].isna().tolist() == [True, False, False]
    assert out["intended_balcon_amount"].isna().tolist() == [True, True, False]
    assert out["velocity_6h"].isna().sum() == 0
    # Input is not modified.
    assert df["prev_address_months_count"].iloc[0] == -1


def test_main_split_months():
    assert MAIN_SPLIT == dict(train=[0, 1, 2], validation=[3], test=[4, 5, 6, 7])
    assert PAPER_SPLIT == dict(train=[0, 1, 2, 3, 4, 5], test=[6, 7])


def test_split_by_month_is_disjoint_and_complete():
    df = pd.DataFrame({"month": np.repeat(np.arange(8), 3), "x": np.arange(24)})
    parts = split_by_month(df, MAIN_SPLIT)
    seen = np.concatenate([p["x"].to_numpy() for p in parts.values()])
    assert sorted(seen.tolist()) == list(range(24))
    assert set(parts["validation"]["month"]) == {3}


def test_age_group_definitions():
    ages = pd.Series([10, 40, 50, 60, 90])
    assert age_group(ages, ">=50").tolist() == [0, 0, 1, 1, 1]
    assert age_group(ages, ">50").tolist() == [0, 0, 0, 1, 1]
    with pytest.raises(ValueError):
        age_group(ages, "50")


def test_stratified_sample_keeps_month_by_label_counts():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "month": rng.integers(0, 8, 20000),
            "fraud_bool": (rng.random(20000) < 0.02).astype(int),
        }
    )
    s = stratified_sample(df, 0.1, seed=0)
    full = df.groupby(["month", "fraud_bool"]).size()
    part = s.groupby(["month", "fraud_bool"]).size()
    assert ((part - (full * 0.1).round()).abs() <= 1).all()
    assert s.index.is_unique and s.index.isin(df.index).all()
