"""Figures from results files: realized FPR, TPR (with realized FPR) and FPR ratio by month, and ROC operating points.

Lines are seed means (primary model, 5% target, primary age definition); error bars
are the seed 0 bootstrap 95% intervals. The oracle is drawn dashed and gray: an
upper bound, not deployable.

Run with: python -m src.report_figures
"""

import numpy as np
import pandas as pd

from src import config
from src.figures import plot_roc_operating_points
from src.plotstyle import LABELS, STYLE, setup
from src.schema import PRIMARY_AGE, PRIMARY_MODEL, PRIMARY_STRATEGIES, PRIMARY_TARGET, TEST_MONTHS, VARIANTS
from src.train import pred_path


def _sel(df):
    return df[(df.model == PRIMARY_MODEL) & np.isclose(df.fpr_target, PRIMARY_TARGET) & (df.age_def == PRIMARY_AGE)]


def _panel(ax, summary, ci, variant, metric, scale=100):
    for s in PRIMARY_STRATEGIES:
        sm = summary[(summary.variant == variant) & (summary.strategy == s) & (summary.metric == metric)].sort_values("month")
        c = ci[(ci.variant == variant) & (ci.strategy == s) & (ci.metric == metric) & (ci.seed == 0)].sort_values("month")
        if sm.empty:
            continue
        ax.plot(sm.month, scale * sm["mean"], label=LABELS[s], **STYLE[s])
        if not c.empty:
            # Percentile intervals need not contain the point estimate, so draw lo to hi directly.
            ax.vlines(c.month, scale * c.lo, scale * c.hi, color=STYLE[s]["color"], linewidth=1)
    ax.set_xticks(TEST_MONTHS)


def _variants(summary):
    return [v for v in VARIANTS if v in set(summary.variant)]


def by_month(summary, ci, metric, ylabel, path, target_line=False, title=""):
    plt = setup()
    vs = _variants(summary)
    fig, axes = plt.subplots(1, len(vs), figsize=(3.1 * len(vs), 3.2), sharey=True, squeeze=False)
    for ax, v in zip(axes[0], vs):
        _panel(ax, summary, ci, v, metric)
        if target_line:
            ax.axhline(100 * PRIMARY_TARGET, color="#52514e", linewidth=0.8, linestyle=":")
        ax.set_title(v, fontsize=9)
        ax.set_xlabel("test month")
    axes[0, 0].set_ylabel(ylabel)
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=len(lab))
    fig.suptitle(title, fontsize=10)
    fig.tight_layout(rect=(0, 0.1, 1, 0.93))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def tpr_with_fpr(summary, ci, path):
    plt = setup()
    vs = _variants(summary)
    fig, axes = plt.subplots(2, len(vs), figsize=(3.1 * len(vs), 5.6), sharex=True, sharey="row", squeeze=False)
    for j, v in enumerate(vs):
        _panel(axes[0, j], summary, ci, v, "realized_fpr")
        axes[0, j].axhline(100 * PRIMARY_TARGET, color="#52514e", linewidth=0.8, linestyle=":")
        _panel(axes[1, j], summary, ci, v, "tpr")
        axes[0, j].set_title(v, fontsize=9)
        axes[1, j].set_xlabel("test month")
    axes[0, 0].set_ylabel("realized FPR, %")
    axes[1, 0].set_ylabel("TPR, %")
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=len(lab))
    fig.suptitle("TPR by month, with the realized FPR it was bought at (LightGBM, seed mean; bars: seed 0 bootstrap 95% CI)", fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def roc_points(metrics, path):
    m = _sel(metrics)
    m = m[(m.seed == 0) & m.strategy.isin(PRIMARY_STRATEGIES) & m.available.astype(bool)]
    curves, points = {}, {}
    for v in [v for v in VARIANTS if v in set(m.variant)]:
        z = np.load(pred_path(v, PRIMARY_MODEL, 0))
        for month in TEST_MONTHS:
            k = z["month"] == month
            curves[(v, month)] = (z["score"][k], z["label"][k])
        for r in m[m.variant == v].itertuples():
            points[(v, r.month, r.strategy)] = r.threshold
    return plot_roc_operating_points(curves, points, path, title="ROC curve of each test month's scores (LightGBM seed 0) with each strategy's operating point")


def main():
    summary = _sel(pd.read_csv(config.RESULTS / "summary.csv"))
    ci = _sel(pd.read_csv(config.RESULTS / "ci.csv"))
    metrics = pd.read_csv(config.RESULTS / "metrics.csv")
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    note = "(LightGBM, seed mean; bars: seed 0 bootstrap 95% CI; dotted: 5% target)"
    by_month(summary, ci, "realized_fpr", "realized FPR, %", config.FIGURES / "realized_fpr_by_month.png", True, f"Realized FPR by test month {note}")
    tpr_with_fpr(summary, ci, config.FIGURES / "tpr_by_month.png")
    by_month(summary, ci, "fpr_ratio", "FPR ratio (lowest / highest)", config.FIGURES / "fpr_ratio_by_month.png", False,
             "Age-group FPR ratio by test month (LightGBM, seed mean; bars: seed 0 bootstrap 95% CI)")
    roc_points(metrics, config.FIGURES / "roc_operating_points.png")
    print(f"wrote figures to {config.FIGURES}")


if __name__ == "__main__":
    main()
