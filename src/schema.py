"""Column layout of the results files. Evaluation writes these; tables read them.

results/metrics.csv  one row per KEYS + seed: point estimates on the full month.
results/summary.csv  one row per KEYS + metric: seed mean, sd (ddof=1), min, max.
results/ci.csv       one row per KEYS + seed + metric: bootstrap 95% interval.
results/paired.csv   one row per KEYS + seed + comparator + metric: paired bootstrap
                     interval of (strategy - comparator) and the PROTOCOL.md verdict.
"""

VARIANTS = ["Base", "Variant I", "Variant II", "Variant III", "Variant IV", "Variant V"]
MODELS = ["lightgbm", "logreg"]
PRIMARY_MODEL = "lightgbm"
PRIMARY_TARGET = 0.05
EXPLORATORY_TARGETS = [0.01, 0.02, 0.10]
PRIMARY_AGE = ">=50"  # final choice recorded in PROTOCOL.md decision log
TEST_MONTHS = [4, 5, 6, 7]
VALIDATION_MONTH = 3

PRIMARY_STRATEGIES = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "oracle"]
DELAY_STRATEGIES = ["delayed_lag1", "delayed_lag2", "delayed_lag3"]
DEPLOYABLE = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "delayed_lag2", "delayed_lag3"]

KEYS = ["variant", "model", "fpr_target", "age_def", "strategy", "month"]

METRICS = [
    "realized_fpr",
    "budget_miss",
    "abs_budget_miss",
    "tpr",
    "alert_rate",
    "precision",
    "fpr_young",
    "fpr_old",
    "fpr_ratio",
    "tpr_young",
    "tpr_old",
    "alert_share_old",
    "application_share_old",
    "alert_share_young",
    "application_share_young",
]
COUNTS = ["n_pos_young", "n_neg_young", "n_pos_old", "n_neg_old"]
# metrics.csv also carries: seed, available (bool), threshold, source_month,
# small_cell_young, small_cell_old (bool, fewer than 30 positives).

# Metrics that get bootstrap intervals and paired comparisons.
CI_METRICS = ["realized_fpr", "budget_miss", "abs_budget_miss", "tpr", "alert_rate", "precision", "fpr_ratio", "tpr_young", "tpr_old"]
PAIRED_METRICS = ["abs_budget_miss", "tpr", "fpr_ratio"]
