"""Train LightGBM (tuned on validation month 3) and logistic regression, 5 seeds each.

Writes one prediction file per (variant, model, seed) for months 3 to 7 to
results/predictions/, and checkpoints every tuning trial, so an interrupted run
resumes where it stopped. Refuses to run unless PREDICTIONS.md is committed and
unchanged (src/guard.py).

Run with: python -m src.train
"""

import json
import sys
import time

import numpy as np
import pandas as pd

from src import config
from src.data import LABEL, MAIN_SPLIT, VARIANT_FILES, load_variant, stratified_sample
from src.guard import predictions_commit
from src.models import fit_lgbm, fit_lr, sample_configs
from src.preprocess import LGBMPrep, LRPrep
from src.thresholds import threshold_at_fpr

CONFIG_SEED = 2022  # the same sampled configurations are tried on every variant
EVAL_MONTHS = MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]


def log(msg):
    config.LOGS.mkdir(parents=True, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(config.LOGS / "train.log", "a") as f:
        f.write(line + "\n")


def variants():
    return config.VARIANT_SUBSET or list(VARIANT_FILES)


def load(variant):
    df = load_variant(variant, raw_dir=config.RAW_DIR)
    if config.SAMPLE_FRACTION < 1:
        df = stratified_sample(df, config.SAMPLE_FRACTION, seed=0)
    return df


def tpr_at_fpr(scores, labels, target=0.05):
    t = threshold_at_fpr(scores, labels, target)
    return float((scores[labels == 1] >= t).mean())


def pred_path(variant, model, seed):
    return config.PREDICTIONS_DIR / variant / f"{model}_seed{seed}.npz"


def save_predictions(variant, model, seed, ev, scores, meta):
    path = pred_path(variant, model, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, row=ev.index.to_numpy(), month=ev["month"].to_numpy(), label=ev[LABEL].to_numpy(),
                        age=ev["customer_age"].to_numpy(), score=scores)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=1, default=str))


def tune(variant, Xtr, ytr, Xval, yval, commit):
    ckpt = config.CHECKPOINTS / "tuning" / f"{variant}.jsonl"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    done = [json.loads(line) for line in ckpt.read_text().splitlines()] if ckpt.exists() else []
    configs = sample_configs(config.N_TRIALS, CONFIG_SEED)
    for i, cfg in enumerate(configs):
        if i < len(done):
            continue
        t0 = time.time()
        model = fit_lgbm(Xtr, ytr, cfg, seed=0, n_jobs=config.N_JOBS)
        val_tpr = tpr_at_fpr(model.predict_proba(Xval)[:, 1], yval)
        rec = dict(variant=variant, trial=i, config=cfg, val_tpr_at_5pct_fpr=val_tpr, fit_seconds=time.time() - t0,
                   predictions_commit=commit)
        with open(ckpt, "a") as f:
            f.write(json.dumps(rec) + "\n")
        done.append(rec)
        log(f"{variant} trial {i + 1}/{len(configs)} val TPR@5%FPR {val_tpr:.4f} ({rec['fit_seconds']:.0f}s)")
    best = max(done[: len(configs)], key=lambda r: (r["val_tpr_at_5pct_fpr"], -r["trial"]))
    return best


def train_variant(variant, commit):
    df = load(variant)
    train = df[df["month"].isin(MAIN_SPLIT["train"])]
    ev = df[df["month"].isin(EVAL_MONTHS)]
    val = ev[ev["month"].isin(MAIN_SPLIT["validation"])]
    ytr = train[LABEL].to_numpy()

    prep = LGBMPrep().fit(train)
    assert "month" not in prep.columns and LABEL not in prep.columns
    Xtr, Xev = prep.transform(train), prep.transform(ev)
    best = tune(variant, Xtr, ytr, prep.transform(val), val[LABEL].to_numpy(), commit)
    log(f"{variant} best trial {best['trial']} val TPR@5%FPR {best['val_tpr_at_5pct_fpr']:.4f}")
    for seed in config.SEEDS:
        if pred_path(variant, "lightgbm", seed).exists():
            continue
        t0 = time.time()
        model = fit_lgbm(Xtr, ytr, best["config"], seed=seed, n_jobs=config.N_JOBS)
        gain = dict(zip(prep.columns, model.booster_.feature_importance("gain").tolist()))
        meta = dict(variant=variant, model="lightgbm", seed=seed, config=best["config"], tuning_trial=best["trial"],
                    val_tpr_at_5pct_fpr=best["val_tpr_at_5pct_fpr"], features=prep.columns, gain_importance=gain,
                    n_train=len(train), fit_seconds=time.time() - t0, predictions_commit=commit,
                    sample_fraction=config.SAMPLE_FRACTION)
        save_predictions(variant, "lightgbm", seed, ev, model.predict_proba(Xev)[:, 1], meta)
        log(f"{variant} lightgbm seed {seed} saved ({meta['fit_seconds']:.0f}s)")

    lrp = LRPrep().fit(train)
    Xtr_lr, Xev_lr = lrp.transform(train), lrp.transform(ev)
    for seed in config.SEEDS:
        if pred_path(variant, "logreg", seed).exists():
            continue
        t0 = time.time()
        model = fit_lr(Xtr_lr, ytr, seed)
        meta = dict(variant=variant, model="logreg", seed=seed, features=lrp.feature_names, n_iter=int(model.n_iter_[0]),
                    n_train=len(train), fit_seconds=time.time() - t0, predictions_commit=commit,
                    sample_fraction=config.SAMPLE_FRACTION)
        save_predictions(variant, "logreg", seed, ev, model.predict_proba(Xev_lr)[:, 1], meta)
        log(f"{variant} logreg seed {seed} saved ({meta['fit_seconds']:.0f}s, {meta['n_iter']} iterations)")


def main():
    commit = predictions_commit()
    log(f"start: variants={variants()} trials={config.N_TRIALS} seeds={config.SEEDS} sample={config.SAMPLE_FRACTION} predictions_commit={commit}")
    for v in variants():
        train_variant(v, commit)
    log("train done")


if __name__ == "__main__":
    sys.exit(main())
