# Paths are relative to the repository root (run from there); they replaced the checker's absolute paths on 2026-10-17.
import numpy as np, pandas as pd, sys
src = sys.argv[1]; dst = sys.argv[2]
r = pd.read_csv(src)
m = pd.read_csv('results/metrics.csv')
m = m[(m.fpr_target == 0.05) & (m.age_def == '>=50')]
K = ['variant','model','seed','strategy','month']
print('stored rows for these strategies:', m[m.strategy.isin(r.strategy.unique())].shape[0],
      'dup keys:', m[m.strategy.isin(r.strategy.unique())].duplicated(K).sum())
j = r.merge(m, on=K, how='left', suffixes=('_mine','_stored'), indicator=True)
print('join:', j['_merge'].value_counts().to_dict())
MET = ['realized_fpr','tpr','alert_rate','precision','fpr_young','fpr_old','fpr_ratio','alert_share_old','budget_miss','threshold']
long = []
for c in MET:
    d = (j[c+'_mine'] - j[c+'_stored']).abs()
    both_nan = j[c+'_mine'].isna() & j[c+'_stored'].isna()
    one_nan = j[c+'_mine'].isna() ^ j[c+'_stored'].isna()
    n = int((~j[c+'_mine'].isna() & ~j[c+'_stored'].isna()).sum())
    mis = (d > 1e-9) | one_nan
    print(f'{c:16s} n={n:5d} both_nan={int(both_nan.sum())} one_nan={int(one_nan.sum())} maxabs={d.max():.3e} mismatches={int(mis.sum())}')
    t = j[K].copy(); t['metric'] = c; t['mine'] = j[c+'_mine']; t['stored'] = j[c+'_stored']; t['abs_diff'] = d; t['mismatch'] = mis
    long.append(t)
long = pd.concat(long)
long.to_csv(dst, index=False)
mm = long[long.mismatch & (long.metric != 'threshold')]
print('total metric mismatches (excluding threshold):', len(mm), 'rows affected:', mm[K].drop_duplicates().shape[0])
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 20)
print(mm.sort_values('abs_diff', ascending=False).head(30).to_string(index=False))
print(mm.groupby(['strategy','metric']).size())
