"""Score PREDICTIONS.md against the results, using the rules declared in PROTOCOL.md
("Scoring rules for PREDICTIONS.md") before the main study was trained.

Writes results/predictions_scored.csv. Run with: python -m src.predictions_eval
"""

import numpy as np
import pandas as pd

from src import config
from src.schema import PRIMARY_AGE, PRIMARY_MODEL, PRIMARY_TARGET

THREE = ["static", "label_free_top", "delayed_lag1"]
FIVE = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "oracle"]
EARLY, LATE = [4, 5], [6, 7]


class _S:
    def __init__(self, summary, metrics):
        s = summary[(summary.model == PRIMARY_MODEL) & np.isclose(summary.fpr_target, PRIMARY_TARGET) & (summary.age_def == PRIMARY_AGE)]
        self.v = {(r.variant, r.strategy, r.month, r.metric): r.mean for r in s.itertuples()}
        m = metrics[(metrics.model == PRIMARY_MODEL) & np.isclose(metrics.fpr_target, PRIMARY_TARGET) & (metrics.age_def == PRIMARY_AGE)
                    & (metrics.seed == metrics.seed.min()) & (metrics.strategy == "static")]
        # Fraud rate by age group and month (data property, identical for every strategy and seed).
        self.prev = {(r.variant, r.month): {"young": r.n_pos_young / (r.n_pos_young + r.n_neg_young),
                                           "old": r.n_pos_old / (r.n_pos_old + r.n_neg_old)} for r in m.itertuples()}

    def __call__(self, variant, strategy, month, metric):
        return self.v[(variant, strategy, month, metric)]


def _row(pid, hit, detail):
    return dict(prediction=pid, result="hit" if hit else "miss", detail=detail)


def score(summary, metrics):
    s = _S(summary, metrics)
    out = []
    four = ["Base", "Variant I", "Variant II", "Variant III"]
    cells = [(v, m) for v in four for m in EARLY + LATE]

    gaps = {(v, m): max(s(v, x, m, "tpr") for x in THREE) - min(s(v, x, m, "tpr") for x in THREE) for v, m in cells}
    worst = max(gaps, key=gaps.get)
    out.append(_row("1", all(g <= 0.04 for g in gaps.values()),
                    f"largest TPR gap among the deployable three: {100 * gaps[worst]:.2f} pt ({worst[0]}, month {worst[1]}); "
                    f"{sum(g <= 0.04 for g in gaps.values())} of {len(gaps)} variant-months within 4 pt"))
    st = {c: s(*c[:1], "static", c[1], "realized_fpr") for c in cells}
    out.append(_row("2 (static FPR)", all(0.04 <= f <= 0.06 for f in st.values()),
                    f"static realized FPR ranged {100 * min(st.values()):.2f}% to {100 * max(st.values()):.2f}%; "
                    f"{sum(0.04 <= f <= 0.06 for f in st.values())} of {len(st)} within 4% to 6%"))
    lf = {c: s(c[0], "label_free_top", c[1], "realized_fpr") for c in cells}
    out.append(_row("2 (label-free FPR)", all(0.042 <= f <= 0.048 for f in lf.values()),
                    f"label-free realized FPR ranged {100 * min(lf.values()):.2f}% to {100 * max(lf.values()):.2f}%; "
                    f"{sum(0.042 <= f <= 0.048 for f in lf.values())} of {len(lf)} within 4.2% to 4.8%"))

    for v, ids in (("Variant IV", ("3", "4", "5", "6", "7", "A")), ("Variant V", ("8", "9", "10", "11", "12", "B"))):
        early = np.mean([s(v, "static", m, "realized_fpr") for m in EARLY])
        late = np.mean([s(v, "static", m, "realized_fpr") for m in LATE])
        out.append(_row(ids[0], abs(late - early) < 0.005,
                        f"static realized FPR, months 4-5 mean {100 * early:.2f}%, months 6-7 mean {100 * late:.2f}%, difference {100 * (late - early):+.2f} pt"))

        ok, parts = True, []
        for m in LATE:
            miss = {x: s(v, x, m, "budget_miss") for x in THREE}
            largest = max(THREE, key=lambda x: abs(miss[x]))
            smallest = min(THREE, key=lambda x: abs(miss[x]))
            ok &= largest == "label_free_top" and -0.010 <= miss["label_free_top"] <= -0.005 and smallest in ("static", "delayed_lag1")
            parts.append(f"month {m}: largest {largest} ({100 * miss[largest]:+.2f} pt), smallest {smallest} ({100 * miss[smallest]:+.2f} pt), "
                         f"label-free {100 * miss['label_free_top']:+.2f} pt")
        out.append(_row(ids[1], ok, "; ".join(parts)))

        ok, parts = True, []
        for m in LATE:
            tpr = {x: s(v, x, m, "tpr") for x in THREE}
            fpr = {x: s(v, x, m, "realized_fpr") for x in THREE}
            top = max(THREE, key=tpr.get)
            ok &= top in ("static", "delayed_lag1") and fpr[top] == max(fpr.values())
            parts.append(f"month {m}: highest TPR {top} ({100 * tpr[top]:.1f}%, realized FPR {100 * fpr[top]:.2f}%; "
                         f"highest realized FPR is {max(THREE, key=fpr.get)})")
        out.append(_row(ids[2], ok, "; ".join(parts)))

        e = np.mean([s(v, "static", m, "fpr_ratio") for m in EARLY])
        la = np.mean([s(v, "static", m, "fpr_ratio") for m in LATE])
        out.append(_row(ids[3], abs(la - e) < 0.05, f"static FPR ratio, months 4-5 mean {e:.3f}, months 6-7 mean {la:.3f}, change {la - e:+.3f}"))

        ok, parts = True, []
        for m in LATE:
            r_lf, r_st = s(v, "label_free_top", m, "fpr_ratio"), s(v, "static", m, "fpr_ratio")
            prev = s.prev[(v, m)]
            hi_group = max(prev, key=prev.get)
            share = s(v, "label_free_top", m, f"alert_share_{hi_group}")
            ok &= abs(r_lf - r_st) <= 0.05 and share >= 0.65
            parts.append(f"month {m}: FPR ratio label-free {r_lf:.3f} vs static {r_st:.3f}; higher-fraud-rate group {hi_group} "
                         f"({100 * prev[hi_group]:.2f}% vs {100 * min(prev.values()):.2f}%) gets {100 * share:.1f}% of label-free alerts")
        out.append(_row(ids[4], ok, "; ".join(parts)))

        loss = {x: np.mean([s(v, x, m, "tpr") for m in EARLY]) - np.mean([s(v, x, m, "tpr") for m in LATE]) for x in FIVE}
        gap = max(max(s(v, x, m, "tpr") for x in FIVE) - min(s(v, x, m, "tpr") for x in FIVE) for m in EARLY + LATE)
        out.append(_row(ids[5], all(l > 0 and l > gap for l in loss.values()),
                        "TPR loss from months 4-5 to 6-7: " + ", ".join(f"{x} {100 * l:+.1f} pt" for x, l in loss.items())
                        + f"; largest gap between strategies in any test month {100 * gap:.1f} pt"))
    return pd.DataFrame(out)


def main():
    summary = pd.read_csv(config.RESULTS / "summary.csv")
    metrics = pd.read_csv(config.RESULTS / "metrics.csv")
    out = score(summary, metrics)
    out.insert(0, "predictions_commit", summary["predictions_commit"].iloc[0])
    out.to_csv(config.RESULTS / "predictions_scored.csv", index=False)
    print(out[["prediction", "result"]].to_string(index=False))


if __name__ == "__main__":
    main()


def prediction_texts(path=config.ROOT / "PREDICTIONS.md"):
    """Answer text per scored id, read verbatim from PREDICTIONS.md."""
    import re

    text = path.read_text()
    answers = dict(re.findall(r"^(\d+)\. (.+)$", text.split("## Answers")[1].split("## Additional")[0], flags=re.M))
    extra = dict(re.findall(r"^([AB])\. (.+)$", text.split("## Additional predictions")[1], flags=re.M))
    out = {k: v for k, v in answers.items() if k != "2"}
    out["2 (static FPR)"] = out["2 (label-free FPR)"] = answers["2"]
    out.update(extra)
    return out
