"""Tables for RESULTS_POSTHOC.md. Format only: every number is stored in results_posthoc/*.csv.

All post hoc. TPR is shown with realized FPR; the oracle is an upper bound, not deployable.
"""

import numpy as np

from src.plotstyle import LABELS
from src.tables import NA, _md, _pct, _pt, _num

LABELS = {**LABELS, "retrain_threshold_prev_month": "Retrained, threshold from month t-1 (exploratory)",
          "label_free_isotonic": "Label-free, isotonic estimated FPR (exploratory)"}
VARIANTS = ["Base", "Variant I", "Variant II", "Variant III", "Variant IV", "Variant V"]


def _idx(summary, keys):
    return {tuple(getattr(r, k) for k in keys) + (r.metric,): r for r in summary.itertuples()}


def _ci_idx(ci, keys):
    c = ci[ci.seed == ci.seed.min()]
    return {tuple(getattr(r, k) for k in keys) + (r.metric,): r for r in c.itertuples()}


def _spread(r, kind="pct", d=2):
    if r is None:
        return NA
    f = {"pct": lambda x: _pct(x, d), "pt": lambda x: _pt(x, d), "num": lambda x: _num(x, d)}[kind]
    sd = _num(100 * r.sd if kind != "num" else r.sd, d)
    return f"{f(r.mean)} ({sd}; {f(r.min)} to {f(r.max)})"


def _iv(r, kind="pt", d=2):
    if r is None:
        return NA
    f = {"pct": lambda x: _pct(x, d), "pt": lambda x: _pt(x, d), "num": lambda x: _num(x, d)}[kind]
    return f"{f(r.estimate)} [{f(r.lo)}, {f(r.hi)}]"


def rolling(results, split):
    s = results["rolling_summary"]
    s = s[s.split == split]
    c = results["rolling_ci"]
    c = c[c.split == split]
    S, C = _idx(s, ["variant", "strategy", "month"]), _ci_idx(c, ["variant", "strategy", "month"])
    strategies = ["static", "label_free_top", "delayed_lag1", "oracle"]
    header = ["Variant", "Month"] + sum([[f"{LABELS[x]}: realized FPR %, seed mean (sd; min to max)", f"{LABELS[x]}: budget miss pt, seed 0 [95% CI]",
                                         f"{LABELS[x]}: TPR %, seed mean"] for x in strategies], [])
    rows = []
    for v in VARIANTS:
        for m in sorted(s.month.unique()):
            row = [v, m]
            for x in strategies:
                if (v, x, m, "realized_fpr") not in S:
                    row += [NA, "", ""]
                    continue
                row += [_spread(S[(v, x, m, "realized_fpr")]), _iv(C.get((v, x, m, "budget_miss"))), _pct(S[(v, x, m, "tpr")].mean, 1)]
            rows.append(row)
    return _md(header, rows)


def mechanism_quantiles(results, arg=None):
    q = results["mechanism_quantiles"]
    header = ["Variant", "Month", "Quantile of month's negative scores at month 3's static threshold", "Realized FPR %", "KS distance to month 3 negatives"]
    rows = [[r.variant, r.month, _num(r.threshold_quantile_in_negatives, 4), _pct(r.realized_fpr, 2), _num(r.ks_vs_month3_negatives, 4)] for r in q.itertuples()]
    return _md(header, rows)


def mechanism_features(results, variant):
    f = results["mechanism_features"]
    f = f[f.variant == variant]
    months = sorted(f.month.unique())
    header = ["Rank", "Feature"] + [f"Month {m}: static miss pt; shrink pt, mean (min to max) over draws" for m in months]
    rows = []
    for (rank, feat), g in f.groupby(["rank", "feature"], sort=True):
        row = [rank, f"`{feat}`"]
        for m in months:
            r = g[g.month == m].iloc[0]
            row.append(f"{_pt(r.static_miss)}; {_pt(r.shrink_mean)} ({_pt(r.shrink_min)} to {_pt(r.shrink_max)})")
        rows.append(row)
    return _md(header, rows)


def hyper(results, variant):
    s = results["hyper_summary"]
    s = s[(s.variant == variant) & (s.metric.isin(["budget_miss", "tpr", "realized_fpr"]))]
    c = results["hyper_ci"]
    c = c[(c.variant == variant)]
    p = results["hyper_paired"]
    p = p[(p.variant == variant) & (p.metric == "abs_budget_miss")]
    S, C = _idx(s, ["config_label", "month"]), _ci_idx(c, ["config_label", "month"])
    P = {(r.config_label, r.month): r for r in p.itertuples()}
    header = ["Configuration", "Month", "Static realized FPR %, seed mean (sd; min to max)", "Static budget miss pt, seed 0 [95% CI]",
              "Static TPR %, seed mean", "Absolute miss vs rank 1, seed 0 [paired 95% CI]", "Verdict"]
    order = sorted(s.config_label.unique(), key=lambda x: (x.startswith("strongly"), x))
    rows = []
    for cfg in order:
        for m in sorted(s.month.unique()):
            pr = P.get((cfg, m))
            rows.append([cfg, m, _spread(S.get((cfg, m, "realized_fpr"))), _iv(C.get((cfg, m, "budget_miss"))), _pct(S[(cfg, m, "tpr")].mean, 1),
                         "reference" if pr is None else f"{_pt(pr.diff)} [{_pt(pr.lo)}, {_pt(pr.hi)}]", "" if pr is None else pr.verdict])
    return _md(header, rows)


def _vs(results, name, strategy):
    s = results[f"{name}_summary"]
    c = results[f"{name}_ci"]
    p = results[f"{name}_paired"]
    S, C = _idx(s, ["variant", "month"]), _ci_idx(c, ["variant", "month"])
    P = {(r.variant, r.month, r.comparator, r.metric): r for r in p.itertuples()}
    return S, C, P


def retrain(results, arg=None):
    S, C, P = _vs(results, "retrain", "retrain_threshold_prev_month")
    comps = ["static", "delayed_lag1", "label_free_val_rate"]
    header = ["Variant", "Month", "Realized FPR %, seed mean (sd; min to max)", "Budget miss pt, seed 0 [95% CI]", "TPR %, seed 0 [95% CI]"] + \
             [f"Absolute miss vs {LABELS[x]}: diff pt [paired CI], verdict" for x in comps] + ["TPR vs Oracle (upper bound): diff pt [paired CI]"]
    rows = []
    for v in VARIANTS:
        for m in (5, 6, 7):
            if (v, m, "realized_fpr") not in S:
                continue
            row = [v, m, _spread(S[(v, m, "realized_fpr")]), _iv(C.get((v, m, "budget_miss"))), _iv(C.get((v, m, "tpr")), "pct", 1)]
            for x in comps:
                r = P[(v, m, x, "abs_budget_miss")]
                row.append(f"{_pt(r.diff)} [{_pt(r.lo)}, {_pt(r.hi)}], {r.verdict}")
            r = P[(v, m, "oracle", "tpr")]
            row.append(f"{_pt(r.diff, 1)} [{_pt(r.lo, 1)}, {_pt(r.hi, 1)}]")
            rows.append(row)
    return _md(header, rows)


def isotonic(results, arg=None):
    S, C, P = _vs(results, "isotonic", "label_free_isotonic")
    comps = ["label_free_top", "label_free_val_rate", "static"]
    header = ["Variant", "Month", "Realized FPR %, seed mean (sd; min to max)", "Budget miss pt, seed 0 [95% CI]", "TPR %, seed mean"] + \
             [f"Absolute miss vs {LABELS[x]}: diff pt [paired CI], verdict" for x in comps]
    rows = []
    for v in VARIANTS:
        for m in (4, 5, 6, 7):
            if (v, m, "realized_fpr") not in S:
                continue
            row = [v, m, _spread(S[(v, m, "realized_fpr")]), _iv(C.get((v, m, "budget_miss"))), _pct(S[(v, m, "tpr")].mean, 1)]
            for x in comps:
                r = P[(v, m, x, "abs_budget_miss")]
                row.append(f"{_pt(r.diff)} [{_pt(r.lo)}, {_pt(r.hi)}], {r.verdict}")
            rows.append(row)
    return _md(header, rows)


POSTHOC_TABLES = dict(rolling=rolling, mechanism_quantiles=mechanism_quantiles, mechanism_features=mechanism_features,
                      hyper=hyper, retrain=retrain, isotonic=isotonic)
