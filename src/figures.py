"""Figures built from saved predictions and thresholds."""

import numpy as np
from matplotlib.ticker import MultipleLocator
from sklearn.metrics import roc_curve

from src.metrics import confusion, rates
from src.plotstyle import INK_2, LABELS, MUTED, STYLE, setup


def plot_roc_operating_points(curves, points, path, max_fpr=0.15, title=None):
    """One panel per (variant, month): the ROC curve of that month's scores, with
    each strategy's operating point at its applied threshold.

    curves: {(variant, month): (scores, labels)}
    points: {(variant, month, strategy): threshold}
    Returns {(variant, month, strategy): (fpr, tpr)} for the marked points.
    """
    plt = setup()
    variants = list(dict.fromkeys(v for v, _ in curves))
    months = sorted({m for _, m in curves})
    fig, axes = plt.subplots(len(variants), len(months), figsize=(3.2 * len(months), 2.8 * len(variants)), squeeze=False)
    coords = {}
    for i, variant in enumerate(variants):
        for j, month in enumerate(months):
            ax = axes[i, j]
            if (variant, month) not in curves:
                ax.set_visible(False)
                continue
            scores, labels = curves[(variant, month)]
            fpr, tpr, _ = roc_curve(labels, scores, drop_intermediate=False)
            ax.plot(fpr, tpr, color=MUTED, linewidth=1.2)
            ax.axvline(0.05, color="#52514e", linewidth=0.8, linestyle=":")
            for (v, m, strategy), t in points.items():
                if (v, m) != (variant, month):
                    continue
                r = rates(confusion(scores, labels, t))
                coords[(v, m, strategy)] = (r["fpr"], r["tpr"])
                style = STYLE.get(strategy, dict(color=MUTED, marker="o"))
                color = INK_2 if strategy == "oracle" else style["color"]
                # Hollow markers so that strategies sitting on the same point stay visible.
                ax.plot(r["fpr"], r["tpr"], linestyle="none", marker=style["marker"], markerfacecolor="none",
                        markeredgecolor=color, markeredgewidth=1.6, markersize=9, label=LABELS.get(strategy, strategy))
            panel_points = [xy[0] for (v, m, _), xy in coords.items() if (v, m) == (variant, month)]
            ax.set_xlim(0, max([max_fpr] + [1.1 * x for x in panel_points]))
            ax.xaxis.set_major_locator(MultipleLocator(0.05))
            ax.set_title(f"{variant}, month {month}", fontsize=9)
            if i == len(variants) - 1:
                ax.set_xlabel("FPR (share of negatives)")
            if j == 0:
                ax.set_ylabel("TPR (share of positives)")
    handles, labels = [], []
    for ax in axes.ravel():
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in labels:
                handles.append(h)
                labels.append(lab)
    fig.legend(handles, labels, loc="lower center", ncol=min(len(labels), 3))
    if title:
        fig.suptitle(title, fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 0.97 if title else 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return coords
