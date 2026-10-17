"""Markdown tables for RESULTS.md and the one-pager, built from results files.

These functions only select, order and format. Every displayed number is a value
stored in results/*.csv (percentages are the stored fraction times 100). Seed
statistics, intervals and verdicts are computed by the evaluation step, not here.
"""

import numpy as np
import pandas as pd

from src.plotstyle import LABELS
from src.schema import (
    DELAY_STRATEGIES,
    PRIMARY_AGE,
    PRIMARY_MODEL,
    PRIMARY_STRATEGIES,
    PRIMARY_TARGET,
    TEST_MONTHS,
    VARIANTS,
)

NA = "not available (source month is a training month)"
SECONDARY_AGE = {">=50": ">50", ">50": ">=50"}


def _md(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    return "\n".join(lines)


def _pct(v, d):
    return "n/a" if pd.isna(v) else f"{100 * v:.{d}f}"


def _pt(v, d=2):
    return "n/a" if pd.isna(v) else f"{100 * v:+.{d}f}"


def _num(v, d):
    return "n/a" if pd.isna(v) else f"{v:.{d}f}"


def _fmt(kind, v, d):
    return {"pct": _pct, "pt": lambda x, dd: _pt(x, dd), "num": _num}[kind](v, d)


def _select(df, variant=None, model=PRIMARY_MODEL, target=PRIMARY_TARGET, age=PRIMARY_AGE):
    m = (df["model"] == model) & np.isclose(df["fpr_target"], target) & (df["age_def"] == age)
    if variant is not None:
        m &= df["variant"] == variant
    return df[m]


class _Cells:
    """Lookups into summary, ci (seed 0) and metrics (seed 0) for one selection."""

    def __init__(self, results, **sel):
        self.summary = {(r.variant, r.strategy, r.month, r.metric): r for r in _select(results["summary"], **sel).itertuples()}
        ci = results["ci"]
        self.ci = {(r.variant, r.strategy, r.month, r.metric): r for r in _select(ci[ci["seed"] == 0], **sel).itertuples()}
        met = results["metrics"]
        self.meta = {(r.variant, r.strategy, r.month): r for r in _select(met[met["seed"] == 0], **sel).itertuples()}

    def available(self, v, s, m):
        r = self.meta.get((v, s, m))
        return r is not None and bool(r.available)

    def spread(self, v, s, m, metric, kind="pct", d=2):
        r = self.summary.get((v, s, m, metric))
        if r is None:
            return NA
        f = lambda x: _fmt(kind, x, d)  # noqa: E731
        return f"{f(r.mean)} ({_fmt('num', 100 * r.sd if kind != 'num' else r.sd, d)}; {f(r.min)} to {f(r.max)})"

    def mean(self, v, s, m, metric, kind="pct", d=2):
        r = self.summary.get((v, s, m, metric))
        return NA if r is None else _fmt(kind, r.mean, d)

    def interval(self, v, s, m, metric, kind="pct", d=2):
        r = self.ci.get((v, s, m, metric))
        if r is None:
            return NA
        f = lambda x: _fmt(kind, x, d)  # noqa: E731
        return f"{f(r.estimate)} [{f(r.lo)}, {f(r.hi)}]"

    def source_note(self, v, s, m):
        r = self.meta.get((v, s, m))
        if s.startswith("delayed") and r is not None and r.available and r.source_month == 3:
            return " (equals static: source month 3)"
        return ""


def headline(results, variant):
    c = _Cells(results, variant=variant)
    header = [
        "Strategy", "Month",
        "Realized FPR %, seed mean (sd; min to max)",
        "Budget miss pt, seed 0 [95% CI]",
        "TPR %, seed mean (sd; min to max)",
        "TPR %, seed 0 [95% CI]",
        "Alert volume %, seed mean",
        "Precision %, seed mean",
    ]
    rows = []
    for s in PRIMARY_STRATEGIES:
        for m in TEST_MONTHS:
            if not c.available(variant, s, m):
                rows.append([LABELS[s], m] + [NA] * 6)
                continue
            rows.append([
                LABELS[s] + c.source_note(variant, s, m), m,
                c.spread(variant, s, m, "realized_fpr"),
                c.interval(variant, s, m, "budget_miss", "pt"),
                c.spread(variant, s, m, "tpr", d=1),
                c.interval(variant, s, m, "tpr", d=1),
                c.mean(variant, s, m, "alert_rate"),
                c.mean(variant, s, m, "precision", d=1),
            ])
    return _md(header, rows)


def fairness(results, variant):
    c = _Cells(results, variant=variant)
    header = ["Strategy", "Month", "Realized FPR %, seed mean", "FPR younger %, seed mean", "FPR older %, seed mean",
              "FPR ratio, seed mean (sd; min to max)", "FPR ratio, seed 0 [95% CI]"]
    rows = []
    for s in PRIMARY_STRATEGIES:
        for m in TEST_MONTHS:
            if not c.available(variant, s, m):
                rows.append([LABELS[s], m] + [NA] * 5)
                continue
            rows.append([LABELS[s], m, c.mean(variant, s, m, "realized_fpr"), c.mean(variant, s, m, "fpr_young"),
                         c.mean(variant, s, m, "fpr_old"), c.spread(variant, s, m, "fpr_ratio", "num", 3),
                         c.interval(variant, s, m, "fpr_ratio", "num", 3)])
    return _md(header, rows)


def alert_shares(results, variant):
    c = _Cells(results, variant=variant)
    header = ["Strategy", "Month", "Older share of applications %", "Older share of alerts %, seed mean",
              "Younger share of applications %", "Younger share of alerts %, seed mean"]
    rows = []
    for s in ["label_free_top", "label_free_val_rate", "static"]:
        for m in TEST_MONTHS:
            rows.append([LABELS[s], m, c.mean(variant, s, m, "application_share_old", d=1), c.mean(variant, s, m, "alert_share_old", d=1),
                         c.mean(variant, s, m, "application_share_young", d=1), c.mean(variant, s, m, "alert_share_young", d=1)])
    return _md(header, rows)


def delay_sweep(results, variant):
    c = _Cells(results, variant=variant)
    header = ["Strategy", "Month", "Realized FPR %, seed mean (sd; min to max)", "Budget miss pt, seed 0 [95% CI]",
              "TPR %, seed mean (sd; min to max)"]
    rows = []
    for s in DELAY_STRATEGIES:
        for m in TEST_MONTHS:
            if not c.available(variant, s, m):
                rows.append([LABELS[s], m, NA, "", ""])
                continue
            rows.append([LABELS[s] + c.source_note(variant, s, m), m, c.spread(variant, s, m, "realized_fpr"),
                         c.interval(variant, s, m, "budget_miss", "pt"), c.spread(variant, s, m, "tpr", d=1)])
    return _md(header, rows)


_PAIRED_FMT = {"abs_budget_miss": ("pt", 2, "absolute budget miss, pt"), "tpr": ("pt", 1, "TPR, pt"), "fpr_ratio": ("num", 3, "FPR ratio")}


def paired(results, variant):
    p = _select(results["paired"], variant=variant)
    p = p[(p["seed"] == 0) & (p["comparator"] == "static")]
    header = ["Strategy", "Month", "Metric", "Strategy minus static, seed 0 [95% paired CI]", "Verdict"]
    rows = []
    order = {s: i for i, s in enumerate(PRIMARY_STRATEGIES + DELAY_STRATEGIES)}
    for r in sorted(p.itertuples(), key=lambda r: (order.get(r.strategy, 99), r.month, r.metric)):
        kind, d, name = _PAIRED_FMT[r.metric]
        f = lambda x: _fmt(kind, x, d)  # noqa: E731
        rows.append([LABELS[r.strategy], r.month, name, f"{f(r.diff)} [{f(r.lo)}, {f(r.hi)}]", r.verdict])
    return _md(header, rows)


def small_cells(results, arg=None):
    met = results["metrics"]
    met = met[(met["seed"] == 0) & np.isclose(met["fpr_target"], PRIMARY_TARGET) & met["available"]]
    ci = results["ci"]
    ci = ci[ci["seed"] == 0].set_index(["variant", "model", "fpr_target", "age_def", "strategy", "month", "metric"])
    header = ["Variant", "Model", "Age definition", "Strategy", "Month", "Group", "Positives", "Group TPR %, seed 0 [95% CI]"]
    rows = []
    for r in met.itertuples():
        for group in ("young", "old"):
            if not getattr(r, f"small_cell_{group}"):
                continue
            k = (r.variant, r.model, r.fpr_target, r.age_def, r.strategy, r.month, f"tpr_{group}")
            iv = ci.loc[k]
            rows.append([r.variant, r.model, r.age_def, LABELS[r.strategy], r.month, "younger" if group == "young" else "older",
                         getattr(r, f"n_pos_{group}"), f"{_pct(iv.estimate, 1)} [{_pct(iv.lo, 1)}, {_pct(iv.hi, 1)}]"])
    if not rows:
        return "No month and age-group cell has fewer than 30 positives."
    return _md(header, rows)


def model_comparison(results, variant=None):
    lg = _Cells(results, model="lightgbm")
    lr = _Cells(results, model="logreg")
    header = ["Variant", "Strategy", "Month", "LightGBM realized FPR %", "LightGBM TPR %", "Logistic regression realized FPR %",
              "Logistic regression TPR %"]
    rows = []
    for v in [variant] if variant else VARIANTS:
        for s in PRIMARY_STRATEGIES:
            for m in TEST_MONTHS:
                if (v, s, m) not in lg.meta:
                    continue
                rows.append([v, LABELS[s], m, lg.mean(v, s, m, "realized_fpr"), lg.mean(v, s, m, "tpr", d=1),
                             lr.mean(v, s, m, "realized_fpr"), lr.mean(v, s, m, "tpr", d=1)])
    return _md(header, rows)


def age_sensitivity(results, variant=None):
    other = SECONDARY_AGE[PRIMARY_AGE]
    a = _Cells(results, age=PRIMARY_AGE)
    b = _Cells(results, age=other)
    header = ["Variant", "Strategy", "Month", f"FPR ratio, older {PRIMARY_AGE} (primary)", f"FPR ratio, older {other}",
              f"Older share of alerts %, {PRIMARY_AGE}", f"Older share of alerts %, {other}"]
    rows = []
    for v in [variant] if variant else VARIANTS:
        for s in PRIMARY_STRATEGIES:
            for m in TEST_MONTHS:
                if (v, s, m) not in a.meta:
                    continue
                rows.append([v, LABELS[s], m, a.mean(v, s, m, "fpr_ratio", "num", 3), b.mean(v, s, m, "fpr_ratio", "num", 3),
                             a.mean(v, s, m, "alert_share_old", d=1), b.mean(v, s, m, "alert_share_old", d=1)])
    return _md(header, rows)


def exploratory_targets(results, variant=None):
    header = ["Variant", "FPR target % (exploratory)", "Strategy", "Month", "Realized FPR %, seed mean", "Budget miss pt, seed mean",
              "TPR %, seed mean"]
    rows = []
    targets = sorted(t for t in results["summary"]["fpr_target"].unique() if not np.isclose(t, PRIMARY_TARGET))
    for t in targets:
        c = _Cells(results, target=t)
        for v in [variant] if variant else VARIANTS:
            for s in PRIMARY_STRATEGIES:
                for m in TEST_MONTHS:
                    if not c.available(v, s, m):
                        continue
                    rows.append([v, _pct(t, 0), LABELS[s], m, c.mean(v, s, m, "realized_fpr"), c.mean(v, s, m, "budget_miss", "pt"),
                                 c.mean(v, s, m, "tpr", d=1)])
    return _md(header, rows) if rows else "No exploratory targets in the results."


def csv_table(results, name):
    """A small results file shown as is, floats to 4 significant decimals."""
    df = results[name]
    rows = [[f"{x:.4f}" if isinstance(x, float) else x for x in r] for r in df.itertuples(index=False)]
    return _md(list(df.columns), rows)


TABLES = {
    "headline": headline,
    "fairness": fairness,
    "alert_shares": alert_shares,
    "delay_sweep": delay_sweep,
    "paired": paired,
    "small_cells": small_cells,
    "model_comparison": model_comparison,
    "age_sensitivity": age_sensitivity,
    "exploratory_targets": exploratory_targets,
    "csv": csv_table,
}


def budget_overview(results, variant=None):
    """Signed budget miss per deployable strategy and the oracle, seed mean, with the paired verdict against static."""
    c = _Cells(results)
    p = _select(results["paired"])
    p = p[(p.seed == 0) & (p.comparator == "static") & (p.metric == "abs_budget_miss")]
    verdicts = {(r.variant, r.strategy, r.month): r.verdict for r in p.itertuples()}
    strategies = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "oracle"]
    header = ["Variant", "Month"] + [f"{LABELS[s]}, budget miss pt" for s in strategies] + \
             [f"{LABELS[s]} vs static, absolute miss" for s in ("label_free_top", "label_free_val_rate", "delayed_lag1")]
    rows = []
    for v in [variant] if variant else VARIANTS:
        for m in TEST_MONTHS:
            if (v, "static", m) not in c.meta:
                continue
            rows.append([v, m] + [c.mean(v, s, m, "budget_miss", "pt") for s in strategies]
                        + [verdicts.get((v, s, m), "n/a") for s in ("label_free_top", "label_free_val_rate", "delayed_lag1")])
    return _md(header, rows)


def groupwise(results, variant=None):
    """Exploratory diagnostics that use the protected attribute at decision time; not recommendations."""
    c = _Cells(results)
    header = ["Variant", "Strategy", "Month", "Realized FPR %, seed mean", "TPR %, seed mean", "FPR younger %", "FPR older %", "FPR ratio"]
    rows = []
    for v in [variant] if variant else VARIANTS:
        for s in ("static", "groupwise_static", "label_free_top", "groupwise_label_free"):
            for m in TEST_MONTHS:
                if (v, s, m) not in c.meta:
                    continue
                rows.append([v, LABELS[s], m, c.mean(v, s, m, "realized_fpr"), c.mean(v, s, m, "tpr", d=1), c.mean(v, s, m, "fpr_young"),
                             c.mean(v, s, m, "fpr_old"), c.mean(v, s, m, "fpr_ratio", "num", 3)])
    return _md(header, rows)


def predictions(results, arg=None):
    """PREDICTIONS.md line by line, with the result under the rules declared in PROTOCOL.md."""
    from src.predictions_eval import prediction_texts

    texts = prediction_texts()
    ps = results["predictions_scored"]
    rows = [[r.prediction, texts[r.prediction], r.result, r.detail] for r in ps.itertuples()]
    return _md(["#", "Prediction (verbatim, PREDICTIONS.md)", "Result", "What happened (seed means)"], rows)


TABLES.update(budget_overview=budget_overview, groupwise=groupwise, predictions=predictions)
