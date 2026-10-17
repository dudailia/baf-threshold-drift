import numpy as np

from src.posthoc.isotonic import _point


def _month(rng, n):
    s = rng.normal(size=n)
    p = 1 / (1 + np.exp(-(3 * s - 5)))  # true fraud probability, about 2% overall
    y = (rng.random(n) < p).astype(int)
    return s, y, rng.choice([20, 30, 60], n)


def test_isotonic_targeting_hits_budget_without_drift():
    rng = np.random.default_rng(0)
    months = {m: _month(rng, 200_000) for m in range(3, 8)}
    for r in _point(months):
        assert r["estimated_fpr"] <= 0.05 + 1e-9
        assert abs(r["realized_fpr"] - 0.05) < 0.003


def test_isotonic_targeting_flags_by_score_order():
    rng = np.random.default_rng(1)
    months = {m: _month(rng, 50_000) for m in range(3, 8)}
    r = _point(months)[0]
    s, y, _ = months[4]
    assert ((s >= r["threshold"]).mean() - r["alert_rate"]) == 0
