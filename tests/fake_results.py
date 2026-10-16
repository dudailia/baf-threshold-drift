"""Writes a small, fake results set in the schema of src/schema.py, for tests only."""

import json
from itertools import product

import numpy as np
import pandas as pd

from src.schema import CI_METRICS, COUNTS, KEYS, METRICS, PAIRED_METRICS

STRATEGIES = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "delayed_lag2", "delayed_lag3", "oracle"]


def write_fake_results(d, variants=("Base", "Variant IV"), seeds=(0, 1), months=(4, 5, 6, 7)):
    rng = np.random.default_rng(0)
    rows = []
    for variant, model, age, strategy, month, seed in product(variants, ["lightgbm", "logreg"], [">=50", ">50"], STRATEGIES, months, seeds):
        lag = int(strategy[-1]) if strategy.startswith("delayed") else None
        source = month - lag if lag else (3 if strategy in ("static", "label_free_val_rate") else month)
        available = source >= 3
        row = dict(variant=variant, model=model, fpr_target=0.05, age_def=age, strategy=strategy, month=month, seed=seed,
                   available=available, threshold=rng.random(), source_month=source)
        for m in METRICS:
            row[m] = rng.uniform(0.01, 0.9) if available else np.nan
        row["budget_miss"] = row["realized_fpr"] - 0.05 if available else np.nan
        row["abs_budget_miss"] = abs(row["budget_miss"]) if available else np.nan
        for c in COUNTS:
            row[c] = int(rng.integers(100, 5000))
        row["n_pos_old"] = 25 if variant == "Variant IV" else 300
        row["small_cell_young"] = row["n_pos_young"] < 30
        row["small_cell_old"] = row["n_pos_old"] < 30
        rows.append(row)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(d / "metrics.csv", index=False)

    avail = metrics[metrics["available"]]
    long = avail.melt(id_vars=KEYS + ["seed"], value_vars=METRICS, var_name="metric")
    summary = long.groupby(KEYS + ["metric"])["value"].agg(mean="mean", sd=lambda x: x.std(ddof=1), min="min", max="max", n_seeds="size").reset_index()
    summary.to_csv(d / "summary.csv", index=False)

    ci = long[long["metric"].isin(CI_METRICS)].rename(columns={"value": "estimate"})
    ci["lo"] = ci["estimate"] - 0.01
    ci["hi"] = ci["estimate"] + 0.01
    ci.to_csv(d / "ci.csv", index=False)

    paired = long[long["metric"].isin(PAIRED_METRICS) & (long["strategy"] != "static")].rename(columns={"value": "diff"}).copy()
    paired["comparator"] = "static"
    paired["lo"] = paired["diff"] - 0.02
    paired["hi"] = paired["diff"] + 0.02
    paired["verdict"] = np.where((paired["lo"] > 0) | (paired["hi"] < 0), "differs", "inconclusive")
    paired.to_csv(d / "paired.csv", index=False)

    (d / "manifest.json").write_text(json.dumps({"text_constants": [0, 1, 2, 3, 4, 5, 6, 7, 30, 50, 95, 1000], "predictions_commit": "fake"}))
    (d / "values.json").write_text(json.dumps({"n_rows": 123}))
    return metrics
