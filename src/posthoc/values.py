"""Named values for RESULTS_POSTHOC.md and the call prep, computed from results_posthoc/*.csv.

Run with: python -m src.posthoc.values   (writes results_posthoc/values.json)
"""

import json

import numpy as np
import pandas as pd

from src.posthoc.common import OUT

LATE = [5, 6, 7]


def _verdicts(p, prefix, d, strategy_col="comparator"):
    q = p[p.metric == "abs_budget_miss"]
    for comp, g in q.groupby(strategy_col):
        d[f"{prefix}/vs/{comp}/n_differs_smaller"] = int(((g.verdict == "differs") & (g["diff"] < 0)).sum())
        d[f"{prefix}/vs/{comp}/n_differs_larger"] = int(((g.verdict == "differs") & (g["diff"] > 0)).sum())
        d[f"{prefix}/vs/{comp}/n_inconclusive"] = int((g.verdict == "inconclusive").sum())
        d[f"{prefix}/vs/{comp}/n"] = int(len(g))


def _range(x, key, d):
    d[f"{key}/min"], d[f"{key}/max"] = float(np.min(x)), float(np.max(x))


def build():
    d = {}
    R = lambda name: pd.read_csv(OUT / f"{name}.csv")  # noqa: E731

    s, c = R("rolling_summary"), R("rolling_ci")
    for split in sorted(s.split.unique()):
        for strategy in ("static", "label_free_top", "delayed_lag1", "oracle"):
            x = s[(s.split == split) & (s.strategy == strategy) & (s.metric == "budget_miss")]
            _range(x["mean"], f"rolling/{split}/{strategy}/miss_all", d)
            late = x[x.month.isin(LATE)]["mean"]
            _range(late, f"rolling/{split}/{strategy}/miss_m567", d)
            ci = c[(c.split == split) & (c.strategy == strategy) & (c.metric == "budget_miss") & c.month.isin(LATE)]
            d[f"rolling/{split}/{strategy}/ci_m567_below_zero"] = int((ci.hi < 0).sum())
            d[f"rolling/{split}/{strategy}/ci_m567_above_zero"] = int((ci.lo > 0).sum())
            d[f"rolling/{split}/{strategy}/ci_m567_n"] = int(len(ci))
        early = s[(s.split == split) & (s.strategy == "static") & (s.metric == "budget_miss") & ~s.month.isin(LATE)]["mean"]
        if len(early):
            _range(early, f"rolling/{split}/static/miss_early", d)
        t = s[(s.split == split) & (s.strategy == "oracle") & (s.metric == "tpr")]
        for v, g in t.groupby("variant"):
            d[f"rolling/{split}/{v}/oracle_tpr_m67"] = float(g[g.month.isin([6, 7])]["mean"].mean())

    q, f, rc = R("mechanism_quantiles"), R("mechanism_features"), R("mechanism_refit_check")
    d["mechanism/refit_max_abs_diff"] = float(rc.max_abs_diff_refit_vs_saved.max())
    test = q[q.month >= 4]
    _range(test.ks_vs_month3_negatives, "mechanism/ks", d)
    _range(test.threshold_quantile_in_negatives, "mechanism/quantile", d)
    late = test[test.month.isin(LATE)]
    _range(late.ks_vs_month3_negatives, "mechanism/ks_m567", d)
    corr = np.corrcoef(test.ks_vs_month3_negatives, test.realized_fpr - 0.05)[0, 1]
    d["mechanism/corr_ks_vs_miss"] = float(corr)
    for v, g in f[f.month.isin(LATE)].groupby("variant"):
        by = g.groupby("feature")["shrink_mean"].mean().sort_values(ascending=False)
        d[f"mechanism/{v}/top_feature"] = str(by.index[0])
        d[f"mechanism/{v}/top_feature_shrink_m567_mean"] = float(by.iloc[0])
        d[f"mechanism/{v}/second_feature"] = str(by.index[1])
        d[f"mechanism/{v}/second_feature_shrink_m567_mean"] = float(by.iloc[1])
        d[f"mechanism/{v}/static_absmiss_m567_mean"] = float(g.groupby("month").static_miss.first().abs().mean())
    cr = f[f.month.isin(LATE) & (f.feature == "credit_risk_score")]
    if len(cr):
        _range(cr.shrink_mean, "mechanism/credit_risk_score/shrink_m567", d)
        d["mechanism/credit_risk_score/n_top_feature"] = int(sum(d[k] == "credit_risk_score" for k in d if k.endswith("/top_feature")))

    hs, hp = R("hyper_summary"), R("hyper_paired")
    miss = hs[hs.metric == "budget_miss"]
    ref = miss[miss.config_rank == 0].set_index(["variant", "month"])["mean"]
    other = miss[miss.config_rank > 0]
    sign_change = [(np.sign(r["mean"]) != np.sign(ref.loc[(r.variant, r.month)])) for _, r in other.iterrows()]
    d["hyper/n_sign_change"] = int(np.sum(sign_change))
    d["hyper/n_cells"] = int(len(other))
    late_o = other[other.month.isin(LATE)]
    d["hyper/n_sign_change_m567"] = int(np.sum([(np.sign(r["mean"]) != np.sign(ref.loc[(r.variant, r.month)])) for _, r in late_o.iterrows()]))
    d["hyper/n_cells_m567"] = int(len(late_o))
    _range(late_o["mean"], "hyper/static_miss_m567", d)
    reg = late_o[late_o.config_label == "strongly regularised"]
    _range(reg["mean"], "hyper/regularised/static_miss_m567", d)
    tuned = late_o[late_o.config_label != "strongly regularised"]
    _range(tuned["mean"], "hyper/tuned/static_miss_m567", d)
    diff = [abs(r["mean"] - ref.loc[(r.variant, r.month)]) for _, r in other.iterrows()]
    d["hyper/max_abs_change"] = float(np.max(diff))
    _verdicts(hp.assign(comparator=np.where(hp.config_label == "strongly regularised", "regularised", "tuned")), "hyper", d)

    rs, rp = R("retrain_summary"), R("retrain_paired")
    m = rs[rs.metric == "budget_miss"]["mean"]
    _range(m, "retrain/miss", d)
    d["retrain/n_within_0.5pt"] = int((m.abs() <= 0.005).sum())
    d["retrain/n"] = int(len(m))
    _verdicts(rp, "retrain", d)
    to = rp[(rp.comparator == "oracle") & (rp.metric == "tpr")]["diff"]
    _range(to, "retrain/tpr_minus_oracle", d)
    tl = rp[(rp.comparator == "delayed_lag1") & (rp.metric == "tpr")]["diff"]
    _range(tl, "retrain/tpr_minus_lag1", d)

    i_s, ip = R("isotonic_summary"), R("isotonic_paired")
    m = i_s[i_s.metric == "budget_miss"]["mean"]
    _range(m, "isotonic/miss", d)
    d["isotonic/n_within_0.5pt"] = int((m.abs() <= 0.005).sum())
    d["isotonic/n"] = int(len(m))
    _verdicts(ip, "isotonic", d)
    by_v = i_s[i_s.metric == "budget_miss"].groupby("variant")["mean"]
    for v, g in by_v:
        _range(g, f"isotonic/{v}/miss", d)
    for name in ("independent_check",):
        path = OUT / f"{name}.csv"
        if path.exists():
            ic = pd.read_csv(path)
            d["independent/max_abs_diff"] = float(ic["max_abs_diff"].max())
            d["independent/rows"] = int(ic["rows_compared"].sum())
            d["independent/mismatches"] = int(ic["mismatches"].sum())
    return d


def main():
    d = build()
    (OUT / "values.json").write_text(json.dumps(d, indent=0, default=float))
    print(f"wrote {len(d)} values")


if __name__ == "__main__":
    main()
