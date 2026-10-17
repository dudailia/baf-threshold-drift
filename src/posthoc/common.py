"""Shared helpers for the post hoc analyses (PROTOCOL.md, "Post hoc analyses").

Outputs go to results_posthoc/ (BAF_POSTHOC_OUT overrides it for tests). Nothing
here writes to results/. Bootstrap resamples use the main study's weight keys, so
post hoc and main strategies are evaluated on the same resampled rows of a month.
"""

import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.data import LABEL
from src.fastboot import evaluate_months
from src.guard import predictions_commit

OUT = Path(os.environ.get("BAF_POSTHOC_OUT", config.ROOT / "results_posthoc"))
PRED = OUT / "predictions"
CKPT = OUT / "checkpoints"
LOGS = OUT / "logs"
MAIN_RESULTS_COMMIT = "125042c"  # main results seen before these analyses were declared
TARGET = 0.05
AGE = ">=50"
CI_METRICS = ["realized_fpr", "budget_miss", "abs_budget_miss", "tpr", "fpr_ratio", "alert_rate"]


def log(msg, name="posthoc"):
    LOGS.mkdir(parents=True, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOGS / f"{name}.log", "a") as f:
        f.write(line + "\n")


def stamp(df, commit):
    df = df.copy()
    df.insert(0, "main_results_commit", MAIN_RESULTS_COMMIT)
    df.insert(0, "predictions_commit", commit)
    return df


def save_pred(path, frame, scores, meta):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, row=frame.index.to_numpy(), month=frame["month"].to_numpy(), label=frame[LABEL].to_numpy(),
                        age=frame["customer_age"].to_numpy(), score=scores)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1, default=str))


def load_months(path):
    z = np.load(path)
    return {int(m): (z["score"][z["month"] == m], z["label"][z["month"] == m], z["age"][z["month"] == m]) for m in np.unique(z["month"])}


def evaluate(months, variant, validation_month, strategies, n_boot):
    """Point rows and seed-level boot arrays for the given strategies at the 5% target, primary age."""
    point, boot = evaluate_months(months, [TARGET], AGE, n_boot=n_boot, weight_seed=(variant,), validation_month=validation_month)
    point = [r for r in point if r["strategy"] in strategies and r["age_def"] == AGE]
    boot = {(k[0], k[1]): v for k, v in boot.items() if k[0] in strategies and k[3] == AGE}
    return point, boot


def ci_rows(point, boot, base):
    rows = []
    for r in point:
        arr = boot.get((r["strategy"], r["month"]))
        if arr is None:
            continue
        for metric in CI_METRICS:
            lo, hi = np.nanpercentile(arr[metric], [2.5, 97.5])
            rows.append({**base, "strategy": r["strategy"], "month": r["month"], "metric": metric, "estimate": r[metric], "lo": lo, "hi": hi})
    return rows


def summarize(metrics, keys):
    m = metrics[metrics["available"].astype(bool)]
    long = m.melt(id_vars=keys + ["seed"], value_vars=CI_METRICS, var_name="metric")
    g = long.groupby(keys + ["metric"])["value"]
    return g.agg(mean="mean", sd=lambda x: x.std(ddof=1) if len(x) > 1 else 0.0, min="min", max="max", n_seeds="size").reset_index()


def commit():
    return predictions_commit()


def write(df, name):
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{name}.csv", index=False)


MAIN_STRATEGIES = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "oracle"]


def main_pred_path(variant, seed=0, model="lightgbm"):
    return config.PREDICTIONS_DIR / variant / f"{model}_seed{seed}.npz"


def main_boot(variant, n_boot):
    """Main-study seed 0 LightGBM bootstrap arrays, recomputed in memory from saved predictions
    with the main study's resample keys (identical draws), cached under results_posthoc/checkpoints/."""
    path = CKPT / "main_boot" / f"{variant}.npz"
    if path.exists():
        z = np.load(path, allow_pickle=True)
        return z["point"].item(), z["boot"].item()
    pt, bt = evaluate(load_months(main_pred_path(variant)), variant, 3, MAIN_STRATEGIES, n_boot)
    point = {(r["strategy"], r["month"]): r for r in pt}
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, point=np.array(point, dtype=object), boot=np.array(bt, dtype=object))
    return point, bt


def paired(a_point, a_arr, c_point, c_arr, metric, base):
    """Paired difference a - c with the PROTOCOL.md verdict (same resampled rows for both)."""
    from src.trace import verdict

    d = a_arr[metric] - c_arr[metric]
    lo, hi = np.nanpercentile(d, [2.5, 97.5])
    ma = tuple(np.nanpercentile(a_arr[metric], [2.5, 97.5]))
    mc = tuple(np.nanpercentile(c_arr[metric], [2.5, 97.5]))
    return {**base, "metric": metric, "diff": a_point[metric] - c_point[metric], "lo": lo, "hi": hi, "verdict": verdict((lo, hi), ma, mc)}
