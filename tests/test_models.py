import numpy as np
import pandas as pd

from src.models import N_ESTIMATORS_CAP, fit_lgbm, fit_lr, lgbm_params, sample_configs


def _xy(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n), "c": pd.Categorical(rng.choice(["x", "y"], n))})
    y = (X["a"] + rng.normal(size=n) > 1.5).astype(int).to_numpy()
    return X, y


def test_configs_stay_inside_paper_space_with_cap():
    for c in sample_configs(200, seed=0):
        assert 20 <= c["n_estimators"] <= N_ESTIMATORS_CAP
        assert 3 <= c["max_depth"] <= 30
        assert 0.02 <= c["learning_rate"] <= 0.1
        assert 10 <= c["num_leaves"] <= 100
        assert c["boosting"] in ("gbdt", "goss")
        assert 5 <= c["min_data_in_leaf"] <= 200
        assert 100 <= c["max_bin"] <= 500
        assert c["enable_bundle"] in (True, False)


def test_configs_are_reproducible():
    assert sample_configs(5, seed=1) == sample_configs(5, seed=1)


def test_goss_config_has_no_bagging_and_gbdt_has_bagging():
    gbdt = lgbm_params(dict(sample_configs(1, 0)[0], boosting="gbdt"), seed=0)
    goss = lgbm_params(dict(sample_configs(1, 0)[0], boosting="goss"), seed=0)
    assert gbdt["subsample"] == 0.8 and gbdt["subsample_freq"] == 1
    assert goss["data_sample_strategy"] == "goss" and "subsample_freq" not in goss


def test_seed_changes_lightgbm_model():
    X, y = _xy()
    cfg = dict(sample_configs(1, 0)[0], n_estimators=30, boosting="gbdt")
    p0 = fit_lgbm(X, y, cfg, seed=0, n_jobs=2).predict_proba(X)[:, 1]
    p1 = fit_lgbm(X, y, cfg, seed=1, n_jobs=2).predict_proba(X)[:, 1]
    p0b = fit_lgbm(X, y, cfg, seed=0, n_jobs=2).predict_proba(X)[:, 1]
    assert not np.allclose(p0, p1)
    np.testing.assert_array_equal(p0, p0b)


def test_logistic_regression_is_identical_across_seeds():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(2000, 4))
    y = (X[:, 0] + rng.normal(size=2000) > 1).astype(int)
    a = fit_lr(X, y, seed=0).predict_proba(X)[:, 1]
    b = fit_lr(X, y, seed=3).predict_proba(X)[:, 1]
    np.testing.assert_array_equal(a, b)
