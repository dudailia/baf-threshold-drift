"""Decision thresholds.

Every strategy flags an application when ``score >= t``. A threshold is chosen
so that the flagged set is the largest one that keeps a weighted count under a
budget: the negatives' weight for an FPR target, all applications' weight for an
alert-share target. Tied scores are never split, so the realized rate can fall
below the target but never above it.
"""

import numpy as np

# Absorbs floating-point error in budget * total (for example 0.05 * 100).
_EPS = 1e-9


def flag(scores, t):
    return np.asarray(scores) >= t


def _threshold_for_budget(scores, weights, budget):
    """Smallest t such that the weight of {scores >= t} is at most ``budget``."""
    scores = np.asarray(scores, dtype=float)
    weights = np.ones_like(scores) if weights is None else np.asarray(weights, dtype=float)
    keep = weights > 0
    scores, weights = scores[keep], weights[keep]
    if budget + _EPS >= weights.sum():
        return -np.inf
    values, inverse = np.unique(scores, return_inverse=True)
    value_weights = np.bincount(inverse, weights=weights)
    # Walk distinct values from the top; stop at the first that breaks the budget.
    cum = np.cumsum(value_weights[::-1])
    first_over = np.searchsorted(cum, budget + _EPS, side="right")
    boundary = values[::-1][first_over]
    return np.nextafter(boundary, np.inf)


def threshold_at_fpr(scores, labels, target_fpr, weights=None):
    """Threshold whose FPR on the given labelled data is as large as possible but <= target."""
    scores = np.asarray(scores, dtype=float)
    neg = np.asarray(labels) == 0
    w = np.ones(scores.shape) if weights is None else np.asarray(weights, dtype=float)
    return _threshold_for_budget(scores[neg], w[neg], target_fpr * w[neg].sum())


def threshold_top_fraction(scores, fraction, weights=None):
    """Label-free threshold flagging at most ``fraction`` of applications."""
    scores = np.asarray(scores, dtype=float)
    w = np.ones(scores.shape) if weights is None else np.asarray(weights, dtype=float)
    return _threshold_for_budget(scores, w, fraction * w.sum())
