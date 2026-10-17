"""End-to-end recovery test on the BAF-schema fixture (synthetic, not BAF).

Runs the real train and evaluate commands in a subprocess with paths pointed at a
temporary folder, then checks that the planted drift is recovered with the right
sign of the static budget miss.
"""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tests.baf_fixture import write_fixture

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pipeline")
    write_fixture(tmp / "raw", n_per_month=5000, variants=["Base", "Variant I"])
    env = dict(os.environ, BAF_RAW_DIR=str(tmp / "raw"), BAF_OUT=str(tmp / "out"), BAF_N_TRIALS="2", BAF_N_SEEDS="2",
               BAF_N_BOOT="200", BAF_N_JOBS="2", BAF_VARIANTS="Base,Variant I", BAF_TRIPWIRES_FATAL="0")
    for mod in ("src.train", "src.evaluate"):
        subprocess.run([sys.executable, "-m", mod], cwd=ROOT, env=env, check=True, capture_output=True)
    res = tmp / "out" / "results"
    return {name: pd.read_csv(res / f"{name}.csv") for name in ("metrics", "ci", "summary", "paired")}


def _static(df, variant, months):
    m = df[(df.variant == variant) & (df.model == "lightgbm") & (df.strategy == "static") & np.isclose(df.fpr_target, 0.05)
           & (df.age_def == ">=50") & df.month.isin(months)]
    return m


def test_planted_upward_shift_gives_positive_static_budget_miss(run):
    ci = run["ci"]
    c = ci[(ci.metric == "budget_miss") & (ci.seed == 0)]
    late = _static(c, "Base", [6, 7])
    assert (late["lo"] > 0).all(), late[["month", "estimate", "lo", "hi"]]


def test_planted_downward_shift_gives_negative_static_budget_miss(run):
    ci = run["ci"]
    c = ci[(ci.metric == "budget_miss") & (ci.seed == 0)]
    late = _static(c, "Variant I", [6, 7])
    assert (late["hi"] < 0).all(), late[["month", "estimate", "lo", "hi"]]


def test_drift_free_months_have_smaller_static_miss_than_drifted_months(run):
    m = run["metrics"]
    for v in ("Base", "Variant I"):
        early = _static(m, v, [4, 5])["abs_budget_miss"].max()
        late = _static(m, v, [6, 7])["abs_budget_miss"].min()
        assert early < late


def test_label_free_and_oracle_stay_near_budget_under_planted_shift(run):
    m = run["metrics"]
    sel = m[(m.variant == "Base") & (m.model == "lightgbm") & np.isclose(m.fpr_target, 0.05) & (m.age_def == ">=50") & m.month.isin([6, 7])]
    assert (sel[sel.strategy == "oracle"]["realized_fpr"] <= 0.05).all()
    static_miss = sel[sel.strategy == "static"]["abs_budget_miss"].min()
    assert (sel[sel.strategy == "label_free_val_rate"]["abs_budget_miss"] < static_miss).all()


def test_results_are_stamped_with_predictions_commit(run):
    for name, df in run.items():
        assert df["predictions_commit"].nunique() == 1 and len(df["predictions_commit"].iloc[0]) == 40


def test_no_nan_in_available_rows(run):
    m = run["metrics"]
    avail = m[m.available.astype(bool)]
    assert avail[["realized_fpr", "tpr", "alert_rate", "budget_miss"]].notna().all().all()
