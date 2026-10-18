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


NCOL = 3  # variants per row: one row of six panels is too wide to read at page width
LAG1_NOTE = "month 4: delayed-label lag 1 uses month 3, so it equals static and hides its marker"


def _grid(plt, n_variants, rows_per_variant, height):
    nrow = -(-n_variants // NCOL) * rows_per_variant
    fig, axes = plt.subplots(nrow, NCOL, figsize=(3.4 * NCOL, height * nrow), sharex=True, squeeze=False)
    for ax in axes.ravel()[n_variants * rows_per_variant:]:
        ax.set_visible(False)
    return fig, axes


def _share_y(axes):
    lo = min(ax.get_ylim()[0] for ax in axes)
    hi = max(ax.get_ylim()[1] for ax in axes)
    for ax in axes:
        ax.set_ylim(lo, hi)
    for ax in axes:
        if ax.get_subplotspec().colspan.start > 0:
            ax.tick_params(labelleft=False)


def _legend(fig, ax):
    h, lab = ax.get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=3)


def by_month(summary, ci, metric, ylabel, path, target_line=False, title="", scale=100):
    plt = setup()
    vs = _variants(summary)
    fig, axes = _grid(plt, len(vs), 1, 2.7)
    used = []
    for k, v in enumerate(vs):
        ax = axes[k // NCOL, k % NCOL]
        used.append(ax)
        _panel(ax, summary, ci, v, metric, scale=scale)
        if target_line:
            ax.axhline(100 * PRIMARY_TARGET, color="#52514e", linewidth=0.8, linestyle=":")
        ax.set_title(v, fontsize=9)
        ax.tick_params(labelbottom=True)
        if k % NCOL == 0:
            ax.set_ylabel(ylabel)
        if k >= len(vs) - NCOL:
            ax.set_xlabel("test month")
    _share_y(used)
    _legend(fig, used[0])
    fig.suptitle(title, fontsize=10)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def tpr_with_fpr(summary, ci, path):
    """Each variant gets a realized FPR panel with its TPR panel directly below it."""
    plt = setup()
    vs = _variants(summary)
    fig, axes = _grid(plt, len(vs), 2, 2.4)
    fpr_axes, tpr_axes = [], []
    for k, v in enumerate(vs):
        r, c = 2 * (k // NCOL), k % NCOL
        top, bottom = axes[r, c], axes[r + 1, c]
        fpr_axes.append(top)
        tpr_axes.append(bottom)
        _panel(top, summary, ci, v, "realized_fpr")
        top.axhline(100 * PRIMARY_TARGET, color="#52514e", linewidth=0.8, linestyle=":")
        _panel(bottom, summary, ci, v, "tpr")
        top.set_title(v, fontsize=9)
        bottom.tick_params(labelbottom=True)
        if c == 0:
            top.set_ylabel("realized FPR, %")
            bottom.set_ylabel("TPR, %")
        if k >= len(vs) - NCOL:
            bottom.set_xlabel("test month")
    _share_y(fpr_axes)
    _share_y(tpr_axes)
    _legend(fig, fpr_axes[0])
    fig.suptitle("TPR by month (lower panel), with the realized FPR it was bought at (upper panel)\n"
                 "LightGBM, seed mean; bars: seed 0 bootstrap 95% CI, often shorter than the marker; dotted: 5% target\n"
                 + LAG1_NOTE, fontsize=9)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
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
    return plot_roc_operating_points(curves, points, path, title="ROC curve of each test month's scores (LightGBM seed 0) with each strategy's operating point; dotted: 5% FPR\n" + LAG1_NOTE)


def main():
    summary = _sel(pd.read_csv(config.RESULTS / "summary.csv"))
    ci = _sel(pd.read_csv(config.RESULTS / "ci.csv"))
    metrics = pd.read_csv(config.RESULTS / "metrics.csv")
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    note = "LightGBM, seed mean; bars: seed 0 bootstrap 95% CI, often shorter than the marker"
    by_month(summary, ci, "realized_fpr", "realized FPR, %", config.FIGURES / "realized_fpr_by_month.png", True,
             f"Realized FPR by test month (dotted: 5% target)\n{note}\n{LAG1_NOTE}")
    tpr_with_fpr(summary, ci, config.FIGURES / "tpr_by_month.png")
    by_month(summary, ci, "fpr_ratio", "FPR ratio (lowest / highest)", config.FIGURES / "fpr_ratio_by_month.png", False,
             f"Age-group FPR ratio by test month (older group: customer_age {PRIMARY_AGE.replace('>=', '>= ')}; 1 means equal group FPRs)\n{note}\n{LAG1_NOTE}",
             scale=1)
    roc_points(metrics, config.FIGURES / "roc_operating_points.png")
    print(f"wrote figures to {config.FIGURES}")


if __name__ == "__main__":
    main()
