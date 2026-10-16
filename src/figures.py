"""Figures built from saved predictions and thresholds."""

import numpy as np
from sklearn.metrics import roc_curve

from src.metrics import confusion, rates
from src.plotstyle import LABELS, MUTED, STYLE, setup


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
                ax.plot(r["fpr"], r["tpr"], linestyle="none", marker=style["marker"], color=style["color"],
                        markersize=8, markeredgecolor="#fcfcfb", markeredgewidth=1, label=LABELS.get(strategy, strategy))
            ax.set_xlim(0, max_fpr)
            ax.set_title(f"{variant}, month {month}", fontsize=9)
            if i == len(variants) - 1:
                ax.set_xlabel("FPR")
            if j == 0:
                ax.set_ylabel("TPR")
    handles, labels = [], []
    for ax in axes.ravel():
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in labels:
                handles.append(h)
                labels.append(lab)
    fig.legend(handles, labels, loc="lower center", ncol=min(len(labels), 4))
    if title:
        fig.suptitle(title, fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 0.97 if title else 1))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return coords
