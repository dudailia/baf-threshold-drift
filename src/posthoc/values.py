"""Named values for RESULTS_POSTHOC.md and the call prep, computed from results_posthoc/*.csv.

Run with: python -m src.posthoc.values   (writes results_posthoc/values.json)
"""

import json

import numpy as np
import pandas as pd

from src.posthoc.common import OUT


def config_root():
    from src import config

    return config.ROOT

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

    have = lambda *names: all((OUT / f"{n}.csv").exists() for n in names)  # noqa: E731

    if have("rolling_summary", "rolling_ci"):
        _rolling(R("rolling_summary"), R("rolling_ci"), d)
    if have("mechanism_quantiles", "mechanism_features", "mechanism_refit_check"):
        _mechanism(R("mechanism_quantiles"), R("mechanism_features"), R("mechanism_refit_check"), d)
    if have("hyper_summary", "hyper_paired"):
        _hyper(R("hyper_summary"), R("hyper_paired"), d)
    if have("retrain_summary", "retrain_paired"):
        _retrain(R("retrain_summary"), R("retrain_paired"), d)
    if have("isotonic_summary", "isotonic_paired"):
        _isotonic(R("isotonic_summary"), R("isotonic_paired"), d)
    if have("valmonth_summary", "valmonth_ci"):
        _valmonth(R("valmonth_summary"), R("valmonth_ci"), d)
    if have("fixedq_summary", "fixedq_paired", "isotonic_summary"):
        _fixedq(R("fixedq_summary"), R("fixedq_paired"), R("isotonic_summary"), d)
    psi_path = config_root() / "results" / "psi.csv"
    if psi_path.exists():
        ps = pd.read_csv(psi_path)
        cols = [f"psi_month_{m}" for m in range(3, 8)]
        top = {v: {g.loc[g[c].idxmax(), "feature"] for c in cols} for v, g in ps.groupby("variant")}
        for feat in ("velocity_4w", "credit_risk_score"):
            vs = [v for v, fs in top.items() if fs == {feat}]
            d[f"psi/{feat}/n_variants_largest"] = len(vs)
            x = ps[ps.variant.isin(vs) & (ps.feature == feat)][cols].to_numpy()
            if x.size:
                _range(x.ravel(), f"psi/{feat}/largest_variants_m3to7", d)
    main_ic = config_root() / "results" / "independent_check.csv"
    if main_ic.exists():
        m = pd.read_csv(main_ic)
        r = m[m.check.str.startswith("bootstrap width")].iloc[0]
        d["main/independent/width_ratio_median"] = float(r.median_ratio)
        d["main/independent/width_ratio_min"] = float(r.min_ratio)
        d["main/independent/width_ratio_max"] = float(r.max_ratio)
        sens = m[m.check.str.startswith("threshold at lowest")].iloc[0]
        d["check/independent/n_rows_differing"] = int(sens.rows_differing)
    if have("independent_check"):
        ic = R("independent_check")
        d["independent/max_abs_diff"] = float(ic["max_abs_diff"].max())
        d["independent/rows"] = int(ic["rows_compared"].sum())
        d["independent/mismatches"] = int(ic["mismatches"].sum())
    return d


def _rolling(s, c, d):
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


def _mechanism(q, f, rc, d):
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
    lf = f[f.month.isin(LATE)]
    d["mechanism/n_cells_m567"] = int(len(lf))
    d["mechanism/n_all_draws_shrink_m567"] = int((lf.shrink_min > 0).sum())
    d["mechanism/n_mean_shrink_positive_m567"] = int((lf.shrink_mean > 0).sum())
    best = lf.loc[lf.shrink_mean.idxmax()]
    d["mechanism/max_shrink_m567"], d["mechanism/max_shrink_feature"] = float(best.shrink_mean), str(best.feature)
    d["mechanism/max_shrink_variant"], d["mechanism/max_shrink_month"] = str(best.variant), int(best.month)
    worst = lf.loc[lf.shrink_mean.idxmin()]
    d["mechanism/min_shrink_m567"], d["mechanism/min_shrink_feature"] = float(worst.shrink_mean), str(worst.feature)
    hs = lf[lf.feature == "housing_status"].groupby("variant").shrink_mean.mean()
    if len(hs):
        _range(hs, "mechanism/housing_status/shrink_m567_by_variant", d)
    ph = lf[lf.feature == "phone_home_valid"].groupby("variant").shrink_mean.mean()
    if len(ph):
        _range(ph, "mechanism/phone_home_valid/shrink_m567_by_variant", d)
        d["mechanism/phone_home_valid/n_variants_in_top10"] = int(len(ph))
    vel = f[f.month.isin(LATE) & (f.feature == "velocity_4w")]
    if len(vel):
        _range(vel.shrink_mean, "mechanism/velocity_4w/shrink_m567", d)
        d["mechanism/velocity_4w/n_variants"] = int(vel.variant.nunique())
    cr = f[f.month.isin(LATE) & (f.feature == "credit_risk_score")]
    if len(cr):
        _range(cr.shrink_mean, "mechanism/credit_risk_score/shrink_m567", d)
        d["mechanism/credit_risk_score/n_top_feature"] = int(sum(d[k] == "credit_risk_score" for k in d if k.endswith("/top_feature")))


def _hyper(hs, hp, d):
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


def _retrain(rs, rp, d):
    m = rs[rs.metric == "budget_miss"]["mean"]
    _range(m, "retrain/miss", d)
    d["retrain/n_within_0.5pt"] = int((m.abs() <= 0.005).sum())
    d["retrain/n"] = int(len(m))
    _verdicts(rp, "retrain", d)
    to = rp[(rp.comparator == "oracle") & (rp.metric == "tpr")]["diff"]
    _range(to, "retrain/tpr_minus_oracle", d)
    tl = rp[(rp.comparator == "delayed_lag1") & (rp.metric == "tpr")]["diff"]
    _range(tl, "retrain/tpr_minus_lag1", d)


def _isotonic(i_s, ip, d):
    m = i_s[i_s.metric == "budget_miss"]["mean"]
    _range(m, "isotonic/miss", d)
    d["isotonic/n_within_0.5pt"] = int((m.abs() <= 0.005).sum())
    d["isotonic/n"] = int(len(m))
    _verdicts(ip, "isotonic", d)
    by_v = i_s[i_s.metric == "budget_miss"].groupby("variant")["mean"]
    for v, g in by_v:
        _range(g, f"isotonic/{v}/miss", d)


def main():
    from src.posthoc.hyper import REGULARISED
    from src.posthoc.mechanism import N_DRAWS

    d = build()
    (OUT / "values.json").write_text(json.dumps(d, indent=0, default=float))
    # Post hoc text constants: configuration settings quoted in the write-up (not results).
    consts = sorted({v for v in REGULARISED.values() if isinstance(v, (int, float)) and not isinstance(v, bool)} | {N_DRAWS})
    consts = sorted(set(consts) | {17})  # the day in 'Amendment 2026-10-17'
    from src.posthoc.fixedq import QS

    consts = sorted(set(consts) | {round(100 * q, 2) for q in QS})  # fixed-rule shares quoted in the write-up
    (OUT / "manifest.json").write_text(json.dumps(dict(text_constants=consts, regularised_config=REGULARISED, main_results_commit="125042c"), indent=1))
    print(f"wrote {len(d)} values")



def _valmonth(s, c, d):
    ci = c[c.metric == "budget_miss"]
    d["valmonth/n_pairs"] = int(len(ci))
    d["valmonth/n_pairs_variants"] = int(len(ci))
    d["valmonth/n_ci_below_zero"] = int((ci.hi < 0).sum())
    d["valmonth/n_ci_above_zero"] = int((ci.lo > 0).sum())
    d["valmonth/n_ci_contains_zero"] = int(((ci.lo <= 0) & (ci.hi >= 0)).sum())
    # Does the sign of the seed-mean miss at a test month depend on the threshold month?
    changes, cells = 0, 0
    for (v, t), g in s.groupby(["variant", "month"]):
        if len(g) < 2:
            continue
        cells += 1
        changes += int(len(set(np.sign(g["mean"]))) > 1)
    d["valmonth/n_test_cells_multi_m"] = cells
    d["valmonth/n_test_cells_sign_depends_on_m"] = changes
    for m, g in s.groupby("threshold_month"):
        _range(g["mean"], f"valmonth/m{m}/miss", d)
        d[f"valmonth/m{m}/n_negative"] = int((g["mean"] < 0).sum())
        d[f"valmonth/m{m}/n_positive"] = int((g["mean"] > 0).sum())
        d[f"valmonth/m{m}/n"] = int(len(g))
    for (m, t), g in s.groupby(["threshold_month", "month"]):
        _range(g["mean"], f"valmonth/m{m}/t{t}/miss", d)


def _fixedq(f, p, iso, d):
    miss = f[f.metric == "budget_miss"]
    im = iso[iso.metric == "budget_miss"]["mean"]
    for rule, g in miss.groupby("rule"):
        key = rule.replace(" ", "_").replace("%", "pct")
        _range(g["mean"], f"fixedq/{key}/miss", d)
        d[f"fixedq/{key}/n_within_0.5pt"] = int((g["mean"].abs() <= 0.005).sum())
        d[f"fixedq/{key}/n"] = int(len(g))
        q = p[p.rule == rule]
        d[f"fixedq/{key}/iso_smaller"] = int(((q.verdict == "differs") & (q["diff"] < 0)).sum())
        d[f"fixedq/{key}/iso_larger"] = int(((q.verdict == "differs") & (q["diff"] > 0)).sum())
        d[f"fixedq/{key}/inconclusive"] = int((q.verdict == "inconclusive").sum())
    best = miss.assign(a=miss["mean"].abs()).groupby("rule")["a"].mean().idxmin()
    d["fixedq/best_rule"] = best
    d["fixedq/best_rule_key"] = best.replace(" ", "_").replace("%", "pct")
    d["fixedq/isotonic/mean_abs_miss"] = float(im.abs().mean())
    d["fixedq/best_rule/mean_abs_miss"] = float(miss[miss.rule == best]["mean"].abs().mean())
    main = pd.read_csv(config_root() / "results" / "summary.csv")
    a = main[(main.model == "lightgbm") & np.isclose(main.fpr_target, 0.05) & (main.age_def == ">=50") & (main.strategy == "oracle") & (main.metric == "alert_rate")]["mean"]
    _range(a, "fixedq/oracle_alert_rate", d)


if __name__ == "__main__":
    main()
