"""Post hoc analysis 7: fixed label-free rules as a control for isotonic targeting.

Main study LightGBM scores. Each test month, flag the top q of applications for
q in 5.0%, 5.25%, 5.5%, 5.75%, 6.0%; budget miss is always against 5% FPR. Seeds 0
to 4; seed 0 with 1,000 resamples on the same rows as the cached isotonic resamples
(task 5), paired against isotonic targeting.

Run with: python -m src.posthoc.fixedq
"""

import numpy as np
import pandas as pd

from src import config
from src.data import VARIANT_FILES
from src.fastboot import evaluate_months
from src.posthoc.common import CKPT, OUT, TARGET, commit, load_months, log, main_pred_path, stamp, write
from src.trace import verdict

QS = [0.05, 0.0525, 0.055, 0.0575, 0.06]
METRICS = ["realized_fpr", "tpr", "alert_rate"]


def _rows(point, q):
    out = {}
    for r in point:
        if r["strategy"] == "label_free_top" and np.isclose(r["fpr_target"], q) and r["age_def"] == ">=50":
            out[r["month"]] = r
    return out


def run(c):
    points, cis, pairs = [], [], []
    for v in config.VARIANT_SUBSET or list(VARIANT_FILES):
        iso_boot = np.load(CKPT / "isotonic_boot" / f"{v}.npz", allow_pickle=True)["boot"].item()
        iso_point = pd.read_csv(OUT / "isotonic_metrics.csv")
        iso_point = iso_point[(iso_point.variant == v) & (iso_point.seed == 0)].set_index("month")
        for s in config.SEEDS:
            months = load_months(main_pred_path(v, s))
            n_boot = config.N_BOOT if s == config.SEEDS[0] else 0
            point, boot = evaluate_months(months, QS, ">=50", n_boot=n_boot, weight_seed=(v,), boot_targets=QS if n_boot else None)
            for q in QS:
                for m, r in _rows(point, q).items():
                    row = dict(variant=v, seed=s, rule=f"top {100 * q:g}%", q=q, month=m, **{k: r[k] for k in METRICS})
                    row["budget_miss"] = r["realized_fpr"] - TARGET
                    row["abs_budget_miss"] = abs(row["budget_miss"])
                    points.append(row)
                    if n_boot:
                        arr = boot[("label_free_top", m, q, ">=50")]
                        miss = arr["realized_fpr"] - TARGET
                        lo, hi = np.nanpercentile(miss, [2.5, 97.5])
                        cis.append(dict(variant=v, seed=s, rule=row["rule"], q=q, month=m, metric="budget_miss", estimate=row["budget_miss"], lo=lo, hi=hi))
                        ia = iso_boot[("label_free_isotonic", m)]
                        d = np.abs(ia["realized_fpr"] - TARGET) - np.abs(miss)
                        dlo, dhi = np.nanpercentile(d, [2.5, 97.5])
                        ma = tuple(np.nanpercentile(ia["abs_budget_miss"], [2.5, 97.5]))
                        mb = tuple(np.nanpercentile(np.abs(miss), [2.5, 97.5]))
                        pairs.append(dict(variant=v, month=m, rule=row["rule"], q=q, metric="abs_budget_miss", comparison="isotonic minus fixed rule",
                                          diff=abs(iso_point.loc[m, "budget_miss"]) - row["abs_budget_miss"], lo=dlo, hi=dhi, verdict=verdict((dlo, dhi), ma, mb)))
        log(f"fixedq {v} done", "fixedq")
    metrics = pd.DataFrame(points)
    keys = ["variant", "rule", "q", "month"]
    long = metrics.melt(id_vars=keys + ["seed"], value_vars=["budget_miss", "abs_budget_miss", "tpr", "realized_fpr", "alert_rate"], var_name="metric")
    summary = long.groupby(keys + ["metric"])["value"].agg(mean="mean", sd=lambda x: x.std(ddof=1), min="min", max="max", n_seeds="size").reset_index()
    write(stamp(metrics, c), "fixedq_metrics")
    write(stamp(summary, c), "fixedq_summary")
    write(stamp(pd.DataFrame(cis), c), "fixedq_ci")
    write(stamp(pd.DataFrame(pairs), c), "fixedq_paired")


if __name__ == "__main__":
    run(commit())
