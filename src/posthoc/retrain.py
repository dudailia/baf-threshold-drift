"""Post hoc task 4 (exploratory): retraining.

For test months t = 5, 6, 7: train on months 0 to t-2 with the main study's best
configuration for the variant (no re-tuning), set the threshold at 5% FPR on month
t-1's labels, apply it to month t. Five seeds; 1,000 paired resamples for seed 0,
compared with the main strategies on the same resampled rows of month t.

Run with: python -m src.posthoc.retrain
"""

import json

import numpy as np
import pandas as pd

from src import config
from src.data import LABEL, VARIANT_FILES, load_variant
from src.models import fit_lgbm
from src.posthoc.common import (CKPT, MAIN_STRATEGIES, PRED, ci_rows, commit, evaluate, load_months, log, main_boot, main_pred_path,
                                paired, save_pred, stamp, summarize, write)
from src.preprocess import LGBMPrep

TEST = [5, 6, 7]


def run(c):
    points, cis, pairs = [], [], []
    for v in config.VARIANT_SUBSET or list(VARIANT_FILES):
        df = load_variant(v, raw_dir=config.RAW_DIR)
        mpoint, mboot = main_boot(v, config.N_BOOT)
        for t in TEST:
            tr = df[df.month <= t - 2]
            ev = df[df.month.isin([t - 1, t])]
            prep = LGBMPrep().fit(tr)
            assert "month" not in prep.columns and tr.month.max() == t - 2
            Xtr, Xev = prep.transform(tr), prep.transform(ev)
            for s in config.SEEDS:
                cfg = json.loads(main_pred_path(v, s).with_suffix(".json").read_text())["config"]
                path = PRED / "retrain" / v / f"month{t}_seed{s}.npz"
                if not path.exists():
                    m = fit_lgbm(Xtr, tr[LABEL].to_numpy(), cfg, seed=s, n_jobs=config.N_JOBS)
                    save_pred(path, ev, m.predict_proba(Xev)[:, 1], dict(variant=v, test_month=t, seed=s, train_months=f"0-{t - 2}", config=cfg))
                ck = CKPT / "retrain_eval" / f"{v}__m{t}__seed{s}.npz"
                if ck.exists():
                    z = np.load(ck, allow_pickle=True)
                    pt, bt = list(z["point"]), z["boot"].item()
                else:
                    pt, bt = evaluate(load_months(path), v, t - 1, ["static"], config.N_BOOT if s == config.SEEDS[0] else 0)
                    ck.parent.mkdir(parents=True, exist_ok=True)
                    np.savez(ck, point=np.array(pt, dtype=object), boot=np.array(bt, dtype=object))
                pt = [dict(r, strategy="retrain_threshold_prev_month") for r in pt if r["month"] == t]
                bt = {("retrain_threshold_prev_month", t): bt[("static", t)]} if bt else {}
                base = dict(variant=v, seed=s, train_months=f"0-{t - 2}")
                points += [{**base, **r} for r in pt]
                cis += ci_rows(pt, bt, base)
                if s == config.SEEDS[0]:
                    r = pt[0]
                    for comp in MAIN_STRATEGIES:
                        for metric in ("abs_budget_miss", "budget_miss", "tpr"):
                            pairs.append(paired(r, bt[("retrain_threshold_prev_month", t)], mpoint[(comp, t)], mboot[(comp, t)], metric,
                                                dict(variant=v, month=t, strategy="retrain_threshold_prev_month", comparator=comp)))
            log(f"retrain {v} month {t} done", "retrain")
    metrics = pd.DataFrame(points)
    write(stamp(metrics, c), "retrain_metrics")
    write(stamp(summarize(metrics, ["variant", "strategy", "month"]), c), "retrain_summary")
    write(stamp(pd.DataFrame(cis), c), "retrain_ci")
    write(stamp(pd.DataFrame(pairs), c), "retrain_paired")


if __name__ == "__main__":
    run(commit())
