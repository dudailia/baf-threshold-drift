"""Evaluate every strategy from saved predictions: point estimates, paired bootstrap, aggregation, tripwires.

Checkpoints one result set per (variant, model, seed) under results/checkpoints/eval/.
Writes results/metrics.csv, summary.csv, ci.csv, paired.csv, tripwires.json and
manifest.json, each stamped with the PREDICTIONS.md commit hash.

Run with: python -m src.evaluate
"""

import json
import platform
import sys
import time
from importlib.metadata import version

import numpy as np
import pandas as pd

from src import config
from src.data import VARIANT_FILES
from src.fastboot import evaluate_months
from src.guard import predictions_commit
from src.schema import CI_METRICS, EXPLORATORY_TARGETS, KEYS, METRICS, PAIRED_METRICS, PRIMARY_AGE, PRIMARY_TARGET
from src.trace import verdict
from src.train import log, pred_path

MODELS = ["lightgbm", "logreg"]
MIN_POSITIVES = 30  # PROTOCOL.md: cells with fewer positives are flagged
TARGETS = [PRIMARY_TARGET] + EXPLORATORY_TARGETS
SINGLE_THRESHOLD = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "delayed_lag2", "delayed_lag3"]
PAIRS = (
    [(s, "static") for s in ["label_free_top", "label_free_val_rate", "delayed_lag1", "delayed_lag2", "delayed_lag3",
                             "oracle", "groupwise_static", "groupwise_label_free"]]
    + [("label_free_top", "delayed_lag1"), ("label_free_val_rate", "delayed_lag1"), ("label_free_top", "label_free_val_rate")]
    + [(s, "oracle") for s in ["label_free_top", "label_free_val_rate", "delayed_lag1"]]
)
# Text constants allowed in the write-up templates (months, seeds, lags, targets, protocol sizes, citations).
TEXT_CONSTANTS = list(range(0, 11)) + [30, 50, 95, 100, 1000, 2000, 2022, 2026, 25, 75, 5, 20, 15, 16, 3.1, 3.2, 3.4, 4.2, 4.3,
                                      2211.13358, 2206.13183, 0.05, 2.5, 97.5, 1.5, 0.85, 0.02, 0.75, 0.25, 0.9, 0.5, 0.55, 40, 60, 0.85]


def variants():
    return config.VARIANT_SUBSET or list(VARIANT_FILES)


def _load_months(path):
    z = np.load(path)
    return {int(m): (z["score"][z["month"] == m], z["label"][z["month"] == m], z["age"][z["month"] == m]) for m in np.unique(z["month"])}


def _lr_seeds_identical(variant):
    ref = np.load(pred_path(variant, "logreg", config.SEEDS[0]))["score"]
    return all(np.array_equal(ref, np.load(pred_path(variant, "logreg", s))["score"]) for s in config.SEEDS[1:])


def evaluate_one(variant, model, seed, n_boot):
    ckpt = config.CHECKPOINTS / "eval" / f"{variant}__{model}__seed{seed}.npz"
    if ckpt.exists():
        z = np.load(ckpt, allow_pickle=True)
        return pd.DataFrame(list(z["point"])), pd.DataFrame(list(z["ci"])), pd.DataFrame(list(z["paired"]))
    months = _load_months(pred_path(variant, model, seed))
    t0 = time.time()
    point, boot = evaluate_months(months, TARGETS, PRIMARY_AGE, n_boot=n_boot, weight_seed=(variant,), boot_targets=[PRIMARY_TARGET])
    base = dict(variant=variant, model=model, seed=seed)
    point = pd.DataFrame([{**base, **r} for r in point])
    ci_rows, paired_rows = [], []
    marg = {}
    for (strategy, m, f, age), arr in boot.items():
        for metric in CI_METRICS:
            v = arr[metric]
            lo, hi = np.nanpercentile(v, [2.5, 97.5]) if np.isfinite(v).any() else (np.nan, np.nan)
            est = point.loc[(point.strategy == strategy) & (point.month == m) & np.isclose(point.fpr_target, f) & (point.age_def == age), metric].iloc[0]
            ci_rows.append({**base, "fpr_target": f, "age_def": age, "strategy": strategy, "month": m, "metric": metric,
                            "estimate": est, "lo": lo, "hi": hi, "n_resamples": int(np.isfinite(v).sum())})
            marg[(strategy, m, f, age, metric)] = (lo, hi)
    for a, c in PAIRS:
        for (strategy, m, f, age), arr in boot.items():
            if strategy != a or (c, m, f, age) not in boot:
                continue
            for metric in PAIRED_METRICS:
                d = arr[metric] - boot[(c, m, f, age)][metric]
                if not np.isfinite(d).any():
                    continue
                lo, hi = np.nanpercentile(d, [2.5, 97.5])
                pa = point.loc[(point.strategy == a) & (point.month == m) & np.isclose(point.fpr_target, f) & (point.age_def == age), metric].iloc[0]
                pc = point.loc[(point.strategy == c) & (point.month == m) & np.isclose(point.fpr_target, f) & (point.age_def == age), metric].iloc[0]
                paired_rows.append({**base, "fpr_target": f, "age_def": age, "strategy": a, "comparator": c, "month": m,
                                    "metric": metric, "diff": pa - pc, "lo": lo, "hi": hi,
                                    "verdict": verdict((lo, hi), marg[(a, m, f, age, metric)], marg[(c, m, f, age, metric)])})
    ci, paired = pd.DataFrame(ci_rows), pd.DataFrame(paired_rows)
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    np.savez(ckpt, point=np.array(point.to_dict("records"), dtype=object), ci=np.array(ci.to_dict("records"), dtype=object),
             paired=np.array(paired.to_dict("records"), dtype=object))
    log(f"evaluated {variant} {model} seed {seed} ({time.time() - t0:.0f}s, {n_boot} resamples)")
    return point, ci, paired


def summarize(metrics):
    avail = metrics[metrics["available"].astype(bool)]
    long = avail.melt(id_vars=KEYS + ["seed"], value_vars=METRICS, var_name="metric")
    g = long.groupby(KEYS + ["metric"])["value"]
    return g.agg(mean="mean", sd=lambda x: x.std(ddof=1) if len(x) > 1 else 0.0, min="min", max="max", n_seeds="size").reset_index()


def tripwires(metrics):
    """Single-threshold strategy within budget with TPR above the oracle's on the same month (impossible by construction),
    oracle over budget, and implausibly high TPR. Group-wise strategies use a different decision rule and are excluded."""
    fired = []
    m = metrics[metrics["available"].astype(bool)]
    key = ["variant", "model", "seed", "fpr_target", "age_def", "month"]
    ora = m[m.strategy == "oracle"].set_index(key)
    for r in m[m.strategy.isin(SINGLE_THRESHOLD)].itertuples():
        o = ora.loc[(r.variant, r.model, r.seed, r.fpr_target, r.age_def, r.month)]
        if r.realized_fpr <= r.fpr_target + 1e-12 and r.tpr > o.tpr + 1e-12:
            fired.append(f"{r.variant} {r.model} seed {r.seed} {r.strategy} month {r.month} target {r.fpr_target}: TPR {r.tpr:.4f} above oracle {o.tpr:.4f} within budget")
    for r in ora.reset_index().itertuples():
        if r.realized_fpr > r.fpr_target + 1e-12:
            fired.append(f"oracle over budget: {r.variant} {r.model} seed {r.seed} month {r.month}")
    hi = m[(m.strategy == "oracle") & np.isclose(m.fpr_target, PRIMARY_TARGET) & (m.tpr > 0.9)]
    for r in hi.itertuples():
        fired.append(f"too good to be true: oracle TPR {r.tpr:.3f} at 5% FPR, {r.variant} {r.model} seed {r.seed} month {r.month}")
    return sorted(set(fired))


def manifest(commit, extra=None):
    pkgs = {p: version(p) for p in ["numpy", "pandas", "scikit-learn", "lightgbm", "scipy", "matplotlib"]}
    return dict(predictions_commit=commit, generated=time.strftime("%Y-%m-%d %H:%M:%S"), python=platform.python_version(),
                packages=pkgs, n_trials=config.N_TRIALS, seeds=config.SEEDS, n_boot=config.N_BOOT,
                sample_fraction=config.SAMPLE_FRACTION, primary_age=PRIMARY_AGE, targets=TARGETS,
                text_constants=TEXT_CONSTANTS, **(extra or {}))


def main():
    commit = predictions_commit()
    log(f"evaluate start: variants={variants()} n_boot={config.N_BOOT} predictions_commit={commit}")
    parts = {"metrics": [], "ci": [], "paired": []}
    lr_identical = {}
    for v in variants():
        lr_identical[v] = _lr_seeds_identical(v)
        for model in MODELS:
            for seed in config.SEEDS:
                n_boot = config.N_BOOT
                if model == "logreg" and lr_identical[v] and seed != config.SEEDS[0]:
                    n_boot = 0  # identical scores to seed 0, so identical intervals; computed once
                p, c, pr = evaluate_one(v, model, seed, n_boot)
                parts["metrics"].append(p)
                parts["ci"].append(c)
                parts["paired"].append(pr)
    out = {k: pd.concat([d for d in v if len(d)], ignore_index=True) for k, v in parts.items()}
    for g in ("young", "old"):
        out["metrics"][f"small_cell_{g}"] = out["metrics"][f"n_pos_{g}"] < MIN_POSITIVES
    out["summary"] = summarize(out["metrics"])
    fired = tripwires(out["metrics"])
    c = out["ci"]
    outside = c[(c.estimate < c.lo) | (c.estimate > c.hi)]
    diag = dict(ci_rows=len(c), ci_rows_estimate_outside_interval=len(outside))
    config.RESULTS.mkdir(parents=True, exist_ok=True)
    for name, df in out.items():
        df.insert(0, "predictions_commit", commit)
        df.to_csv(config.RESULTS / f"{name}.csv", index=False)
    tw_path = config.RESULTS / "tripwires.json"
    tw = json.loads(tw_path.read_text()) if tw_path.exists() else {}
    tw.update(predictions_commit=commit, evaluation=fired)
    tw_path.write_text(json.dumps(tw, indent=1))
    man_path = config.RESULTS / "manifest.json"
    old = json.loads(man_path.read_text()) if man_path.exists() else {}
    man_path.write_text(json.dumps({**old, **manifest(commit, dict(logreg_seeds_identical=lr_identical, bootstrap_diagnostics=diag))}, indent=1))
    log(f"evaluate done: {len(out['metrics'])} metric rows, tripwires fired: {len(fired)}")
    for f in fired:
        log(f"TRIPWIRE {f}")
    return 1 if fired and config.TRIPWIRES_FATAL else 0


if __name__ == "__main__":
    sys.exit(main())
