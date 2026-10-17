"""Post hoc task 1: rolling-origin robustness.

Splits A (train 0-1, validate 2, test 3-7) and B (train 0-3, validate 4, test 5-7).
LightGBM, the same 20 configurations as the main study tuned on the split's
validation month, 5 seeds, strategies static, label-free top 5%, delayed-label lag 1
and the oracle (upper bound), 1,000 paired resamples.

Run with: python -m src.posthoc.rolling train | evaluate
"""

import json
import sys

import numpy as np
import pandas as pd

from src import config
from src.data import LABEL, VARIANT_FILES, load_variant
from src.models import fit_lgbm, sample_configs
from src.posthoc.common import CKPT, PRED, ci_rows, commit, evaluate, load_months, log, save_pred, stamp, summarize, write
from src.preprocess import LGBMPrep
from src.train import CONFIG_SEED, tpr_at_fpr

SPLITS = {
    "A": dict(train=[0, 1], validation=[2], test=[3, 4, 5, 6, 7]),
    "B": dict(train=[0, 1, 2, 3], validation=[4], test=[5, 6, 7]),
}
STRATEGIES = ["static", "label_free_top", "delayed_lag1", "oracle"]


def _variants():
    return config.VARIANT_SUBSET or list(VARIANT_FILES)


def pred_path(split, variant, seed):
    return PRED / f"rolling_{split}" / variant / f"lightgbm_seed{seed}.npz"


def train(c):
    configs = sample_configs(config.N_TRIALS, CONFIG_SEED)
    for v in _variants():
        df = load_variant(v, raw_dir=config.RAW_DIR)
        for split, sp in SPLITS.items():
            if all(pred_path(split, v, s).exists() for s in config.SEEDS):
                continue
            tr = df[df.month.isin(sp["train"])]
            ev = df[df.month.isin(sp["validation"] + sp["test"])]
            va = ev[ev.month.isin(sp["validation"])]
            prep = LGBMPrep().fit(tr)
            assert "month" not in prep.columns
            Xtr, Xev, Xva = prep.transform(tr), prep.transform(ev), prep.transform(va)
            ckpt = CKPT / f"rolling_{split}_tuning" / f"{v}.jsonl"
            ckpt.parent.mkdir(parents=True, exist_ok=True)
            done = [json.loads(x) for x in ckpt.read_text().splitlines()] if ckpt.exists() else []
            for i, cfg in enumerate(configs):
                if i < len(done):
                    continue
                m = fit_lgbm(Xtr, tr[LABEL].to_numpy(), cfg, seed=0, n_jobs=config.N_JOBS)
                rec = dict(variant=v, split=split, trial=i, config=cfg, val_tpr_at_5pct_fpr=tpr_at_fpr(m.predict_proba(Xva)[:, 1], va[LABEL].to_numpy()))
                with open(ckpt, "a") as f:
                    f.write(json.dumps(rec) + "\n")
                done.append(rec)
            best = max(done[: len(configs)], key=lambda r: (r["val_tpr_at_5pct_fpr"], -r["trial"]))
            log(f"rolling {split} {v} best trial {best['trial']} val TPR {best['val_tpr_at_5pct_fpr']:.4f}", "rolling")
            for s in config.SEEDS:
                if pred_path(split, v, s).exists():
                    continue
                m = fit_lgbm(Xtr, tr[LABEL].to_numpy(), best["config"], seed=s, n_jobs=config.N_JOBS)
                save_pred(pred_path(split, v, s), ev, m.predict_proba(Xev)[:, 1],
                          dict(variant=v, split=split, seed=s, config=best["config"], tuning_trial=best["trial"], predictions_commit=c))
            log(f"rolling {split} {v} seeds saved", "rolling")


def evaluate_all(c):
    points, cis = [], []
    for split, sp in SPLITS.items():
        for v in _variants():
            for s in config.SEEDS:
                ck = CKPT / "rolling_eval" / f"{split}__{v}__seed{s}.json"
                if ck.exists():
                    d = json.loads(ck.read_text())
                else:
                    pt, bt = evaluate(load_months(pred_path(split, v, s)), v, sp["validation"][0], STRATEGIES,
                                      config.N_BOOT if s == config.SEEDS[0] else 0)
                    base = dict(split=split, variant=v, seed=s)
                    d = dict(point=[{**base, **r} for r in pt], ci=ci_rows(pt, bt, base))
                    ck.parent.mkdir(parents=True, exist_ok=True)
                    ck.write_text(json.dumps(d, default=float))
                    log(f"rolling evaluated {split} {v} seed {s}", "rolling")
                points += d["point"]
                cis += d["ci"]
    metrics = pd.DataFrame(points)
    keys = ["split", "variant", "strategy", "month"]
    write(stamp(metrics, c), "rolling_metrics")
    write(stamp(summarize(metrics, keys), c), "rolling_summary")
    write(stamp(pd.DataFrame(cis), c), "rolling_ci")


if __name__ == "__main__":
    c = commit()
    {"train": train, "evaluate": evaluate_all}[sys.argv[1]](c)
