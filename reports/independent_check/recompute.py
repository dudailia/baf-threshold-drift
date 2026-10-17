# Paths are relative to the repository root (run from there); they replaced the checker's absolute paths on 2026-10-17.
import numpy as np, pandas as pd, sys
PRED = 'results/predictions'
VARIANTS = ["Base","Variant I","Variant II","Variant III","Variant IV","Variant V"]
MODELS = ["lightgbm","logreg"]; F = 0.05
READING = sys.argv[1] if len(sys.argv) > 1 else 'literal'   # 'literal' or 'lowest_flagged'

def threshold(scores, counted, limit, reading=READING):
    """scores: array; counted: bool mask of items counted against limit.
    Returns threshold t such that flag = scores >= t."""
    u, inv = np.unique(scores, return_inverse=True)       # ascending
    c = np.bincount(inv, weights=counted.astype(float), minlength=len(u))
    ud, cd = u[::-1], c[::-1]
    cs = np.cumsum(cd)
    k = int(np.searchsorted(cs, limit, side='right'))     # number of distinct values flagged
    if k == 0:
        return np.nextafter(ud[0], np.inf)
    if k == len(ud):
        return -np.inf
    if reading == 'literal':
        return np.nextafter(ud[k], np.inf)                # just above first breaking value
    return ud[k-1]                                        # lowest flagged value

def thr_fpr(s, y, f): return threshold(s, y == 0, f * np.sum(y == 0))
def thr_top(s, q): return threshold(s, np.ones(len(s), bool), q * len(s))

def metrics(s, y, a, t):
    fl = s >= t; neg = y == 0; pos = ~neg; old = a >= 50; yng = ~old
    rf = (fl & neg).sum() / neg.sum()
    fo = (fl & neg & old).sum() / (neg & old).sum()
    fy = (fl & neg & yng).sum() / (neg & yng).sum()
    nf = fl.sum()
    return dict(realized_fpr=rf, budget_miss=rf - F, tpr=(fl & pos).sum() / pos.sum(),
                alert_rate=nf / len(s), precision=(fl & pos).sum() / nf if nf else np.nan,
                fpr_young=fy, fpr_old=fo,
                fpr_ratio=min(fy, fo) / max(fy, fo) if max(fy, fo) > 0 else np.nan,
                alert_share_old=(fl & old).sum() / nf if nf else np.nan, threshold=t)

rows = []
for v in VARIANTS:
    for mo in MODELS:
        for k in range(5):
            z = np.load(f'{PRED}/{v}/{mo}_seed{k}.npz')
            M = {m: (z['score'][z['month'] == m], z['label'][z['month'] == m], z['age'][z['month'] == m]) for m in range(3, 8)}
            s3, y3, _ = M[3]
            t_static = thr_fpr(s3, y3, F)
            q_val = np.mean(s3 >= t_static)
            for m in range(4, 8):
                s, y, a = M[m]
                ths = dict(static=t_static, label_free_top=thr_top(s, F),
                           label_free_val_rate=thr_top(s, q_val),
                           delayed_lag1=thr_fpr(*M[m-1][:2], F), oracle=thr_fpr(s, y, F))
                for st, t in ths.items():
                    rows.append(dict(variant=v, model=mo, seed=k, strategy=st, month=m, **metrics(s, y, a, t)))
out = pd.DataFrame(rows)
out.to_csv('recomputed.csv' if READING == 'literal' else f'recomputed_{READING}.csv', index=False)
print(out.shape)
