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

REPORT = Path(__file__).resolve().parent.parent / "reports" / "data_audit.md"
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
    out.append(
        f"\nSplit overlap. Splits are by month, so a row cannot be in two splits by construction. "
        f"Exact duplicate rows within the file: {full_dupes}. "
        f"Rows identical in every column except `month` that occur in more than one split: "
        f"main split {cross_split_duplicates(df, MAIN_SPLIT)}, paper split {cross_split_duplicates(df, PAPER_SPLIT)}.\n"
    )


def main():
    files = list_raw_files(RAW_DIR)
    out = ["# Data audit\n", "Generated by `python -m src.audit` (`make audit`) from `data/raw/`. No numbers in this file are edited by hand.\n"]
    out.append("\n## Files\n\n" + md_table(pd.DataFrame(
        [{"file": f, "bytes": (RAW_DIR / f).stat().st_size, "sha256": sha256(RAW_DIR / f)} for f in files]
    )) + "\n")
    missing = [v for v, f in VARIANT_FILES.items() if f not in files]
    if len(VARIANT_FILES) != 6 or missing:
        raise SystemExit(f"Expected six mapped variant files in {RAW_DIR}; mapping={VARIANT_FILES}, missing={missing}, found={files}")

    summary, t1 = [], []
    frames = {}
    for name in VARIANT_FILES:
        df = load_variant(name)
        frames[name] = df
        summary.append({"variant": name, "rows": len(df), "fraud rate": df[LABEL].mean(), "months": f"{df['month'].min()}-{df['month'].max()}"})
        t1.extend(table1_rows(name, df))

    out.append("\n## Summary\n\n" + md_table(pd.DataFrame(summary)) + "\n")
    out.append(
        "\n## Age group definition against Table 1\n\n"
        "Table 1 (p7) lists group sizes and prevalences for the majority (younger) and minority (older) group. "
        "`mean rel. diff` is the mean of |measured - Table 1| / Table 1 over the three quantities. Lower is closer.\n\n"
        + md_table(pd.DataFrame(t1)) + "\n"
    )
    for name, df in frames.items():
        audit_variant(name, df, out)

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(out))
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
