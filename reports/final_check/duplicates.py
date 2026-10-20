"""Item 13c of reports/code_review.md: rows shared between any two months, for every variant.

Each row is hashed on all columns except `month`, once with the label and once without
(feature-identical rows). Prints, per variant and month pair, the number of distinct
hashes present in both months. Reads data/raw/ only; writes nothing.
Run from the repository root: .venv/bin/python -m reports.final_check.duplicates
"""

from itertools import combinations

import pandas as pd

from src.data import LABEL, VARIANT_FILES, load_variant

for v in VARIANT_FILES:
    df = load_variant(v)
    for name, cols in [("with label", [c for c in df.columns if c != "month"]),
                       ("without label", [c for c in df.columns if c not in ("month", LABEL)])]:
        h = pd.util.hash_pandas_object(df[cols], index=False)
        sets = {m: set(h[df.month == m]) for m in sorted(df.month.unique())}
        shared = {(a, b): len(sets[a] & sets[b]) for a, b in combinations(sets, 2)}
        print(f"{v:12s} {name:14s} rows {len(df):,} month pairs {len(shared)} pairs with shared rows "
              f"{sum(n > 0 for n in shared.values())} max shared {max(shared.values())}")
