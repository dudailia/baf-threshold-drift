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


DEPLOY = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1"]
GLOBAL = DEPLOY + ["oracle"]


def derived(s, p, full):
    """Summaries over variants and months, computed from seed means in summary.csv."""
    d = {}
    m = s.pivot_table(index=["variant", "month", "strategy"], columns="metric", values="mean")

    def col(strategy, metric, months=(4, 5, 6, 7), variants=VARIANTS):
        x = m.xs(strategy, level="strategy")[metric]
        return x[x.index.get_level_values("variant").isin(variants) & x.index.get_level_values("month").isin(months)]

    for name, months in (("m4", (4,)), ("m567", (5, 6, 7)), ("all", (4, 5, 6, 7))):
        for strategy in GLOBAL:
            x = col(strategy, "budget_miss", months)
            d[f"derived/{strategy}/miss_{name}/min"], d[f"derived/{strategy}/miss_{name}/max"] = float(x.min()), float(x.max())
            ax = x.abs()
            d[f"derived/{strategy}/absmiss_{name}/max"] = float(ax.max())
            d[f"derived/{strategy}/absmiss_{name}/n_within_0.5pt"] = int((ax <= 0.005).sum())
            d[f"derived/{strategy}/absmiss_{name}/n_cells"] = int(len(ax))
    # Which deployable strategy has the smallest absolute miss in each variant-month.
    absmiss = m["abs_budget_miss"].unstack("strategy")[DEPLOY]
    best = absmiss.idxmin(axis=1)
    for strategy in DEPLOY:
        d[f"derived/{strategy}/n_smallest_absmiss"] = int((best == strategy).sum())
    # Paired verdicts against static on absolute miss.
    pv = p[(p.seed == 0) & (p.comparator == "static") & (p.metric == "abs_budget_miss")]
    for strategy in ("label_free_top", "label_free_val_rate", "delayed_lag1"):
        q = pv[pv.strategy == strategy]
        d[f"derived/{strategy}/vs_static/n_differs_smaller"] = int(((q.verdict == "differs") & (q["diff"] < 0)).sum())
        d[f"derived/{strategy}/vs_static/n_differs_larger"] = int(((q.verdict == "differs") & (q["diff"] > 0)).sum())
        d[f"derived/{strategy}/vs_static/n_inconclusive"] = int((q.verdict == "inconclusive").sum())
    # Spread of the FPR ratio across global-threshold strategies, within a variant-month.
    ratio = m["fpr_ratio"].unstack("strategy")[GLOBAL]
    spread = ratio.max(axis=1) - ratio.min(axis=1)
    d["derived/ratio_spread_across_strategies/max"] = float(spread.max())
    for vname in VARIANTS:
        r = ratio.loc[vname]
        d[f"derived/{vname}/ratio_global/min"], d[f"derived/{vname}/ratio_global/max"] = float(r.min().min()), float(r.max().max())
        for strategy in ("groupwise_static", "groupwise_label_free"):
            g = col(strategy, "fpr_ratio", variants=[vname])
            d[f"derived/{vname}/{strategy}/ratio/min"], d[f"derived/{vname}/{strategy}/ratio/max"] = float(g.min()), float(g.max())
        for strategy in GLOBAL:
            t = col(strategy, "tpr", variants=[vname])
            d[f"derived/{vname}/{strategy}/tpr_m45"] = float(t[t.index.get_level_values("month").isin([4, 5])].mean())
            d[f"derived/{vname}/{strategy}/tpr_m67"] = float(t[t.index.get_level_values("month").isin([6, 7])].mean())
        sh = col("label_free_top", "alert_share_old", (6, 7), [vname])
        d[f"derived/{vname}/label_free_top/alert_share_old_m67/min"] = float(sh.min())
        d[f"derived/{vname}/label_free_top/alert_share_old_m67/max"] = float(sh.max())
        ap = col("label_free_top", "application_share_old", (6, 7), [vname])
        d[f"derived/{vname}/application_share_old_m67/max"] = float(ap.max())
    for vname in VARIANTS:
        fpr = col("static", "realized_fpr", variants=[vname])
        mo = fpr.index.get_level_values("month")
        d[f"derived/{vname}/static/fpr_m45"] = float(fpr[mo.isin([4, 5])].mean())
        d[f"derived/{vname}/static/fpr_m67"] = float(fpr[mo.isin([6, 7])].mean())
        for lag in ("delayed_lag1", "delayed_lag2", "delayed_lag3"):
            x = col(lag, "budget_miss", variants=[vname])
            d[f"derived/{vname}/{lag}/miss/min"], d[f"derived/{vname}/{lag}/miss/max"] = float(x.min()), float(x.max())
    gw = pd.concat([col(st, "fpr_ratio") for st in ("groupwise_static", "groupwise_label_free")])
    d["derived/groupwise/ratio/min"], d["derived/groupwise/ratio/max"] = float(gw.min()), float(gw.max())
    # TPR cost of group-wise label-free against label-free top 5%.
    cost = col("groupwise_label_free", "tpr") - col("label_free_top", "tpr")
    d["derived/groupwise_label_free_minus_label_free_top/tpr/min"] = float(cost.min())
    d["derived/groupwise_label_free_minus_label_free_top/tpr/max"] = float(cost.max())
    # Secondary: logistic regression static miss, and the > 50 age definition FPR ratio range.
    lr = full[(full.model == "logreg") & np.isclose(full.fpr_target, PRIMARY_TARGET) & (full.age_def == PRIMARY_AGE)
              & (full.strategy == "static") & (full.metric == "budget_miss") & full.month.isin([5, 6, 7])]["mean"]
    d["derived/logreg/static/miss_m567/min"], d["derived/logreg/static/miss_m567/max"] = float(lr.min()), float(lr.max())
    alt = full[(full.model == PRIMARY_MODEL) & np.isclose(full.fpr_target, PRIMARY_TARGET) & (full.age_def == ">50")
               & full.strategy.isin(GLOBAL) & (full.metric == "fpr_ratio")]["mean"]
    d["derived/age_gt50/ratio_global/min"], d["derived/age_gt50/ratio_global/max"] = float(alt.min()), float(alt.max())
    a = full[(full.model == PRIMARY_MODEL) & np.isclose(full.fpr_target, PRIMARY_TARGET) & (full.age_def == ">50")
             & full.strategy.isin(GLOBAL) & (full.metric == "fpr_ratio")].pivot_table(index=["variant", "month"], columns="strategy", values="mean")
    d["derived/age_gt50/ratio_spread_across_strategies/max"] = float((a.max(axis=1) - a.min(axis=1)).max())
    for t in (0.01, 0.02, 0.10):
        e = full[(full.model == PRIMARY_MODEL) & np.isclose(full.fpr_target, t) & (full.age_def == PRIMARY_AGE) & (full.strategy == "static")
                 & (full.metric == "budget_miss") & full.month.isin([5, 6, 7])]
        d[f"derived/target_{t}/static/m567_under/n"] = int((e["mean"] < 0).sum())
        d[f"derived/target_{t}/static/m567/n"] = int(len(e))
        d[f"derived/target_{t}/static/m567_under_base/n"] = int((e[e.variant == "Base"]["mean"] < 0).sum())
    return d


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

    v.update(derived(s, p, pd.read_csv(R / "summary.csv")))
    c0 = ci[(ci.seed == 0) & (ci.metric == "budget_miss") & ci.month.isin([5, 6, 7])]
    for strategy in ("static", "label_free_top"):
        q = c0[c0.strategy == strategy]
        v[f"derived/{strategy}/ci_m567_below_zero"] = int((q.hi < 0).sum())
        v[f"derived/{strategy}/ci_m567_n"] = int(len(q))
    v["predictions_commit"] = str(s["predictions_commit"].iloc[0])
    ic = pd.read_csv(R / "independent_check.csv")
    v["check/independent/tpr_sensitivity"] = float(ic["max_abs_diff_tpr"].max())
    v["check/independent/n_rows"] = int(ic["rows_compared"].iloc[0])

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
