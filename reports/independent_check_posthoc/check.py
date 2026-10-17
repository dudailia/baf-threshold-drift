# Paths are relative to the repository root (run from there); they replaced the checker's absolute paths on 2026-10-17.
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

R = ""
OUT = "checker_output/independent_check_posthoc/"
VARIANTS = ["Base", "Variant I", "Variant II", "Variant III", "Variant IV", "Variant V"]
SEEDS = range(5)
F = 0.05
TOL = 1e-9


def weighted_threshold(score, weight, budget):
    """Largest {score >= t} with sum(weight over flagged) <= budget; ties never split."""
    u, inv = np.unique(score, return_inverse=True)  # ascending
    w = np.bincount(inv, weights=weight, minlength=len(u))
    u = u[::-1]
    cum = np.cumsum(w[::-1])
    bad = np.nonzero(cum > budget)[0]
    if len(bad) == 0:
        return -np.inf
    return np.nextafter(u[bad[0]], np.inf)


def thr_fpr(score, label, f=F):
    neg = label == 0
    s = score[neg]
    return weighted_threshold(s, np.ones(len(s)), f * len(s))


def thr_top(score, q=F):
    return weighted_threshold(score, np.ones(len(score)), q * len(score))


def metrics(score, label, t):
    flag = score >= t
    neg = label == 0
    pos = label == 1
    fpr = (flag & neg).sum() / neg.sum()
    return dict(threshold=t, realized_fpr=fpr, budget_miss=fpr - F, tpr=(flag & pos).sum() / pos.sum())


def load(path):
    z = np.load(path)
    return {k: z[k] for k in z.files}


def by_month(d, m):
    sel = d["month"] == m
    return d["score"][sel], d["label"][sel]


def compare(name, mine, stored_path, keys, mets, stored_filter=None):
    st = pd.read_csv(stored_path)
    if stored_filter is not None:
        st = stored_filter(st)
    mine.to_csv(OUT + f"recomputed_{name}.csv", index=False)
    m = mine.merge(st[keys + mets], on=keys, how="outer", suffixes=("_mine", "_stored"), indicator=True)
    unmatched = (m["_merge"] != "both").sum()
    rows = []
    for c in mets:
        m[c + "_absdiff"] = (m[c + "_mine"] - m[c + "_stored"]).abs()
    m.to_csv(OUT + f"comparison_{name}.csv", index=False)
    both = m[m["_merge"] == "both"]
    anymis = np.zeros(len(both), bool)
    for c in mets:
        d = both[c + "_absdiff"]
        mis = (d > TOL) | (d.isna() & ~(both[c + "_mine"].isna() & both[c + "_stored"].isna()))
        anymis |= mis.values
        rows.append(dict(check=name, rows_compared=len(both), metrics=c, max_abs_diff=d.max(), mismatches=int(mis.sum())))
    print(f"== {name}: rows mine={len(mine)} stored={len(st)} matched={len(both)} unmatched={unmatched}")
    if anymis.any():
        cols = keys + [x for c in mets for x in (c + "_mine", c + "_stored", c + "_absdiff")]
        print(both.loc[anymis, cols].head(10).to_string())
    return rows


summary = []

# A. Rolling-origin
recs = []
SPLITS = {"A": (2, [3, 4, 5, 6, 7]), "B": (4, [5, 6, 7])}
for sp, (vm, tms) in SPLITS.items():
    for v in VARIANTS:
        for k in SEEDS:
            d = load(R + f"results_posthoc/predictions/rolling_{sp}/{v}/lightgbm_seed{k}.npz")
            t_static = thr_fpr(*by_month(d, vm))
            for m in tms:
                s, y = by_month(d, m)
                strat = {
                    "static": t_static,
                    "label_free_top": thr_top(s),
                    "delayed_lag1": thr_fpr(*by_month(d, m - 1)),
                    "oracle": thr_fpr(s, y),
                }
                for name, t in strat.items():
                    recs.append(dict(split=sp, variant=v, seed=k, strategy=name, month=m, **metrics(s, y, t)))
summary += compare("A_rolling", pd.DataFrame(recs), R + "results_posthoc/rolling_metrics.csv",
                   ["split", "variant", "seed", "strategy", "month"], ["realized_fpr", "budget_miss", "tpr"])

# B. Hyperparameter sensitivity
recs = []
for v in VARIANTS:
    for r in range(6):
        for k in SEEDS:
            p = (R + f"results/predictions/{v}/lightgbm_seed{k}.npz" if r == 0
                 else R + f"results_posthoc/predictions/hyper/{v}/cfg{r}_seed{k}.npz")
            d = load(p)
            t = thr_fpr(*by_month(d, 3))
            for m in [4, 5, 6, 7]:
                s, y = by_month(d, m)
                recs.append(dict(variant=v, config_rank=r, seed=k, month=m, **metrics(s, y, t)))
summary += compare("B_hyper", pd.DataFrame(recs), R + "results_posthoc/hyper_metrics.csv",
                   ["variant", "config_rank", "seed", "month"], ["realized_fpr", "budget_miss", "tpr"],
                   stored_filter=lambda x: x[x.strategy == "static"])

# C. Retraining
recs = []
for v in VARIANTS:
    for k in SEEDS:
        for m in [5, 6, 7]:
            d = load(R + f"results_posthoc/predictions/retrain/{v}/month{m}_seed{k}.npz")
            assert set(np.unique(d["month"])) == {m - 1, m}
            t = thr_fpr(*by_month(d, m - 1))
            s, y = by_month(d, m)
            recs.append(dict(variant=v, seed=k, month=m, **metrics(s, y, t)))
summary += compare("C_retrain", pd.DataFrame(recs), R + "results_posthoc/retrain_metrics.csv",
                   ["variant", "seed", "month"], ["realized_fpr", "budget_miss", "tpr"])

# D. Isotonic label-free targeting
recs = []
for v in VARIANTS:
    for k in SEEDS:
        d = load(R + f"results/predictions/{v}/lightgbm_seed{k}.npz")
        s3, y3 = by_month(d, 3)
        iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(s3, y3)
        for m in [4, 5, 6, 7]:
            s, y = by_month(d, m)
            q = 1.0 - iso.predict(s)
            t = weighted_threshold(s, q, F * q.sum())
            met = metrics(s, y, t)
            met["estimated_fpr"] = q[s >= t].sum() / q.sum()
            recs.append(dict(variant=v, seed=k, month=m, **met))
summary += compare("D_isotonic", pd.DataFrame(recs), R + "results_posthoc/isotonic_metrics.csv",
                   ["variant", "seed", "month"], ["realized_fpr", "budget_miss", "tpr", "estimated_fpr"])

S = pd.DataFrame(summary)
S.to_csv(OUT + "summary.csv", index=False)
print(S.to_string(index=False))
