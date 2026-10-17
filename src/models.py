"""LightGBM search space (Jesus et al. 2022, App A.2; repo lightgbm_hyperparameter_space.yaml) and model fits."""

import warnings

import lightgbm as lgb
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

N_ESTIMATORS_CAP = 2000  # paper range is 20 to 10000; capped for compute (PROTOCOL.md)


def _log_int(rng, lo, hi):
    return int(round(np.exp(rng.uniform(np.log(lo), np.log(hi)))))


def sample_configs(n, seed):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        out.append(
            dict(
                n_estimators=_log_int(rng, 20, N_ESTIMATORS_CAP),
                max_depth=int(rng.integers(3, 31)),
                learning_rate=float(np.exp(rng.uniform(np.log(0.02), np.log(0.1)))),
                num_leaves=_log_int(rng, 10, 100),
                boosting=str(rng.choice(["gbdt", "goss"])),
                min_data_in_leaf=_log_int(rng, 5, 200),
                max_bin=int(rng.integers(100, 501)),
                enable_bundle=bool(rng.choice([True, False])),
            )
        )
    return out


def lgbm_params(config, seed, n_jobs=8):
    p = dict(
        objective="binary",
        n_estimators=config["n_estimators"],
        max_depth=config["max_depth"],
        learning_rate=config["learning_rate"],
        num_leaves=config["num_leaves"],
        min_child_samples=config["min_data_in_leaf"],
        max_bin=config["max_bin"],
        enable_bundle=config["enable_bundle"],
        colsample_bytree=0.8,  # feature_fraction, so that the seed changes the model (PROTOCOL.md)
        random_state=seed,
        n_jobs=n_jobs,
        verbose=-1,
    )
    if config["boosting"] == "goss":
        p["data_sample_strategy"] = "goss"
    else:
        p.update(subsample=0.8, subsample_freq=1)
    return p


def fit_lgbm(X, y, config, seed, n_jobs=8):
    return lgb.LGBMClassifier(**lgbm_params(config, seed, n_jobs)).fit(X, y)


def fit_lr(X, y, seed):
    model = LogisticRegression(max_iter=2000, solver="lbfgs", random_state=seed)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        model.fit(X, y)
    return model
