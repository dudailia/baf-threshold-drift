"""Post hoc task 3: hyperparameter sensitivity of the static strategy.

Main split (train 0-2, validate 3, test 4-7). For each variant: the 5 tuning trials
with the highest validation TPR at 5% FPR (rank 1 is the main study's model, whose
saved predictions are reused) and one strongly regularised configuration, 5 seeds
each, static threshold from month 3, 1,000 paired resamples for seed 0, plus a
paired comparison of each configuration's static miss against the main model's.

Run with: python -m src.posthoc.hyper
"""

import json

import numpy as np
import pandas as pd

from src import config
from src.data import LABEL, MAIN_SPLIT, VARIANT_FILES, load_variant
from src.models import fit_lgbm
from src.posthoc.common import CKPT, PRED, ci_rows, commit, evaluate, load_months, log, main_pred_path, paired, save_pred, stamp, summarize, write
from src.preprocess import LGBMPrep

REGULARISED = dict(n_estimators=200, max_depth=3, learning_rate=0.05, num_leaves=8, boosting="gbdt",
                   min_data_in_leaf=2000, max_bin=255, enable_bundle=True)
EVAL_MONTHS = MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]


def configs(v):
    trials = [json.loads(x) for x in (config.CHECKPOINTS / "tuning" / f"{v}.jsonl").read_text().splitlines()]
    top = sorted(trials, key=lambda r: (-r["val_tpr_at_5pct_fpr"], r["trial"]))[:5]
    out = [(f"rank {i} (trial {r['trial']})", r["config"], r["val_tpr_at_5pct_fpr"]) for i, r in enumerate(top, 1)]
    return out + [("strongly regularised", REGULARISED, np.nan)]


def run(c):
    points, cis, pairs, cfg_rows = [], [], [], []
    for v in config.VARIANT_SUBSET or list(VARIANT_FILES):
        df = None
        main_saved = None
        for k, (label, cfg, val_tpr) in enumerate(configs(v)):
            cfg_rows.append(dict(variant=v, config_label=label, val_tpr_at_5pct_fpr=val_tpr, config=json.dumps(cfg, sort_keys=True)))
            for s in config.SEEDS:
                path = main_pred_path(v, s) if k == 0 else PRED / "hyper" / v / f"cfg{k}_seed{s}.npz"
                if k > 0 and not path.exists():
                    if df is None:
                        df = load_variant(v, raw_dir=config.RAW_DIR)
                        tr = df[df.month.isin(MAIN_SPLIT["train"])]
                        ev = df[df.month.isin(EVAL_MONTHS)]
                        prep = LGBMPrep().fit(tr)
                        Xtr, Xev = prep.transform(tr), prep.transform(ev)
                    m = fit_lgbm(Xtr, tr[LABEL].to_numpy(), cfg, seed=s, n_jobs=config.N_JOBS)
                    save_pred(path, ev, m.predict_proba(Xev)[:, 1], dict(variant=v, config_label=label, seed=s, config=cfg))
                ck = CKPT / "hyper_eval" / f"{v}__cfg{k}__seed{s}.npz"
                if ck.exists():
                    z = np.load(ck, allow_pickle=True)
                    pt, bt = list(z["point"]), z["boot"].item()
                else:
                    pt, bt = evaluate(load_months(path), v, 3, ["static"], config.N_BOOT if s == config.SEEDS[0] else 0)
                    ck.parent.mkdir(parents=True, exist_ok=True)
                    np.savez(ck, point=np.array(pt, dtype=object), boot=np.array(bt, dtype=object))
                base = dict(variant=v, config_label=label, config_rank=k, seed=s)
                points += [{**base, **r} for r in pt]
                cis += ci_rows(pt, bt, base)
                if s == config.SEEDS[0]:
                    if k == 0:
                        main_saved = ({r["month"]: r for r in pt}, bt)
                    else:
                        for r in pt:
                            mp, mb = main_saved[0][r["month"]], main_saved[1][("static", r["month"])]
                            for metric in ("budget_miss", "abs_budget_miss"):
                                pairs.append(paired(r, bt[("static", r["month"])], mp, mb, metric,
                                                    dict(variant=v, config_label=label, month=r["month"], comparator="rank 1 (main model)")))
            log(f"hyper {v} {label} done", "hyper")
    metrics = pd.DataFrame(points)
    write(stamp(metrics, c), "hyper_metrics")
    write(stamp(summarize(metrics, ["variant", "config_label", "config_rank", "strategy", "month"]), c), "hyper_summary")
    write(stamp(pd.DataFrame(cis), c), "hyper_ci")
    write(stamp(pd.DataFrame(pairs), c), "hyper_paired")
    write(stamp(pd.DataFrame(cfg_rows), c), "hyper_configs")


if __name__ == "__main__":
    run(commit())
