"""Loading, missing-value sentinels, month splits and protected groups.

Column names, ranges and sentinels follow the BAF datasheet (A7, A8). See PROTOCOL.md.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import RAW_DIR

LABEL = "fraud_bool"

CATEGORICAL = ["payment_type", "employment_status", "housing_status", "source", "device_os"]

# Explicit dtypes for every column the datasheet lists, plus the two columns that
# Variants III and V append (mvn.py). Any other column makes loading fail.
DTYPES = {
    "income": "float64",
    "name_email_similarity": "float64",
    "prev_address_months_count": "int64",
    "current_address_months_count": "int64",
    "customer_age": "int64",
    "days_since_request": "float64",
    "intended_balcon_amount": "float64",
    "payment_type": "str",
    "zip_count_4w": "int64",
    "velocity_6h": "float64",
    "velocity_24h": "float64",
    "velocity_4w": "float64",
    "bank_branch_count_8w": "int64",
    "date_of_birth_distinct_emails_4w": "int64",
    "employment_status": "str",
    "credit_risk_score": "int64",
    "email_is_free": "int64",
    "housing_status": "str",
    "phone_home_valid": "int64",
    "phone_mobile_valid": "int64",
    "bank_months_count": "int64",
    "has_other_cards": "int64",
    "proposed_credit_limit": "float64",
    "foreign_request": "int64",
    "source": "str",
    "session_length_in_minutes": "float64",
    "device_os": "str",
    "keep_alive_session": "int64",
    "device_distinct_emails_8w": "int64",
    "device_fraud_count": "int64",
    "month": "int64",
    "fraud_bool": "int64",
    "x1": "float64",
    "x2": "float64",
}

# Datasheet A7: "-1 is a missing value" for these columns.
MINUS_ONE_MISSING = [
    "prev_address_months_count",
    "current_address_months_count",
    "bank_months_count",
    "session_length_in_minutes",
    "device_distinct_emails_8w",
]
# Datasheet A7: "negatives are missing values".
NEGATIVE_MISSING = ["intended_balcon_amount"]

MAIN_SPLIT = dict(train=[0, 1, 2], validation=[3], test=[4, 5, 6, 7])
PAPER_SPLIT = dict(train=[0, 1, 2, 3, 4, 5], test=[6, 7])

# Names as listed in data/raw/ on 2026-10-16 (reports/progress.md), not assumed.
VARIANT_FILES = {
    "Base": "Base.csv",
    "Variant I": "Variant I.csv",
    "Variant II": "Variant II.csv",
    "Variant III": "Variant III.csv",
    "Variant IV": "Variant IV.csv",
    "Variant V": "Variant V.csv",
}


def list_raw_files(raw_dir=RAW_DIR):
    return sorted(p.name for p in Path(raw_dir).iterdir() if p.is_file())


def load_variant(variant, raw_dir=RAW_DIR):
    path = Path(raw_dir) / VARIANT_FILES[variant]
    header = pd.read_csv(path, nrows=0).columns.tolist()
    unknown = [c for c in header if c not in DTYPES]
    if unknown:
        raise ValueError(f"{path.name}: columns not in the datasheet: {unknown}")
    return pd.read_csv(path, dtype={c: DTYPES[c] for c in header})


def apply_sentinels(df):
    out = df.copy()
    for col in MINUS_ONE_MISSING:
        if col in out:
            out[col] = out[col].astype("float64").mask(out[col] == -1)
    for col in NEGATIVE_MISSING:
        if col in out:
            out[col] = out[col].astype("float64").mask(out[col] < 0)
    return out


def split_by_month(df, split):
    return {name: df[df["month"].isin(months)] for name, months in split.items()}


def age_group(customer_age, definition):
    """1 for the older group, 0 otherwise. Ages are decade-rounded (datasheet A7)."""
    if definition == ">=50":
        return (customer_age >= 50).astype(int)
    if definition == ">50":
        return (customer_age > 50).astype(int)
    raise ValueError(f"unknown age group definition: {definition!r}")


def stratified_sample(df, fraction, seed):
    """Sample ``fraction`` of rows within every (month, label) cell."""
    rng = np.random.default_rng(seed)
    picked = []
    for _, idx in df.groupby(["month", LABEL]).groups.items():
        n = int(round(len(idx) * fraction))
        picked.append(rng.choice(np.asarray(idx), size=n, replace=False))
    return df.loc[np.sort(np.concatenate(picked))]
