import numpy as np
import pandas as pd
import pytest

from src.preprocess import LGBMPrep, LRPrep


def _frame(n, rng, months, extra_cat=None):
    df = pd.DataFrame(
        {
            "income": rng.random(n),
            "prev_address_months_count": rng.choice([-1, 5, 10], n),
            "customer_age": rng.choice([20, 50, 70], n),
            "payment_type": rng.choice(["AA", "AB"], n),
            "employment_status": rng.choice(["CA", "CB"], n),
            "housing_status": rng.choice(["BA", "BB"], n),
            "source": rng.choice(["INTERNET", "TELEAPP"], n),
            "device_os": rng.choice(["linux", "windows"], n),
            "month": rng.choice(months, n),
            "fraud_bool": (rng.random(n) < 0.1).astype(int),
        }
    )
    if extra_cat:
        df.loc[: n // 2, "payment_type"] = extra_cat
    return df


@pytest.fixture
def split():
    rng = np.random.default_rng(0)
    return _frame(2000, rng, [0, 1, 2]), _frame(500, rng, [6, 7], extra_cat="ZZ")


def test_lgbm_features_exclude_label_and_month(split):
    train, test = split
    prep = LGBMPrep().fit(train)
    X = prep.transform(test)
    assert "month" not in X.columns and "fraud_bool" not in X.columns


def test_lgbm_unseen_category_becomes_missing_and_categories_come_from_train(split):
    train, test = split
    X = LGBMPrep().fit(train).transform(test)
    assert list(X["payment_type"].cat.categories) == ["AA", "AB"]
    assert X["payment_type"].isna().sum() == (test["payment_type"] == "ZZ").sum()


def test_lgbm_sentinels_become_nan(split):
    train, _ = split
    X = LGBMPrep().fit(train).transform(train)
    assert X["prev_address_months_count"].isna().sum() == (train["prev_address_months_count"] == -1).sum()


def test_replication_mode_keeps_month_and_raw_sentinels(split):
    train, test = split
    X = LGBMPrep(include_month=True, raw_sentinels=True).fit(train).transform(test)
    assert "month" in X.columns
    assert (X["prev_address_months_count"] == -1).sum() == (test["prev_address_months_count"] == -1).sum()


def test_lr_statistics_are_fit_on_train_only(split):
    train, test = split
    prep = LRPrep().fit(train)
    before = prep.transform(train.head(5))
    # Changing the test month's values must not change how train rows are transformed.
    shifted = test.copy()
    shifted["income"] += 100
    prep.transform(shifted)
    after = prep.transform(train.head(5))
    np.testing.assert_array_equal(before, after)
    # Standardized training income has mean 0 on the training rows.
    Xtr = prep.transform(train)
    col = prep.feature_names.index("num__income")
    assert Xtr[:, col].mean() == pytest.approx(0.0, abs=1e-9)


def test_lr_adds_missing_indicator_and_ignores_unseen_category(split):
    train, test = split
    prep = LRPrep().fit(train)
    assert any("missingindicator_prev_address_months_count" in f for f in prep.feature_names)
    X = prep.transform(test)
    assert np.isfinite(X).all()
    assert "num__month" not in prep.feature_names
