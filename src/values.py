"""Named values for the write-up templates, computed only from results files.

Keys (used as {{value:key|fmt}} in docs/*.template.md):
  {variant}/{strategy}/{month}/{metric}            seed mean (LightGBM, 5% target, primary age)
  {variant}/{strategy}/{month}/{metric}/sd         seed standard deviation
  ci/{variant}/{strategy}/{month}/{metric}/{est|lo|hi}            seed 0 bootstrap
  paired/{variant}/{strategy}/{comparator}/{month}/{metric}/{diff|lo|hi|verdict}
  range/{strategy}/{metric}/{min|max}[/{variant set}]             over variants and test months
  checks, audit and diagnostics values under check/, audit/, diag/

Run with: python -m src.values   (writes results/values.json)
"""

import json

import numpy as np
import pandas as pd

from src import config
from src.schema import PRIMARY_AGE, PRIMARY_MODEL, PRIMARY_TARGET, VARIANTS


def _sel(df):
    return df[(df.model == PRIMARY_MODEL) & np.isclose(df.fpr_target, PRIMARY_TARGET) & (df.age_def == PRIMARY_AGE)]


def build():
    R = config.RESULTS
    v = {}
    s = _sel(pd.read_csv(R / "summary.csv"))
    for r in s.itertuples():
        k = f"{r.variant}/{r.strategy}/{r.month}/{r.metric}"
        v[k], v[k + "/sd"] = r.mean, r.sd
    ci = _sel(pd.read_csv(R / "ci.csv"))
    for r in ci[ci.seed == 0].itertuples():
        k = f"ci/{r.variant}/{r.strategy}/{r.month}/{r.metric}"
        v[k + "/est"], v[k + "/lo"], v[k + "/hi"] = r.estimate, r.lo, r.hi
    p = _sel(pd.read_csv(R / "paired.csv"))
    for r in p[p.seed == 0].itertuples():
        k = f"paired/{r.variant}/{r.strategy}/{r.comparator}/{r.month}/{r.metric}"
        v[k + "/diff"], v[k + "/lo"], v[k + "/hi"], v[k + "/verdict"] = r.diff, r.lo, r.hi, r.verdict

    groups = {"all": VARIANTS, "base_to_iii": VARIANTS[:4], "iv_v": VARIANTS[4:]}
    for strategy in s.strategy.unique():
        for metric in ("realized_fpr", "budget_miss", "abs_budget_miss", "tpr", "fpr_ratio"):
            for gname, vs in groups.items():
                x = s[(s.strategy == strategy) & (s.metric == metric) & s.variant.isin(vs)]["mean"]
                if len(x):
                    v[f"range/{strategy}/{metric}/min/{gname}"] = float(x.min())
                    v[f"range/{strategy}/{metric}/max/{gname}"] = float(x.max())

    rep = pd.read_csv(R / "replication.csv")
    for r in rep.itertuples():
        tag = "with_month" if r.with_month else "without_month"
        for c in ("best_tpr", "top5_mean_tpr", "top5_mean_fpr_ratio", "median_tpr", "n_configs"):
            v[f"check/replication/{tag}/{c}"] = getattr(r, c)
    sh = pd.read_csv(R / "shuffled.csv")
    for r in sh.itertuples():
        v[f"check/shuffled/{r.months}/oracle_tpr"] = r.oracle_tpr_at_5pct_fpr
    d = pd.read_csv(R / "diag_shuffles.csv")
    for r in d.itertuples():
        for c in ("min", "median", "max", "real_label_tpr_at_5pct_fpr", "density_score_tpr_at_5pct_fpr", "n_shuffles"):
            v[f"diag/shuffles/{r.model}/{c}"] = getattr(r, c)
    la = pd.read_csv(R / "diag_leak_audit_all.csv")
    v["diag/leak_audit/n_flagged"] = int(la.flag_for_review.sum())
    v["diag/leak_audit/max_auc"] = float(la[["auc_train_months", "auc_test_months"]].max().max())
    v["diag/leak_audit/min_auc"] = float(la[["auc_train_months", "auc_test_months"]].min().min())
    audit = json.loads((R / "audit.json").read_text())
    for k, x in audit["mean_group_size_diff"].items():
        v[f"audit/group_size_diff/{k}"] = x
    man = json.loads((R / "manifest.json").read_text())
    diag = man.get("bootstrap_diagnostics", {})
    for k, x in diag.items():
        v[f"boot/{k}"] = x
    if diag.get("ci_rows"):
        v["boot/share_outside"] = diag["ci_rows_estimate_outside_interval"] / diag["ci_rows"]
    from src.trace import _parse, extract_numbers

    # Numbers quoted verbatim from PREDICTIONS.md in the scorecard.
    v["pred/numbers_in_predictions_md"] = [_parse(t)[0] for t in extract_numbers((config.ROOT / "PREDICTIONS.md").read_text())]
    ps = pd.read_csv(R / "predictions_scored.csv")
    v["pred/n_hit"] = int((ps.result == "hit").sum())
    v["pred/n_total"] = len(ps)
    return v


def main():
    v = build()
    (config.RESULTS / "values.json").write_text(json.dumps(v, indent=0, default=float))
    print(f"wrote {len(v)} values")


if __name__ == "__main__":
    main()
