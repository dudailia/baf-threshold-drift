"""Post hoc analysis 6: isolate the validation month with the model held fixed.

Main study LightGBM (trained on months 0 to 2). For every pair 3 <= m < t <= 7: static
threshold at 5% FPR on month m's negatives, applied to month t. Seeds 0 to 4 for the
seed spread; seed 0 with 1,000 paired resamples (main study resample keys).

Run with: python -m src.posthoc.valmonth
"""

import numpy as np
import pandas as pd

from src import config
from src.data import VARIANT_FILES
from src.posthoc.common import ci_rows, commit, evaluate, load_months, log, main_pred_path, stamp, write

MONTHS = [3, 4, 5, 6, 7]


def run(c):
    points, cis = [], []
    for v in config.VARIANT_SUBSET or list(VARIANT_FILES):
        for s in config.SEEDS:
            months = load_months(main_pred_path(v, s))
            for m in MONTHS:
                for t in MONTHS:
                    if t <= m:
                        continue
                    pt, bt = evaluate({m: months[m], t: months[t]}, v, m, ["static"], config.N_BOOT if s == config.SEEDS[0] else 0)
                    base = dict(variant=v, seed=s, threshold_month=m)
                    points += [{**base, **r} for r in pt]
                    cis += ci_rows(pt, bt, base)
            log(f"valmonth {v} seed {s} done", "valmonth")
    metrics = pd.DataFrame(points)
    keys = ["variant", "threshold_month", "month"]
    g = metrics.groupby(keys)["budget_miss"]
    summary = g.agg(mean="mean", sd=lambda x: x.std(ddof=1), min="min", max="max", n_seeds="size").reset_index()
    write(stamp(metrics, c), "valmonth_metrics")
    write(stamp(summary, c), "valmonth_summary")
    write(stamp(pd.DataFrame(cis), c), "valmonth_ci")


if __name__ == "__main__":
    run(commit())
