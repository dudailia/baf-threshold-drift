"""Item 13f of reports/code_review.md: what the checkpoints and saved predictions behind the results record.

Prints counts only. Writes nothing.
Run from the repository root: .venv/bin/python -m reports.final_check.provenance
"""

import json
from collections import Counter
from pathlib import Path

import numpy as np

from src.data import MAIN_SPLIT, VARIANT_FILES, load_variant

R = Path("results")
meta = [json.loads(p.read_text()) for p in sorted((R / "predictions").glob("*/*.json"))]
print("prediction metadata files:", len(meta))
print("sample_fraction:", dict(Counter(m["sample_fraction"] for m in meta)))
print("predictions_commit:", dict(Counter(m["predictions_commit"] for m in meta)))
for v in VARIANT_FILES:
    tun = [json.loads(line) for line in (R / "checkpoints" / "tuning" / f"{v}.jsonl").read_text().splitlines()]
    df = load_variant(v)
    n_train = int(df.month.isin(MAIN_SPLIT["train"]).sum())
    n_eval = int(df.month.isin(MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]).sum())
    rows = {len(np.load(p)["row"]) for p in sorted((R / "predictions" / v).glob("*.npz"))}
    ok_meta = {m["n_train"] for m in meta if m["variant"] == v}
    tm = [m for m in meta if m["variant"] == v and m["model"] == "lightgbm"]
    best = max(tun, key=lambda r: (r["val_tpr_at_5pct_fpr"], -r["trial"]))
    print(f"{v:12s} tuning trials {len(tun)} (ids {tun[0]['trial']}..{tun[-1]['trial']}) commits {sorted({r['predictions_commit'][:7] for r in tun})} "
          f"| n_train in metadata {sorted(ok_meta)} vs data months 0-2 {n_train:,} | rows per prediction file {sorted(rows)} vs data months 3-7 {n_eval:,} "
          f"| lightgbm config = best tuning trial {all(m['config'] == best['config'] and m['tuning_trial'] == best['trial'] for m in tm)}")

# Post hoc cache of the main-study bootstrap (results_posthoc/checkpoints/main_boot/), which make clean does not delete:
# its point estimates must equal results/metrics.csv (LightGBM seed 0, 5%, >=50) and each array must hold 1,000 resamples.
import pandas as pd  # noqa: E402

mt = pd.read_csv(R / "metrics.csv")
mt = mt[(mt.model == "lightgbm") & (mt.seed == 0) & np.isclose(mt.fpr_target, 0.05) & (mt.age_def == ">=50")].set_index(["variant", "strategy", "month"])
for v in VARIANT_FILES:
    z = np.load(Path("results_posthoc/checkpoints/main_boot") / f"{v}.npz", allow_pickle=True)
    point, boot = z["point"].item(), z["boot"].item()
    diffs = [abs(r[c] - mt.loc[(v, s, m), c]) for (s, m), r in point.items() if r["available"] for c in ("realized_fpr", "tpr", "alert_rate", "fpr_ratio")]
    sizes = {len(a["realized_fpr"]) for a in boot.values()}
    print(f"{v:12s} main_boot cells {len(point)} max |cache - metrics.csv| {max(diffs):.3g} resamples per array {sorted(sizes)}")
