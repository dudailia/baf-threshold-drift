"""Post hoc task 5 (exploratory): probability-based label-free targeting.

Main study LightGBM scores. Isotonic regression maps scores to fraud probability p,
fitted on month 3 only. In each test month the threshold flags the largest set with
estimated FPR = sum over flagged of (1 - p) / sum over all of (1 - p) at most 5%,
without using the month's labels. Five seeds; for seed 0, 1,000 paired resamples in
which month 3 is resampled and the isotonic map refitted, compared with the main
label-free strategies on the same resampled rows.

Run with: python -m src.posthoc.isotonic
"""

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from src import config
from src.data import VARIANT_FILES
from src.fastboot import AGE_DEFS, AGE_BINS, CHUNK, resample_weights
from src.posthoc.common import (CKPT, MAIN_STRATEGIES, TARGET, ci_rows, commit, load_months, log, main_boot, main_pred_path, paired,
                                stamp, summarize, write)
from src.thresholds import _threshold_for_budget

NAME = "label_free_isotonic"
TEST = [4, 5, 6, 7]


def _fit(s, y, w=None):
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    keep = None if w is None else w > 0
    return iso.fit(s if keep is None else s[keep], y if keep is None else y[keep], sample_weight=None if w is None else w[keep])


def _metrics(s, y, age, t, w):
    flag = s >= t
    old = np.isin(AGE_BINS(age), AGE_DEFS[">=50"])
    neg, pos = w * (y == 0), w * (y == 1)
    fpr = (neg * flag).sum() / neg.sum()
    tpr = (pos * flag).sum() / pos.sum()
    fy = (neg * flag * ~old).sum() / (neg * ~old).sum()
    fo = (neg * flag * old).sum() / (neg * old).sum()
    return dict(realized_fpr=fpr, budget_miss=fpr - TARGET, abs_budget_miss=abs(fpr - TARGET), tpr=tpr,
                fpr_ratio=min(fy, fo) / max(fy, fo) if max(fy, fo) > 0 else np.nan, alert_rate=(w * flag).sum() / w.sum(),
                estimated_fpr=None)


def _point(months):
    s3, y3, _ = months[3]
    iso = _fit(s3, y3)
    out = []
    for m in TEST:
        s, y, age = months[m]
        q = 1 - iso.predict(s)
        t = _threshold_for_budget(s, q, TARGET * q.sum())
        r = _metrics(s, y, age, t, np.ones_like(s))
        r["estimated_fpr"] = float(q[s >= t].sum() / q.sum())
        out.append(dict(strategy=NAME, month=m, available=True, threshold=t, **r))
    return out


def _boot(months, variant, n_boot):
    s3, y3, _ = months[3]
    acc = {m: [] for m in TEST}
    for c0 in range(0, n_boot, CHUNK):
        b = min(CHUNK, n_boot - c0)
        W = {m: resample_weights(len(months[m][0]), CHUNK, ((variant,), m, c0))[:b].astype(float) for m in [3] + TEST}
        for i in range(b):
            iso = _fit(s3, y3, W[3][i])
            for m in TEST:
                s, y, age = months[m]
                w = W[m][i]
                q = w * (1 - iso.predict(s))
                t = _threshold_for_budget(s, q, TARGET * q.sum())
                acc[m].append(_metrics(s, y, age, t, w))
    return {(NAME, m): {k: np.array([r[k] for r in rows], dtype=float) for k in rows[0] if k != "estimated_fpr"} for m, rows in acc.items()}


def run(c):
    points, cis, pairs = [], [], []
    for v in config.VARIANT_SUBSET or list(VARIANT_FILES):
        mpoint, mboot = main_boot(v, config.N_BOOT)
        for s in config.SEEDS:
            months = load_months(main_pred_path(v, s))
            pt = _point(months)
            base = dict(variant=v, seed=s)
            points += [{**base, **r} for r in pt]
            if s == config.SEEDS[0]:
                ck = CKPT / "isotonic_boot" / f"{v}.npz"
                if ck.exists():
                    bt = np.load(ck, allow_pickle=True)["boot"].item()
                else:
                    bt = _boot(months, v, config.N_BOOT)
                    ck.parent.mkdir(parents=True, exist_ok=True)
                    np.savez(ck, boot=np.array(bt, dtype=object))
                cis += ci_rows(pt, bt, base)
                for r in pt:
                    for comp in MAIN_STRATEGIES:
                        for metric in ("abs_budget_miss", "budget_miss", "tpr"):
                            pairs.append(paired(r, bt[(NAME, r["month"])], mpoint[(comp, r["month"])], mboot[(comp, r["month"])], metric,
                                                dict(variant=v, month=r["month"], strategy=NAME, comparator=comp)))
        log(f"isotonic {v} done", "isotonic")
    metrics = pd.DataFrame(points)
    write(stamp(metrics, c), "isotonic_metrics")
    write(stamp(summarize(metrics, ["variant", "strategy", "month"]), c), "isotonic_summary")
    write(stamp(pd.DataFrame(cis), c), "isotonic_ci")
    write(stamp(pd.DataFrame(pairs), c), "isotonic_paired")


if __name__ == "__main__":
    run(commit())
