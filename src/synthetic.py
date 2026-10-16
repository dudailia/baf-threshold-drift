"""Synthetic mechanism study: threshold strategies under controlled score shifts.

Synthetic, not BAF. Scores are binormal (unit variance) within each group, with
known means, group shares and prevalences. Month 0 is the reference
(validation) month; a shift, if any, starts in month 1. The strategies are
the ones in PROTOCOL.md, applied to the same scores, so every operating point
lies on that month's ROC curve.

Run with: python -m src.synthetic
"""

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from src.metrics import confusion, fpr_ratio, rates
from src.thresholds import flag, threshold_at_fpr, threshold_top_fraction

TARGET = 0.05
STRATEGIES = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "oracle"]


@dataclass(frozen=True)
class MonthSpec:
    group_share: dict
    prevalence: dict
    neg_mean: dict
    pos_mean: dict


def simulate_month(spec, n, rng):
    groups = list(spec.group_share)
    gi = rng.choice(len(groups), size=n, p=[spec.group_share[k] for k in groups])
    prev, pos, neg = (np.array([d[k] for k in groups])[gi] for d in (spec.prevalence, spec.pos_mean, spec.neg_mean))
    y = (rng.random(n) < prev).astype(int)
    mean = np.where(y == 1, pos, neg)
    return pd.DataFrame({"score": rng.normal(mean, 1.0), "label": y, "group": np.array(groups)[gi]})


def _evaluate(df, t):
    r = rates(confusion(df["score"], df["label"], t))
    row = dict(fpr=r["fpr"], tpr=r["tpr"], alert_share=r["alert_rate"], prevalence=df["label"].mean())
    alerts = flag(df["score"], t)
    group_fpr = {}
    for g, sub in df.groupby("group"):
        group_fpr[g] = rates(confusion(sub["score"], sub["label"], t))["fpr"]
        row[f"fpr_{g}"] = group_fpr[g]
        row[f"alert_share_{g}"] = alerts[df["group"] == g].sum() / alerts.sum()
        row[f"application_share_{g}"] = (df["group"] == g).mean()
    if len(group_fpr) == 2:
        row["fpr_ratio"] = fpr_ratio(*group_fpr.values())
    return row


def run_scenario(months, n, seed, target=TARGET):
    rng = np.random.default_rng(seed)
    data = [simulate_month(spec, n, rng) for spec in months]
    ref = data[0]
    t_static = threshold_at_fpr(ref["score"], ref["label"], target)
    ref_alert_rate = flag(ref["score"], t_static).mean()
    rows = []
    for m, df in enumerate(data):
        thresholds = {
            "static": t_static,
            "label_free_top": threshold_top_fraction(df["score"], target),
            "label_free_val_rate": threshold_top_fraction(df["score"], ref_alert_rate),
            "oracle": threshold_at_fpr(df["score"], df["label"], target),
        }
        if m >= 1:
            prev = data[m - 1]
            thresholds["delayed_lag1"] = threshold_at_fpr(prev["score"], prev["label"], target)
        for strategy in STRATEGIES:
            if strategy in thresholds:
                rows.append(dict(month=m, strategy=strategy, **_evaluate(df, thresholds[strategy])))
    return rows


BASE = MonthSpec(
    group_share={"young": 0.8, "old": 0.2},
    prevalence={"young": 0.009, "old": 0.018},
    neg_mean={"young": 0.0, "old": 0.4},
    pos_mean={"young": 2.0, "old": 2.0},
)

SCENARIOS = {
    "(0) no shift": BASE,
    "(a) negative scores shift up 0.3": replace(BASE, neg_mean={k: v + 0.3 for k, v in BASE.neg_mean.items()}),
    "(b) positive scores shift down 0.5": replace(BASE, pos_mean={k: v - 0.5 for k, v in BASE.pos_mean.items()}),
    "(c) prevalence doubles": replace(BASE, prevalence={k: 2 * v for k, v in BASE.prevalence.items()}),
    "(d) older group share 0.2 to 0.5": replace(BASE, group_share={"young": 0.5, "old": 0.5}),
}


N_PER_MONTH = 1_000_000
N_MONTHS = 4
SEED = 20261016
ON_BUDGET_PT = 0.25  # |budget miss| below this many FPR points counts as on budget

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
CSV = ROOT / "results" / "synthetic" / "mechanism.csv"
REPORT = ROOT / "reports" / "mechanism.md"
FIGURE = ROOT / "figures" / "synthetic_mechanism.png"


def run_all():
    frames = []
    for i, (name, shifted) in enumerate(SCENARIOS.items()):
        months = [BASE] + [shifted] * (N_MONTHS - 1)
        df = pd.DataFrame(run_scenario(months, N_PER_MONTH, seed=SEED + i))
        df.insert(0, "scenario", name)
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["budget_miss"] = out["fpr"] - TARGET
    out["identity_fpr"] = (out["alert_share"] - out["tpr"] * out["prevalence"]) / (1 - out["prevalence"])
    return out


def _fmt_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def write_report(out):
    from src.plotstyle import LABELS

    m = out[out["month"].isin([1, 2])].copy()
    table = pd.DataFrame(
        {
            "scenario": m["scenario"],
            "month": m["month"],
            "strategy": m["strategy"].map(LABELS),
            "realized FPR %": (100 * m["fpr"]).round(2),
            "budget miss, pt": (100 * m["budget_miss"]).round(2),
            "TPR %": (100 * m["tpr"]).round(1),
            "alert share %": (100 * m["alert_share"]).round(2),
            "FPR ratio": m["fpr_ratio"].round(3),
            "older share of alerts %": (100 * m["alert_share_old"]).round(1),
            "older share of applications %": (100 * m["application_share_old"]).round(1),
        }
    )
    fixes = []
    month2 = out[(out["month"] == 2) & (out["strategy"] != "oracle")]
    for name, sub in month2.groupby("scenario", sort=False):
        ok = sub.loc[(100 * sub["budget_miss"]).abs() < ON_BUDGET_PT, "strategy"].map(LABELS).tolist()
        oracle_tpr = out[(out["scenario"] == name) & (out["month"] == 2) & (out["strategy"] == "oracle")]["tpr"].iloc[0]
        ref_tpr = out[(out["scenario"] == name) & (out["month"] == 0) & (out["strategy"] == "oracle")]["tpr"].iloc[0]
        fixes.append(
            {
                "scenario": name,
                f"deployable strategies within {ON_BUDGET_PT} pt of budget in month 2": "; ".join(ok) or "none",
                "static budget miss, pt, month 2": round(100 * sub.loc[sub["strategy"] == "static", "budget_miss"].iloc[0], 2),
                "oracle TPR % month 0": round(100 * ref_tpr, 1),
                "oracle TPR % month 2": round(100 * oracle_tpr, 1),
            }
        )
    max_dev = (out["fpr"] - out["identity_fpr"]).abs().max()
    spec = BASE
    text = f"""# Mechanism study (synthetic, not BAF)

Everything in this file is synthetic, not BAF. It explains how threshold strategies respond to different kinds of shift when the truth is known. It is not a result about BAF. Generated by `python -m src.synthetic`; no number here is typed by hand.

## Setup

Scores are normal with unit variance within each group and label. Reference month 0 (the validation month): younger group share {spec.group_share['young']}, older {spec.group_share['old']}; prevalence younger {spec.prevalence['young']}, older {spec.prevalence['old']}; negative score mean younger {spec.neg_mean['young']}, older {spec.neg_mean['old']}; positive score mean {spec.pos_mean['young']} in both groups. Each scenario applies one shift from month 1 onward and keeps it through month {N_MONTHS - 1}. {N_PER_MONTH:,} applications per month, seed {SEED} plus the scenario index. Strategies and threshold rules are those in PROTOCOL.md, with a {100 * TARGET:.0f}% FPR target. Delayed-label lag 1 in month 1 uses month 0 and so equals static by construction.

## Accounting identity

For every row, realized FPR equals (alert share - TPR x prevalence) / (1 - prevalence), using the month's own prevalence. Largest absolute difference over all {len(out)} rows: {max_dev:.2e}.

## Which shifts recalibration fixes

{_fmt_table(pd.DataFrame(fixes))}

Reading. In (a) the negatives' scores move, and in (d) the mix of groups with different negative score distributions moves, so the static threshold overshoots the budget; label-free recalibration on the validation alert rate stays near budget, and delayed-label lag 1 returns near budget from the second shifted month. In (b) only the positives move: static stays on budget, and no threshold recovers the lost TPR, because the oracle loses the same TPR. In (c) only prevalence moves: static stays on budget, while both label-free strategies fall below budget because positives take a larger share of a fixed alert volume. Label-free top 5% is below budget in every scenario, including no shift, because by the identity above its FPR is below 5% whenever TPR is above 5%. In (a) the static TPR stays near its reference level only because it overshoots the FPR budget.

## Months 1 and 2 by scenario and strategy

{_fmt_table(table)}

![Synthetic, not BAF](../figures/synthetic_mechanism.png)
"""
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(text)


def plot(out):
    from src.plotstyle import LABELS, STYLE, setup

    plt = setup()
    names = list(SCENARIOS)
    fig, axes = plt.subplots(2, len(names), figsize=(15, 5.6), sharex=True, sharey="row")
    for j, name in enumerate(names):
        sub = out[out["scenario"] == name]
        for strategy, style in STYLE.items():
            s = sub[sub["strategy"] == strategy]
            axes[0, j].plot(s["month"], 100 * s["fpr"], label=LABELS[strategy], **style)
            axes[1, j].plot(s["month"], 100 * s["tpr"], **style)
        axes[0, j].axhline(100 * TARGET, color="#52514e", linewidth=0.8, linestyle=":")
        axes[0, j].set_title(name, fontsize=9)
        axes[1, j].set_xlabel("month (0 = reference)")
        axes[1, j].set_xticks(range(N_MONTHS))
    axes[0, 0].set_ylabel("realized FPR, %")
    axes[1, 0].set_ylabel("TPR, %")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Synthetic, not BAF: threshold strategies under controlled shifts (dotted line: 5% FPR target)", fontsize=10)
    fig.tight_layout(rect=(0, 0.05, 1, 0.97))
    FIGURE.parent.mkdir(exist_ok=True)
    fig.savefig(FIGURE, dpi=150)


def main():
    out = run_all()
    CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(CSV, index=False)
    write_report(out)
    plot(out)
    print(f"wrote {CSV}, {REPORT}, {FIGURE}")


if __name__ == "__main__":
    main()
