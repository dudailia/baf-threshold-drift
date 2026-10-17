import pandas as pd

from src.predictions_eval import score

VARIANTS = ["Base", "Variant I", "Variant II", "Variant III", "Variant IV", "Variant V"]
STRATS = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "oracle"]


def _build(overrides=None):
    """All predictions hit by construction; overrides {(variant, strategy, month, metric): value} break one."""
    base = dict(realized_fpr=0.050, budget_miss=0.0, tpr=0.50, fpr_ratio=0.30, alert_share_old=0.70, alert_share_young=0.30)
    rows = []
    for v in VARIANTS:
        for s in STRATS:
            for m in (4, 5, 6, 7):
                vals = dict(base)
                if s == "label_free_top":
                    vals.update(realized_fpr=0.044, budget_miss=-0.006, tpr=0.49, fpr_ratio=0.31)
                if s == "static":
                    vals.update(realized_fpr=0.051, budget_miss=0.001, tpr=0.505)
                if v in ("Variant IV", "Variant V") and m in (6, 7):
                    vals["tpr"] -= 0.10
                for k, x in vals.items():
                    rows.append(dict(variant=v, model="lightgbm", fpr_target=0.05, age_def=">=50", strategy=s, month=m, metric=k, mean=x))
    summary = pd.DataFrame(rows)
    for (v, s, m, k), x in (overrides or {}).items():
        summary.loc[(summary.variant == v) & (summary.strategy == s) & (summary.month == m) & (summary.metric == k), "mean"] = x
    metrics = pd.DataFrame([dict(variant=v, model="lightgbm", fpr_target=0.05, age_def=">=50", seed=0, strategy="static", month=m,
                                 n_pos_young=100, n_neg_young=9900, n_pos_old=300, n_neg_old=9700)
                            for v in VARIANTS for m in (4, 5, 6, 7)])
    return summary, metrics


def _result(df, pid):
    return df.set_index("prediction").loc[pid, "result"]


def test_all_hit_when_constructed_to_hit():
    out = score(*_build())
    assert (out["result"] == "hit").all(), out[out.result == "miss"]


def test_prediction_1_misses_on_a_5_point_gap():
    out = score(*_build({("Variant II", "delayed_lag1", 6, "tpr"): 0.555}))
    assert _result(out, "1") == "miss"


def test_label_free_fpr_band_is_inclusive_of_4_2_and_exclusive_below():
    assert _result(score(*_build({("Base", "label_free_top", 4, "realized_fpr"): 0.042})), "2 (label-free FPR)") == "hit"
    assert _result(score(*_build({("Base", "label_free_top", 4, "realized_fpr"): 0.0419})), "2 (label-free FPR)") == "miss"


def test_prediction_4_misses_when_static_has_largest_budget_miss():
    out = score(*_build({("Variant IV", "static", 7, "budget_miss"): 0.02}))
    assert _result(out, "4") == "miss"


def test_prediction_7_uses_higher_fraud_rate_group_alert_share():
    out = score(*_build({("Variant IV", "label_free_top", 6, "alert_share_old"): 0.60}))
    assert _result(out, "7") == "miss"


def test_prediction_a_misses_when_one_strategy_does_not_lose_tpr():
    out = score(*_build({("Variant IV", "oracle", 6, "tpr"): 0.60, ("Variant IV", "oracle", 7, "tpr"): 0.60}))
    assert _result(out, "A") == "miss"
