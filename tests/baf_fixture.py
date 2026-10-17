"""Synthetic data in the real BAF schema, with known planted drift. For tests only; not BAF.

Labels depend on credit_risk_score, name_email_similarity, housing_status and
age (older applicants have about twice the fraud rate). Planted drift, months 6
and 7 only, on legitimate applications' credit_risk_score:
  Base       shifted up (towards the fraud direction): a static threshold should go over budget
  Variant I  shifted down: a static threshold should go under budget
  others     no drift
Variants III and V carry x1, x2 as in the real files.
"""

import numpy as np
import pandas as pd

from src.data import VARIANT_FILES

DRIFT = {"Base": +45.0, "Variant I": -45.0}


def make_variant(name, n_per_month, seed):
    rng = np.random.default_rng(seed)
    n = 8 * n_per_month
    month = np.repeat(np.arange(8), n_per_month)
    age = rng.choice([10, 20, 30, 40, 50, 60, 70, 80, 90], n, p=[0.02, 0.25, 0.25, 0.2, 0.13, 0.08, 0.04, 0.02, 0.01])
    y = (rng.random(n) < np.where(age >= 50, 0.03, 0.015)).astype(int)
    housing = rng.choice(["BA", "BB", "BC", "BD", "BE", "BF", "BG"], n)
    crs = rng.normal(130 + 70 * y, 50)
    shift = DRIFT.get(name, 0.0)
    crs = crs + np.where((month >= 6) & (y == 0), shift, 0.0)
    df = pd.DataFrame(
        {
            "fraud_bool": y,
            "income": rng.choice(np.round(np.arange(0.1, 1.0, 0.1), 1), n),
            "name_email_similarity": np.clip(rng.beta(2, 2, n) - 0.15 * y, 0, 1),
            "prev_address_months_count": np.where(rng.random(n) < 0.7, -1, rng.integers(5, 380, n)),
            "current_address_months_count": np.where(rng.random(n) < 0.01, -1, rng.integers(0, 429, n)),
            "customer_age": age,
            "days_since_request": rng.exponential(1.0, n),
            "intended_balcon_amount": np.where(rng.random(n) < 0.7, -rng.uniform(0, 16, n), rng.uniform(0, 114, n)),
            "payment_type": rng.choice(["AA", "AB", "AC", "AD", "AE"], n),
            "zip_count_4w": rng.integers(1, 6830, n),
            "velocity_6h": rng.normal(5000, 3000, n),
            "velocity_24h": rng.uniform(1297, 9586, n),
            "velocity_4w": rng.uniform(2825, 7020, n),
            "bank_branch_count_8w": rng.integers(0, 2404, n),
            "date_of_birth_distinct_emails_4w": rng.integers(0, 39, n),
            "employment_status": rng.choice(["CA", "CB", "CC", "CD", "CE", "CF", "CG"], n),
            "credit_risk_score": np.round(crs).astype(int),
            "email_is_free": rng.integers(0, 2, n),
            "housing_status": housing,
            "phone_home_valid": rng.integers(0, 2, n),
            "phone_mobile_valid": rng.integers(0, 2, n),
            "bank_months_count": np.where(rng.random(n) < 0.25, -1, rng.integers(1, 32, n)),
            "has_other_cards": rng.integers(0, 2, n),
            "proposed_credit_limit": rng.choice([200.0, 500.0, 1000.0, 1500.0, 2000.0], n),
            "foreign_request": rng.integers(0, 2, n),
            "source": rng.choice(["INTERNET", "TELEAPP"], n, p=[0.99, 0.01]),
            "session_length_in_minutes": np.where(rng.random(n) < 0.01, -1, rng.exponential(8, n)),
            "device_os": rng.choice(["linux", "windows", "macintosh", "x11", "other"], n),
            "keep_alive_session": rng.integers(0, 2, n),
            "device_distinct_emails_8w": rng.choice([-1, 0, 1, 2], n, p=[0.01, 0.03, 0.9, 0.06]),
            "device_fraud_count": np.zeros(n, dtype=int),
            "month": month,
        }
    )
    if name in ("Variant III", "Variant V"):
        df["x1"] = rng.normal(size=n) + 1.0 * y * (age < 50) * (month < 6 if name == "Variant V" else 1)
        df["x2"] = rng.normal(size=n)
    return df


def write_fixture(raw_dir, n_per_month=4000, seed=0, variants=None):
    raw_dir.mkdir(parents=True, exist_ok=True)
    for i, (name, fname) in enumerate(VARIANT_FILES.items()):
        if variants and name not in variants:
            continue
        make_variant(name, n_per_month, seed + i).to_csv(raw_dir / fname, index=False)
    return raw_dir


if __name__ == "__main__":
    import sys
    from pathlib import Path

    write_fixture(Path(sys.argv[1]), n_per_month=int(sys.argv[2]) if len(sys.argv) > 2 else 4000)
