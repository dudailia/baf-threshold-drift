import numpy as np
import pytest

from src.fastboot import AGE_BINS, evaluate_months, resample_weights
from src.metrics import confusion, fpr_ratio, rates
from src.thresholds import flag, threshold_at_fpr, threshold_top_fraction

TARGETS = [0.05, 0.10]


def _month(rng, n, shift=0.0):
    y = (rng.random(n) < 0.05).astype(int)
    age = rng.choice([20, 30, 40, 50, 60, 70], size=n, p=[0.3, 0.25, 0.2, 0.1, 0.1, 0.05])
    s = np.round(rng.normal(1.5 * y + 0.2 * (age >= 50) + shift, 1.0), 2)  # rounding creates ties
    return s, y, age


@pytest.fixture
def months():
    rng = np.random.default_rng(0)
    return {m: _month(rng, 3000, shift=0.3 * (m >= 6)) for m in range(3, 8)}


def _old(age, definition):
    return age >= 50 if definition == ">=50" else age > 50


def _expected(months, strategy, m, target, definition):
    s, y, age = months[m]
    sv, yv, av = months[3]
    if strategy == "static":
        t = threshold_at_fpr(sv, yv, target)
    elif strategy == "label_free_top":
        t = threshold_top_fraction(s, target)
    elif strategy == "label_free_val_rate":
        rate = flag(sv, threshold_at_fpr(sv, yv, target)).mean()
        t = threshold_top_fraction(s, rate)
    elif strategy.startswith("delayed_lag"):
        src = m - int(strategy[-1])
        t = threshold_at_fpr(months[src][0], months[src][1], target)
    elif strategy == "oracle":
        t = threshold_at_fpr(s, y, target)
    elif strategy in ("groupwise_static", "groupwise_label_free"):
        old_dec = _old(age, ">=50")
        t = np.empty(s.size)
        for g in (False, True):
            if strategy == "groupwise_static":
                mv = _old(av, ">=50") == g
                t[old_dec == g] = threshold_at_fpr(sv[mv], yv[mv], target)
            else:
                t[old_dec == g] = threshold_top_fraction(s[old_dec == g], target)
    pred = s >= t
    old = _old(age, definition)
    c = rates(confusion(pred.astype(float), y, 0.5))
    fy = rates(confusion(pred[~old].astype(float), y[~old], 0.5))["fpr"]
    fo = rates(confusion(pred[old].astype(float), y[old], 0.5))["fpr"]
    return dict(realized_fpr=c["fpr"], tpr=c["tpr"], alert_rate=c["alert_rate"], precision=c["precision"],
                fpr_young=fy, fpr_old=fo, fpr_ratio=fpr_ratio(fy, fo),
                alert_share_old=pred[old].sum() / pred.sum())


STRATS = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "delayed_lag2", "delayed_lag3", "oracle",
          "groupwise_static", "groupwise_label_free"]


def test_point_estimates_match_simple_functions(months):
    point, _ = evaluate_months(months, TARGETS, primary_age=">=50", n_boot=0)
    for r in point:
        if not r["available"]:
            continue
        exp = _expected(months, r["strategy"], r["month"], r["fpr_target"], r["age_def"])
        for k, v in exp.items():
            assert r[k] == pytest.approx(v, abs=1e-12, nan_ok=True), (r["strategy"], r["month"], k)


def test_every_strategy_target_age_and_month_present(months):
    point, _ = evaluate_months(months, TARGETS, primary_age=">=50", n_boot=0)
    keys = {(r["strategy"], r["month"], r["fpr_target"], r["age_def"]) for r in point}
    assert len(keys) == len(STRATS) * 4 * len(TARGETS) * 2 == len(point)


def test_delayed_cells_using_training_months_are_not_available(months):
    point, _ = evaluate_months(months, TARGETS, primary_age=">=50", n_boot=0)
    na = {(r["strategy"], r["month"]) for r in point if not r["available"]}
    assert na == {("delayed_lag2", 4), ("delayed_lag3", 4), ("delayed_lag3", 5)}
    src = {(r["strategy"], r["month"]): r["source_month"] for r in point if r["fpr_target"] == 0.05 and r["age_def"] == ">=50"}
    assert src[("delayed_lag1", 4)] == 3 and src[("delayed_lag3", 7)] == 4


def test_oracle_never_beaten_by_single_threshold_strategy_within_budget(months):
    point, boot = evaluate_months(months, [0.05], primary_age=">=50", n_boot=50, weight_seed=("v", 0))
    single = [s for s in STRATS if not s.startswith("groupwise")]
    for key, arr in boot.items():
        strategy, m, f, age = key
        if strategy not in single or age != ">=50":
            continue
        ora = boot[("oracle", m, f, age)]
        within = arr["realized_fpr"] <= f + 1e-12
        assert np.all(arr["tpr"][within] <= ora["tpr"][within] + 1e-12)
        assert np.all(ora["realized_fpr"] <= f + 1e-12)


def test_integer_weights_equal_duplicated_rows():
    rng = np.random.default_rng(3)
    base = {m: _month(rng, 500) for m in range(3, 8)}
    w = {m: rng.integers(0, 3, size=500) for m in base}
    dup = {m: tuple(np.repeat(a, w[m]) for a in base[m]) for m in base}
    p_dup, _ = evaluate_months(dup, [0.05], primary_age=">=50", n_boot=0)
    p_w, _ = evaluate_months(base, [0.05], primary_age=">=50", n_boot=0, weights={m: w[m][None, :] for m in base})
    for a, b in zip(p_dup, p_w):
        assert a["strategy"] == b["strategy"] and a["month"] == b["month"]
        assert a["tpr"] == pytest.approx(b["tpr"], nan_ok=True)
        assert a["realized_fpr"] == pytest.approx(b["realized_fpr"], nan_ok=True)


def test_resample_weights_are_deterministic_and_sum_to_n():
    a = resample_weights(1000, 20, ("Base", 4, 0))
    b = resample_weights(1000, 20, ("Base", 4, 0))
    c = resample_weights(1000, 20, ("Base", 5, 0))
    assert (a == b).all() and not (a == c).all()
    assert (a.sum(axis=1) == 1000).all()


def test_bootstrap_intervals_cover_point_estimate(months):
    point, boot = evaluate_months(months, [0.05], primary_age=">=50", n_boot=200, weight_seed=("v", 0))
    r = next(r for r in point if r["strategy"] == "static" and r["month"] == 7 and r["age_def"] == ">=50")
    lo, hi = np.percentile(boot[("static", 7, 0.05, ">=50")]["tpr"], [2.5, 97.5])
    assert lo <= r["tpr"] <= hi


def test_age_bins_cover_decades():
    assert AGE_BINS(np.array([10, 40, 50, 60, 90])).tolist() == [0, 0, 1, 2, 2]
