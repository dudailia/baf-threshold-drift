"""Post hoc task 2 (exploratory): what moves the negatives' scores.

Main study, LightGBM seed 0. For each variant and month 3 to 7: the quantile of the
month's negative scores at which month 3's static threshold falls (equals 1 - FPR),
and the KS distance between month 3 negative scores and month t negative scores.
Then, for each of the 10 features with the highest gain, the feature's values in
month t negatives are replaced by draws (with replacement) from month 3 negatives of
the same age group (`customer_age >= 50` or not), the model rescores those rows,
and the static FPR miss is recomputed. Five independent draws per cell.

Run with: python -m src.posthoc.mechanism
"""

import json

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from src import config
from src.data import LABEL, MAIN_SPLIT, VARIANT_FILES, load_variant
from src.models import fit_lgbm
from src.posthoc.common import TARGET, commit, log, main_pred_path, stamp, write
from src.preprocess import LGBMPrep
from src.thresholds import threshold_at_fpr

N_DRAWS = 5
MONTHS = MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]  # split months are defined once, in src/data.py
VAL = MAIN_SPLIT["validation"][0]


def run(c):
    q_rows, f_rows, checks = [], [], []
    for v in config.VARIANT_SUBSET or list(VARIANT_FILES):
        df = load_variant(v, raw_dir=config.RAW_DIR)
        meta = json.loads(main_pred_path(v).with_suffix(".json").read_text())
        z = np.load(main_pred_path(v))
        train = df[df.month.isin(MAIN_SPLIT["train"])]
        prep = LGBMPrep().fit(train)
        model = fit_lgbm(prep.transform(train), train[LABEL].to_numpy(), meta["config"], seed=0, n_jobs=config.N_JOBS)
        ev = df.loc[z["row"]]
        refit = model.predict_proba(prep.transform(ev))[:, 1]
        checks.append(dict(variant=v, max_abs_diff_refit_vs_saved=float(np.max(np.abs(refit - z["score"])))))
        score, label, month = z["score"], z["label"], z["month"]
        neg3 = score[(month == VAL) & (label == 0)]
        t = threshold_at_fpr(score[month == VAL], label[month == VAL], TARGET)
        for m in MONTHS:
            neg = score[(month == m) & (label == 0)]
            fpr = float((neg >= t).mean())
            q_rows.append(dict(variant=v, month=m, static_threshold=t, threshold_quantile_in_negatives=float((neg < t).mean()),
                               realized_fpr=fpr, one_minus_fpr=1 - fpr, ks_vs_month3_negatives=float(ks_2samp(neg3, neg).statistic) if m != VAL else 0.0))
        top = sorted(meta["gain_importance"], key=meta["gain_importance"].get, reverse=True)[:10]
        neg_rows = ev[(ev[LABEL] == 0)]
        ref = neg_rows[neg_rows.month == VAL]
        old_ref = ref.customer_age >= 50
        for m in MONTHS[1:]:
            cur = neg_rows[neg_rows.month == m]
            base_fpr = float((model.predict_proba(prep.transform(cur))[:, 1] >= t).mean())
            old_cur = (cur.customer_age >= 50).to_numpy()
            for rank, f in enumerate(top, 1):
                misses = []
                for draw in range(N_DRAWS):
                    rng = np.random.default_rng([draw, m, rank])
                    mod = cur.copy()
                    for g in (True, False):
                        pool = ref.loc[old_ref == g, f].to_numpy()
                        mod.loc[old_cur == g, f] = rng.choice(pool, size=int((old_cur == g).sum()), replace=True)
                    misses.append(float((model.predict_proba(prep.transform(mod))[:, 1] >= t).mean()) - TARGET)
                base_miss = base_fpr - TARGET
                shrink = [abs(base_miss) - abs(x) for x in misses]
                f_rows.append(dict(variant=v, month=m, rank=rank, feature=f, static_miss=base_miss,
                                   miss_after_replacement_mean=float(np.mean(misses)), miss_after_replacement_min=float(np.min(misses)),
                                   miss_after_replacement_max=float(np.max(misses)), shrink_mean=float(np.mean(shrink)),
                                   shrink_min=float(np.min(shrink)), shrink_max=float(np.max(shrink)), n_draws=N_DRAWS))
            log(f"mechanism {v} month {m} done", "mechanism")
    write(stamp(pd.DataFrame(q_rows), c), "mechanism_quantiles")
    write(stamp(pd.DataFrame(f_rows), c), "mechanism_features")
    write(stamp(pd.DataFrame(checks), c), "mechanism_refit_check")


if __name__ == "__main__":
    run(commit())
