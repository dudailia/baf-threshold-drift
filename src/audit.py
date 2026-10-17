"""Data audit: writes reports/data_audit.md from the files in data/raw/.

Run with: python -m src.audit
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from src.data import (
    CATEGORICAL,
    LABEL,
    MAIN_SPLIT,
    MINUS_ONE_MISSING,
    NEGATIVE_MISSING,
    PAPER_SPLIT,
    RAW_DIR,
    VARIANT_FILES,
    age_group,
    list_raw_files,
    load_variant,
)

from src.config import REPORTS, RESULTS, TRIPWIRES_FATAL

REPORT = REPORTS / "data_audit.md"
MIN_POSITIVES = 30

# Table 1 of Jesus et al. 2022 (p7): older ("minority") group share, and fraud
# prevalence for (majority, minority). Variant IV lists train-month values and,
# in parentheses, test-month values.
TABLE1 = {
    "Base": dict(min_share=0.23, prev_maj=0.009, prev_min=0.018),
    "Variant I": dict(min_share=0.10, prev_maj=0.011, prev_min=0.011),
    "Variant II": dict(min_share=0.50, prev_maj=0.004, prev_min=0.019),
    "Variant III": dict(min_share=0.50, prev_maj=0.011, prev_min=0.011),
    "Variant IV (months 0-5)": dict(min_share=0.50, prev_maj=0.003, prev_min=0.017),
    "Variant IV (months 6-7)": dict(min_share=0.50, prev_maj=0.015, prev_min=0.015),
    "Variant V": dict(min_share=0.50, prev_maj=0.011, prev_min=0.011),
}


def md_table(df, floatfmt="{:.4f}"):
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = [floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def group_stats(df, definition):
    g = age_group(df["customer_age"], definition)
    y = df[LABEL]
    return dict(
        min_share=g.mean(),
        prev_maj=y[g == 0].mean(),
        prev_min=y[g == 1].mean(),
        prev_all=y.mean(),
    )


def table1_rows(name, df):
    subsets = {name: df}
    if name == "Variant IV":
        subsets = {
            "Variant IV (months 0-5)": df[df["month"] <= 5],
            "Variant IV (months 6-7)": df[df["month"] >= 6],
        }
    rows = []
    for label, sub in subsets.items():
        ref = TABLE1[label]
        for definition in (">=50", ">50"):
            s = group_stats(sub, definition)
            dist = sum(abs(s[k] - ref[k]) / ref[k] for k in ("min_share", "prev_maj", "prev_min")) / 3
            rows.append(
                {
                    "subset": label,
                    "older group": definition,
                    "older share": s["min_share"],
                    "Table 1 share": ref["min_share"],
                    "prev younger": s["prev_maj"],
                    "Table 1": ref["prev_maj"],
                    "prev older": s["prev_min"],
                    "Table 1 ": ref["prev_min"],
                    "mean rel. diff": dist,
                }
            )
    return rows


def cross_split_duplicates(df, split):
    """Rows identical in every column except month that occur in more than one split."""
    feats = df.drop(columns=["month"])
    h = pd.util.hash_pandas_object(feats, index=False).to_numpy()
    part = np.full(len(df), "", dtype=object)
    for name, months in split.items():
        part[df["month"].isin(months).to_numpy()] = name
    frame = pd.DataFrame({"h": h, "part": part})
    frame = frame[frame["part"] != ""]
    n_parts = frame.groupby("h")["part"].nunique()
    return int((n_parts > 1).sum())


def audit_variant(name, df, out):
    out.append(f"\n## {name}\n")
    out.append(f"Rows: {len(df):,}. Columns: {df.shape[1]}. Exact NaN cells as loaded: {int(df.isna().sum().sum())}.\n")
    out.append("Columns and loaded dtypes: " + ", ".join(f"`{c}` ({df[c].dtype})" for c in df.columns) + "\n")

    by_month = df.groupby("month")[LABEL].agg(rows="size", frauds="sum", fraud_rate="mean").reset_index()
    by_month["share_of_rows"] = by_month["rows"] / len(df)
    out.append("\nRows and fraud rate by month:\n\n" + md_table(by_month) + "\n")

    sent = []
    for col in MINUS_ONE_MISSING + NEGATIVE_MISSING:
        if col not in df:
            sent.append({"column": col, "rule": "absent", "sentinel rows": "", "share": np.nan, "fraud rate if sentinel": np.nan})
            continue
        m = df[col] == -1 if col in MINUS_ONE_MISSING else df[col] < 0
        other_neg = int(((df[col] < 0) & ~m).sum())
        sent.append(
            {
                "column": col,
                "rule": "-1" if col in MINUS_ONE_MISSING else "< 0",
                "sentinel rows": int(m.sum()),
                "share": m.mean(),
                "fraud rate if sentinel": df.loc[m, LABEL].mean() if m.any() else np.nan,
                "other negatives": other_neg,
            }
        )
    out.append("\nDocumented missing-value sentinels (datasheet A7):\n\n" + md_table(pd.DataFrame(sent)) + "\n")

    numeric = [c for c in df.columns if c not in CATEGORICAL + [LABEL, "month"]]
    neg = [
        {"column": c, "negative rows": int((df[c] < 0).sum()), "min": float(df[c].min()), "max": float(df[c].max())}
        for c in numeric
        if c not in MINUS_ONE_MISSING + NEGATIVE_MISSING and (df[c] < 0).any()
    ]
    if neg:
        out.append("\nOther numeric columns with negative values (not documented as missing; kept as values):\n\n" + md_table(pd.DataFrame(neg)) + "\n")

    out.append("\n`customer_age` values: " + ", ".join(f"{a}: {n:,}" for a, n in df["customer_age"].value_counts().sort_index().items()) + "\n")

    for definition in (">=50", ">50"):
        g = age_group(df["customer_age"], definition)
        cells = (
            df.assign(older=g)
            .groupby(["month", "older"])[LABEL]
            .agg(positives="sum", rows="size")
            .reset_index()
        )
        cells["negatives"] = cells["rows"] - cells["positives"]
        cells["fewer than 30 positives"] = np.where(cells["positives"] < MIN_POSITIVES, "FLAG", "")
        cells = cells.drop(columns="rows")
        out.append(f"\nPositive and negative counts by month and age group, older group `customer_age {definition}`:\n\n" + md_table(cells) + "\n")

    unseen = []
    train = df[df["month"].isin(MAIN_SPLIT["train"])]
    for col in CATEGORICAL:
        levels = set(train[col].unique())
        for m in MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]:
            new = set(df.loc[df["month"] == m, col].unique()) - levels
            if new:
                unseen.append({"column": col, "month": m, "levels unseen in months 0-2": ", ".join(sorted(map(str, new)))})
    out.append("\nCategorical levels: " + "; ".join(f"`{c}`: {df[c].nunique()} ({', '.join(sorted(map(str, df[c].unique())))})" for c in CATEGORICAL) + "\n")
    out.append("\nLevels in months 3 to 7 not seen in training months 0 to 2: " + ("none." if not unseen else "\n\n" + md_table(pd.DataFrame(unseen))) + "\n")

    full_dupes = int(df.duplicated().sum())
    stats = dict(within_file_duplicates=full_dupes, cross_split_main=cross_split_duplicates(df, MAIN_SPLIT),
                 cross_split_paper=cross_split_duplicates(df, PAPER_SPLIT))
    out.append(
        f"\nSplit overlap. Splits are by month, so a row cannot be in two splits by construction. "
        f"Exact duplicate rows within the file: {full_dupes}. "
        f"Rows identical in every column except `month` that occur in more than one split: "
        f"main split {stats['cross_split_main']}, paper split {stats['cross_split_paper']}.\n"
    )
    return stats


# Paper Sec 3.1 (p4): "The prevalence of fraud varies between 0.85% and 1.5% of the instances over different months."
BASE_MONTHLY_FRAUD_RANGE = (0.0085, 0.015)
EXPECTED_ROWS = 1_000_000  # Datasheet A5: each dataset has 1M instances
GROUP_SIZE_TOLERANCE = 0.05  # 5 points
AGE_CLOSE = 0.01  # definitions within 1 point of each other on mean group-size error count as close
IGNORED = {"CLAUDE.md", ".claude"}


def main():
    import json

    all_files = list_raw_files(RAW_DIR)
    ignored = [f for f in all_files if f in IGNORED]
    files = [f for f in all_files if f not in IGNORED]
    tripwires = []
    out = ["# Data audit\n", "Generated by `python -m src.audit` (`make audit`) from `data/raw/`. No numbers in this file are edited by hand.\n"]
    out.append("\n## Files\n\n" + md_table(pd.DataFrame(
        [{"file": f, "bytes": (RAW_DIR / f).stat().st_size, "sha256": sha256(RAW_DIR / f)} for f in files]
    )) + "\n")
    if ignored:
        out.append(f"\nIgnored without reading, as instructed: {ignored}.\n")
    extra = sorted(set(files) - set(VARIANT_FILES.values()))
    missing = sorted(set(VARIANT_FILES.values()) - set(files))
    if extra:
        tripwires.append(f"files other than the six variants: {extra}")
    if missing:
        raise SystemExit(f"missing variant files in {RAW_DIR}: {missing}")

    summary, t1, by_month, frames, stats = [], [], [], {}, {}
    for name in VARIANT_FILES:
        try:
            df = load_variant(name)
        except ValueError as e:
            tripwires.append(f"unexpected columns: {e}")
            continue
        frames[name] = df
        months = sorted(df["month"].unique().tolist())
        if min(months) < 0 or max(months) > 7:
            tripwires.append(f"{name}: months outside 0 to 7: {months}")
        if len(df) != EXPECTED_ROWS:
            tripwires.append(f"{name}: {len(df):,} rows, datasheet A5 says {EXPECTED_ROWS:,}")
        summary.append({"variant": name, "rows": len(df), "fraud rate": df[LABEL].mean(), "months": f"{min(months)}-{max(months)}",
                        "columns": df.shape[1]})
        rates_m = df.groupby("month")[LABEL].mean()
        by_month.append({"variant": name, **{f"month {m}": r for m, r in rates_m.items()}})
        if name == "Base":
            lo, hi = BASE_MONTHLY_FRAUD_RANGE
            bad = {int(m): round(float(r), 5) for m, r in rates_m.items() if not (lo - 5e-5 <= r <= hi + 5e-5)}
            if bad:
                tripwires.append(f"Base monthly fraud rate outside the paper's {lo:.2%} to {hi:.2%} (Sec 3.1): {bad}")
        t1.extend(table1_rows(name, df))
    t1 = pd.DataFrame(t1)
    t1["group size diff, pt"] = (100 * (t1["older share"] - t1["Table 1 share"]).abs()).round(2)

    # Age rule (PROTOCOL.md): the definition whose group sizes match Table 1 better across variants; >=50 if close.
    err = t1.groupby("older group")["group size diff, pt"].mean() / 100
    if abs(err[">=50"] - err[">50"]) < AGE_CLOSE:
        choice, reason = ">=50", "close (difference below 1 point), so the primary stays >=50"
    else:
        choice = err.idxmin()
        reason = f"{choice} matches Table 1 group sizes better"
    for subset, g in t1.groupby("subset"):
        if (g["group size diff, pt"] > 100 * GROUP_SIZE_TOLERANCE).all():
            tripwires.append(f"{subset}: both age definitions differ from Table 1 group size by more than 5 points")

    out.append("\n## Summary\n\n" + md_table(pd.DataFrame(summary)) + "\n")
    out.append("\n## Fraud rate by month and variant\n\n" + md_table(pd.DataFrame(by_month)) + "\n")
    out.append(
        "\n## Age group definition against Table 1\n\n"
        "Table 1 (p7) lists group sizes and prevalences for the majority (younger) and minority (older) group. "
        "`mean rel. diff` is the mean of |measured - Table 1| / Table 1 over the three quantities. "
        "`group size diff, pt` is |measured older share - Table 1 share| in percentage points.\n\n"
        + md_table(t1) + "\n"
        + f"\nMean group-size difference from Table 1 over all variants: `>=50` {100 * err['>=50']:.2f} pt, `>50` {100 * err['>50']:.2f} pt. "
        + f"Decision: primary older group `customer_age {choice}`; {reason}.\n"
    )
    for name, df in frames.items():
        stats[name] = audit_variant(name, df, out)
        if stats[name]["cross_split_main"] or stats[name]["cross_split_paper"]:
            tripwires.append(f"{name}: rows identical except month in more than one split: {stats[name]}")
    out.append("\n## Tripwires\n\n" + ("\n".join(f"- {t}" for t in tripwires) if tripwires else "None fired.") + "\n")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(out))
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "audit.json").write_text(json.dumps(dict(
        files=files, ignored=ignored, tripwires=tripwires, age_choice=choice, age_reason=reason,
        mean_group_size_diff={k: float(v) for k, v in err.items()}, split_overlap=stats,
        base_monthly_fraud_range=BASE_MONTHLY_FRAUD_RANGE), indent=1))
    print(f"wrote {REPORT}; tripwires: {tripwires or 'none'}; age choice {choice}")
    if tripwires and TRIPWIRES_FATAL:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
