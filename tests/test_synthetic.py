import numpy as np
import pytest
from scipy.stats import norm

from src.synthetic import MonthSpec, run_scenario, simulate_month

N = 400_000


def one_group(neg_mean=0.0, pos_mean=2.0, prevalence=0.01):
    return MonthSpec(
        group_share={"young": 1.0},
        prevalence={"young": prevalence},
        neg_mean={"young": neg_mean},
        pos_mean={"young": pos_mean},
    )


def _row(rows, strategy, month):
    (r,) = [r for r in rows if r["strategy"] == strategy and r["month"] == month]
    return r


def test_simulate_month_matches_requested_shares():
    spec = MonthSpec(
        group_share={"young": 0.8, "old": 0.2},
        prevalence={"young": 0.01, "old": 0.02},
        neg_mean={"young": 0.0, "old": 0.3},
        pos_mean={"young": 2.0, "old": 2.0},
    )
    df = simulate_month(spec, N, np.random.default_rng(0))
    assert (df["group"] == "old").mean() == pytest.approx(0.2, abs=0.003)
    assert df.loc[df["group"] == "old", "label"].mean() == pytest.approx(0.02, abs=0.002)
    neg_old = df.loc[(df["group"] == "old") & (df["label"] == 0), "score"]
    assert neg_old.mean() == pytest.approx(0.3, abs=0.01)


def test_identity_fpr_from_alert_share_tpr_and_prevalence_holds_exactly():
    months = [one_group(), one_group(neg_mean=0.4), one_group(neg_mean=0.4)]
    rows = run_scenario(months, N, seed=1)
    for r in rows:
        implied = (r["alert_share"] - r["tpr"] * r["prevalence"]) / (1 - r["prevalence"])
        assert r["fpr"] == pytest.approx(implied, abs=1e-12)


def test_no_shift_keeps_static_on_budget():
    rows = run_scenario([one_group()] * 3, N, seed=2)
    assert _row(rows, "static", 2)["fpr"] == pytest.approx(0.05, abs=0.002)


def test_negative_shift_static_fpr_matches_analytic_value():
    d = 0.3
    rows = run_scenario([one_group(), one_group(neg_mean=d), one_group(neg_mean=d)], N, seed=3)
    expected = norm.sf(norm.ppf(0.95) - d)
    assert _row(rows, "static", 1)["fpr"] == pytest.approx(expected, abs=0.003)
    # One month later, delayed-label lag 1 has seen the shifted negatives.
    assert _row(rows, "delayed_lag1", 2)["fpr"] == pytest.approx(0.05, abs=0.002)


def test_positive_shift_leaves_static_fpr_unchanged_and_lowers_tpr():
    rows = run_scenario([one_group(), one_group(pos_mean=1.5), one_group(pos_mean=1.5)], N, seed=4)
    assert _row(rows, "static", 1)["fpr"] == pytest.approx(0.05, abs=0.002)
    assert _row(rows, "static", 1)["tpr"] < _row(rows, "static", 0)["tpr"] - 0.05
    # The oracle cannot recover TPR either: the negatives did not move.
    assert _row(rows, "oracle", 1)["tpr"] == pytest.approx(_row(rows, "static", 1)["tpr"], abs=0.02)


def test_prevalence_shift_pushes_top_fraction_under_budget():
    rows = run_scenario([one_group(), one_group(prevalence=0.04), one_group(prevalence=0.04)], N, seed=5)
    assert _row(rows, "static", 1)["fpr"] == pytest.approx(0.05, abs=0.002)
    assert _row(rows, "label_free_top", 1)["fpr"] < _row(rows, "label_free_top", 0)["fpr"] - 0.005


def test_delayed_lag1_equals_static_in_first_shifted_month():
    rows = run_scenario([one_group(), one_group(neg_mean=0.5), one_group(neg_mean=0.5)], N, seed=6)
    assert _row(rows, "delayed_lag1", 1)["fpr"] == _row(rows, "static", 1)["fpr"]


def test_oracle_is_on_budget_every_month():
    rows = run_scenario([one_group(), one_group(neg_mean=0.5, prevalence=0.03)], N, seed=7)
    for m in (0, 1):
        assert _row(rows, "oracle", m)["fpr"] <= 0.05
        assert _row(rows, "oracle", m)["fpr"] == pytest.approx(0.05, abs=1e-4)
