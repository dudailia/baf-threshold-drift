"""Every fitted preprocessing step (scalers, encoders, imputers, category maps) and
every model fit uses training months only. Post hoc, added after the shuffled-label
tripwire fired (PROTOCOL.md, Decision log)."""

import numpy as np
import pandas as pd
import pytest

from src import config
from src.data import CATEGORICAL, MAIN_SPLIT, apply_sentinels
from src.preprocess import LGBMPrep, LRPrep
from tests.baf_fixture import make_variant, write_fixture


@pytest.fixture(scope="module")
def frame():
    df = make_variant("Base", 3000, seed=0)
    # Make test months clearly different so that any use of them would change fitted statistics.
    late = df["month"] >= 3
    df.loc[late, "income"] = 0.9
    df.loc[late, "velocity_6h"] += 50_000
    df.loc[late & (df.index % 2 == 0), "payment_type"] = "ZZ"
    return df


def test_lr_prep_statistics_equal_a_train_only_fit(frame):
    train = frame[frame.month.isin(MAIN_SPLIT["train"])]
    prep = LRPrep().fit(train)
    num = prep.ct.named_transformers_["num"]
    ref = apply_sentinels(train)[prep.columns]
    num_cols = [c for c in prep.columns if c not in CATEGORICAL]
    np.testing.assert_allclose(num.named_steps["impute"].statistics_, ref[num_cols].median().to_numpy())
    np.testing.assert_allclose(num.named_steps["scale"].mean_[: len(num_cols)],
                               ref[num_cols].fillna(ref[num_cols].median()).mean().to_numpy(), rtol=1e-10)
    cats = prep.ct.named_transformers_["cat"].categories_
    assert [list(c) for c in cats] == [sorted(train[c].unique()) for c in CATEGORICAL]
    # Transforming test months leaves the fitted statistics unchanged.
    before = num.named_steps["scale"].mean_.copy()
    prep.transform(frame)
    np.testing.assert_array_equal(before, num.named_steps["scale"].mean_)


def test_fitting_on_all_months_would_change_the_statistics(frame):
    train = frame[frame.month.isin(MAIN_SPLIT["train"])]
    a = LRPrep().fit(train).ct.named_transformers_["num"].named_steps["scale"].mean_
    b = LRPrep().fit(frame).ct.named_transformers_["num"].named_steps["scale"].mean_
    assert not np.allclose(a, b)


def test_lgbm_category_maps_come_from_train_months(frame):
    train = frame[frame.month.isin(MAIN_SPLIT["train"])]
    prep = LGBMPrep().fit(train)
    assert "ZZ" not in prep.categories["payment_type"]
    assert prep.categories == {c: sorted(train[c].astype(str).unique()) for c in CATEGORICAL}


def test_pipeline_fits_only_see_training_months(tmp_path, monkeypatch):
    """Spy on every preprocessing fit and model fit in the real training and check code."""
    import src.checks as checks
    import src.train as train

    raw = write_fixture(tmp_path / "raw", n_per_month=1500, variants=["Base"])
    for name, value in dict(RAW_DIR=raw, PREDICTIONS_DIR=tmp_path / "out" / "pred", CHECKPOINTS=tmp_path / "out" / "ckpt",
                            LOGS=tmp_path / "out" / "logs", RESULTS=tmp_path / "out", N_TRIALS=2, SEEDS=[0, 1], N_JOBS=1).items():
        monkeypatch.setattr(config, name, value)

    seen = []
    for cls in (LGBMPrep, LRPrep):
        orig = cls.fit
        monkeypatch.setattr(cls, "fit", lambda self, df, _o=orig: (seen.append(("prep", set(df["month"]))), _o(self, df))[1])
    n_train = {}
    orig_lgbm, orig_lr = train.fit_lgbm, train.fit_lr

    def spy_lgbm(X, y, *a, **k):
        seen.append(("lightgbm rows", len(X)))
        return orig_lgbm(X, y, *a, **k)

    def spy_lr(X, y, *a, **k):
        seen.append(("logreg rows", len(X)))
        return orig_lr(X, y, *a, **k)

    monkeypatch.setattr(train, "fit_lgbm", spy_lgbm)
    monkeypatch.setattr(train, "fit_lr", spy_lr)
    train.train_variant("Base", commit="test")
    df = pd.read_csv(raw / "Base.csv")
    n_train = int(df["month"].isin(MAIN_SPLIT["train"]).sum())
    preps = [months for kind, months in seen if kind == "prep"]
    assert preps and all(m <= set(MAIN_SPLIT["train"]) for m in preps)
    assert all(n == n_train for kind, n in seen if kind.endswith("rows"))

    seen.clear()
    checks._check_model(df, df.loc[df["month"].isin(MAIN_SPLIT["train"]), "fraud_bool"].to_numpy(),
                        train.sample_configs(1, 0)[0])
    assert all(m <= set(MAIN_SPLIT["train"]) for kind, m in seen if kind == "prep")
