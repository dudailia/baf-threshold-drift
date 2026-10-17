# Paths are relative to the repository root (run from there); they replaced the checker's absolute paths on 2026-10-17.
import numpy as np, pandas as pd
PRED = 'results/predictions'
VARIANTS = ["Base","Variant I","Variant II","Variant III","Variant IV","Variant V"]
F = 0.05; B = 1000
rng = np.random.default_rng(20261016)

def thr_weighted(u_desc, inv_desc, counted_w, limit):
    c = np.bincount(inv_desc, weights=counted_w, minlength=len(u_desc))
    cs = np.cumsum(c)
    k = int(np.searchsorted(cs, limit, side='right'))
    if k == 0: return np.nextafter(u_desc[0], np.inf)
    if k == len(u_desc): return -np.inf
    return np.nextafter(u_desc[k], np.inf)

def prep(s):
    u, inv = np.unique(s, return_inverse=True)
    return u[::-1], (len(u) - 1 - inv)

def fpr_w(s, neg, w, t):
    wn = w * neg
    return wn[s >= t].sum() / wn.sum()

ci = pd.read_csv('results/ci.csv')
ci = ci[(ci.model == 'lightgbm') & (ci.seed == 0) & (ci.fpr_target == 0.05) & (ci.age_def == '>=50') & (ci.metric == 'budget_miss')]
rows = []
for v in VARIANTS:
    z = np.load(f'{PRED}/{v}/lightgbm_seed0.npz')
    M = {m: (z['score'][z['month'] == m], (z['label'][z['month'] == m] == 0).astype(float)) for m in range(3, 8)}
    s3, n3 = M[3]; u3, i3 = prep(s3); N3 = len(s3)
    P = {m: prep(M[m][0]) for m in range(4, 8)}
    bm = {(st, m): np.empty(B) for st in ('static', 'label_free_top') for m in range(4, 8)}
    for b in range(B):
        w3 = np.bincount(rng.integers(0, N3, N3), minlength=N3).astype(float)
        t_static = thr_weighted(u3, i3, w3 * n3, F * (w3 * n3).sum())
        for m in range(4, 8):
            s, neg = M[m]; N = len(s)
            w = np.bincount(rng.integers(0, N, N), minlength=N).astype(float)
            bm[('static', m)][b] = fpr_w(s, neg, w, t_static) - F
            u, i = P[m]
            t_top = thr_weighted(u, i, w, F * w.sum())
            bm[('label_free_top', m)][b] = fpr_w(s, neg, w, t_top) - F
    for (st, m), arr in bm.items():
        lo, hi = np.percentile(arr, [2.5, 97.5])
        srow = ci[(ci.variant == v) & (ci.strategy == st) & (ci.month == m)]
        assert len(srow) == 1, (v, st, m, len(srow))
        srow = srow.iloc[0]
        rows.append(dict(variant=v, strategy=st, month=m, my_lo=lo, my_hi=hi, my_width=hi - lo,
                         stored_estimate=srow.estimate, stored_lo=srow.lo, stored_hi=srow.hi,
                         stored_width=srow.hi - srow.lo, ratio=(hi - lo) / (srow.hi - srow.lo)))
    print(v, 'done', flush=True)
out = pd.DataFrame(rows)
out['flag'] = (out.ratio < 0.7) | (out.ratio > 1.4)
out.to_csv('bootstrap_widths.csv', index=False)
pd.set_option('display.width', 250)
print(out.to_string(index=False))
print('ratio median/min/max:', out.ratio.median(), out.ratio.min(), out.ratio.max(), 'n=', len(out))
print(out.groupby('strategy').ratio.describe())
print('flagged:', int(out.flag.sum()))
