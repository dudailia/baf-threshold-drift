"""Confusion-matrix metrics, group fairness, and feature drift (PSI)."""

import numpy as np
from sklearn import metrics as skm

from src.thresholds import flag

# Proportion floor for empty PSI bins, so the log term stays finite.
_PSI_FLOOR = 1e-4


def confusion(scores, labels, t, weights=None):
    pred = flag(scores, t)
    y = np.asarray(labels) == 1
    w = np.ones(pred.shape) if weights is None else np.asarray(weights, dtype=float)
    return dict(
        tp=w[pred & y].sum(),
        fp=w[pred & ~y].sum(),
        tn=w[~pred & ~y].sum(),
        fn=w[~pred & y].sum(),
    )


def _div(a, b):
    return a / b if b > 0 else np.nan


def rates(c):
    n = c["tp"] + c["fp"] + c["tn"] + c["fn"]
    return dict(
        tpr=_div(c["tp"], c["tp"] + c["fn"]),
        fpr=_div(c["fp"], c["fp"] + c["tn"]),
        precision=_div(c["tp"], c["tp"] + c["fp"]),
        alert_rate=_div(c["tp"] + c["fp"], n),
    )


def fpr_ratio(fpr_a, fpr_b):
    """Predictive equality: lowest group FPR divided by highest (Jesus et al. 2022, Sec 3.2)."""
    lo, hi = min(fpr_a, fpr_b), max(fpr_a, fpr_b)
    return _div(lo, hi)


def group_report(scores, labels, groups, t, min_positives=30):
    """Per-group counts and rates at threshold t, plus each group's share of alerts and applications."""
    scores, labels, groups = np.asarray(scores), np.asarray(labels), np.asarray(groups)
    alerts = flag(scores, t)
    total_alerts = alerts.sum()
    out = {}
    for g in np.unique(groups):
        m = groups == g
        c = confusion(scores[m], labels[m], t)
        r = rates(c)
        n_pos = int(c["tp"] + c["fn"])
        out[g] = dict(
            n_pos=n_pos,
            n_neg=int(c["fp"] + c["tn"]),
            tpr=r["tpr"],
            fpr=r["fpr"],
            precision=r["precision"],
            alert_share=_div(alerts[m].sum(), total_alerts),
            application_share=m.mean(),
            small_cell=bool(n_pos < min_positives),
        )
    return out


def _proportions(codes, n_codes):
    p = np.bincount(codes, minlength=n_codes) / codes.size
    return np.maximum(p, _PSI_FLOOR)


def psi(reference, current, n_bins=10, categorical=False):
    """Population stability index of ``current`` against ``reference``.

    Numeric features use reference quantile bins, with missing values as their
    own bin. Features with at most ``n_bins`` distinct reference values, and
    categorical features, use one bin per value.
    """
    ref, cur = np.asarray(reference), np.asarray(current)
    if not categorical:
        ref, cur = ref.astype(float), cur.astype(float)
        ref_vals = np.unique(ref[~np.isnan(ref)])
        categorical = ref_vals.size <= n_bins
    if categorical:
        cats = np.unique(np.r_[ref.astype(str), cur.astype(str)])
        ref_codes = np.searchsorted(cats, ref.astype(str))
        cur_codes = np.searchsorted(cats, cur.astype(str))
        n_codes = cats.size
    else:
        edges = np.unique(np.quantile(ref[~np.isnan(ref)], np.linspace(0, 1, n_bins + 1)[1:-1]))

        def codes(x):
            c = np.searchsorted(edges, x, side="right")
            c[np.isnan(x)] = edges.size + 1
            return c

        ref_codes, cur_codes = codes(ref), codes(cur)
        n_codes = edges.size + 2
    p, q = _proportions(ref_codes, n_codes), _proportions(cur_codes, n_codes)
    return float(np.sum((q - p) * np.log(q / p)))


def notebook_operating_point(scores, labels):
    """Threshold rule of the BAF empirical results notebook (cell 10), for replication only.

    Picks the ROC point with the largest FPR strictly below 0.05 on the given
    labelled data and returns (threshold, TPR at that ROC point). The notebook
    binarizes with ``score > threshold``.
    """
    fprs, tprs, thresholds = skm.roc_curve(labels, scores)
    best = fprs == fprs[fprs < 0.05].max()
    return float(np.min(thresholds[best])), float(np.max(tprs[best]))
