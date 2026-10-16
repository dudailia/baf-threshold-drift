import numpy as np
import pytest

from src.metrics import (
    confusion,
    fpr_ratio,
    group_report,
    notebook_operating_point,
    psi,
    rates,
)


def test_confusion_counts_on_hand_example():
    scores = np.array([0.9, 0.8, 0.7, 0.4, 0.3, 0.2])
    labels = np.array([1, 0, 1, 0, 1, 0])
    c = confusion(scores, labels, 0.5)
    assert (c["tp"], c["fp"], c["tn"], c["fn"]) == (2, 1, 2, 1)


def test_rates_on_hand_example():
    r = rates(dict(tp=2, fp=1, tn=2, fn=1))
    assert r["tpr"] == pytest.approx(2 / 3)
    assert r["fpr"] == pytest.approx(1 / 3)
    assert r["precision"] == pytest.approx(2 / 3)
    assert r["alert_rate"] == pytest.approx(3 / 6)


def test_rates_are_nan_when_denominator_is_zero():
    r = rates(dict(tp=0, fp=0, tn=5, fn=0))
    assert np.isnan(r["tpr"]) and np.isnan(r["precision"])
    assert r["fpr"] == 0.0


def test_confusion_with_weights_equals_duplicated_rows():
    scores = np.array([0.9, 0.8, 0.7, 0.4])
    labels = np.array([1, 0, 1, 0])
    w = np.array([2, 0, 3, 1])
    c = confusion(scores, labels, 0.5, weights=w)
    assert (c["tp"], c["fp"], c["tn"], c["fn"]) == (5, 0, 1, 0)


def test_fpr_ratio_is_lowest_over_highest_in_either_order():
    assert fpr_ratio(0.02, 0.08) == pytest.approx(0.25)
    assert fpr_ratio(0.08, 0.02) == pytest.approx(0.25)
    assert fpr_ratio(0.05, 0.05) == 1.0


def test_fpr_ratio_undefined_when_both_zero():
    assert np.isnan(fpr_ratio(0.0, 0.0))
    assert fpr_ratio(0.0, 0.1) == 0.0


def test_group_report_counts_rates_and_shares():
    # Group A: 4 negatives, 2 positives. Group B: 2 negatives, 2 positives.
    scores = np.array([0.9, 0.1, 0.8, 0.2, 0.3, 0.6, 0.7, 0.9, 0.1, 0.4])
    labels = np.array([0, 0, 0, 0, 1, 1, 0, 1, 1, 0])
    groups = np.array(["A"] * 6 + ["B"] * 4)
    rep = group_report(scores, labels, groups, 0.5, min_positives=30)
    a, b = rep["A"], rep["B"]
    assert (a["n_pos"], a["n_neg"], b["n_pos"], b["n_neg"]) == (2, 4, 2, 2)
    assert a["fpr"] == pytest.approx(2 / 4)
    assert a["tpr"] == pytest.approx(1 / 2)
    assert b["fpr"] == pytest.approx(1 / 2)
    assert b["tpr"] == pytest.approx(1 / 2)
    # Alerts: A flags 0.9, 0.8, 0.6 (3); B flags 0.7, 0.9 (2).
    assert a["alert_share"] == pytest.approx(3 / 5)
    assert a["application_share"] == pytest.approx(6 / 10)
    assert a["small_cell"] and b["small_cell"]


def test_group_report_small_cell_flag_uses_positive_count():
    labels = np.r_[np.ones(30), np.zeros(10), np.ones(29), np.zeros(10)].astype(int)
    groups = np.array(["A"] * 40 + ["B"] * 39)
    scores = np.zeros(labels.size)
    rep = group_report(scores, labels, groups, 0.5, min_positives=30)
    assert rep["A"]["small_cell"] is False
    assert rep["B"]["small_cell"] is True


def test_psi_zero_for_identical_distributions():
    x = np.random.default_rng(0).normal(size=5000)
    assert psi(x, x) == pytest.approx(0.0, abs=1e-12)


def test_psi_known_two_bin_value():
    # Categorical reference split 50/50, current 25/75.
    ref = np.array(["a"] * 50 + ["b"] * 50)
    cur = np.array(["a"] * 25 + ["b"] * 75)
    expected = (0.25 - 0.5) * np.log(0.25 / 0.5) + (0.75 - 0.5) * np.log(0.75 / 0.5)
    assert psi(ref, cur, categorical=True) == pytest.approx(expected)


def test_psi_treats_nan_as_its_own_bin():
    ref = np.r_[np.arange(100.0), np.full(100, np.nan)]
    cur = np.arange(100.0)
    # Reference is half missing, current has no missing values: PSI must be large.
    assert psi(ref, cur) > 0.5


def test_notebook_operating_point_matches_roc_rule():
    # Negatives 0..99, positives at 50.5 and 200. The notebook picks the ROC
    # point with the largest FPR strictly below 0.05 and reports its TPR.
    scores = np.r_[np.arange(100.0), 50.5, 200.0]
    labels = np.r_[np.zeros(100), 1, 1].astype(int)
    t, tpr = notebook_operating_point(scores, labels)
    assert tpr == pytest.approx(0.5)
    # Binarized with ">" as in the notebook, at most 4 negatives are flagged.
    assert (scores[labels == 0] > t).sum() <= 4
