"""Shared figure style. Colors follow the strategy, never its rank.

Categorical slots 1 to 4 from the dataviz reference palette (validated light mode,
contrast below 3:1 for slots 3 and 4, so every figure carries a legend and
distinct markers, and its numbers are in a table). The oracle is drawn in muted
gray with a dashed line because it is an upper bound, not a deployable strategy.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

LABELS = {
    "static": "Static",
    "label_free_top": "Label-free, top 5%",
    "label_free_val_rate": "Label-free, validation alert rate",
    "delayed_lag1": "Delayed-label, lag 1",
    "delayed_lag2": "Delayed-label, lag 2",
    "delayed_lag3": "Delayed-label, lag 3",
    "oracle": "Oracle (upper bound, not deployable)",
    "groupwise_static": "Group-wise static (exploratory diagnostic, uses age)",
    "groupwise_label_free": "Group-wise label-free (exploratory diagnostic, uses age)",
}

STYLE = {
    "static": dict(color="#2a78d6", marker="o", linestyle="-"),
    "label_free_top": dict(color="#eb6834", marker="s", linestyle="-"),
    "label_free_val_rate": dict(color="#1baf7a", marker="^", linestyle="-"),
    "delayed_lag1": dict(color="#eda100", marker="D", linestyle="-"),
    "oracle": dict(color=MUTED, marker="x", linestyle="--"),
}


def setup():
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": AXIS,
            "axes.labelcolor": INK_2,
            "axes.titlecolor": INK,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "lines.linewidth": 2,
            "lines.markersize": 6,
            "font.size": 9,
            "legend.frameon": False,
        }
    )
    return plt
