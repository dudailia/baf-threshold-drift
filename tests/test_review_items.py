"""Direct tests for the five items the leakage code review marked suspicious (reports/code_review.md, 13c to 13i).

13c (duplicate rows across months) needs the real data and is checked by reports/final_check/duplicates.py.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from sklearn import metrics

from src.data import MAIN_SPLIT
from src.metrics import confusion, notebook_operating_point, rates

ROOT = Path(__file__).resolve().parent.parent


def _run(code, **env):
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=dict(os.environ, **env), capture_output=True, text=True, check=True).stdout


# 13f: checkpoints and predictions follow BAF_OUT, and the only reduced run (make sample) writes to its own folder.
def test_checkpoint_paths_follow_baf_out(tmp_path):
    out = _run("from src import config; print(config.CHECKPOINTS); print(config.PREDICTIONS_DIR)", BAF_OUT=str(tmp_path))
    assert out.split() == [str(tmp_path / "results" / "checkpoints"), str(tmp_path / "results" / "predictions")]


def test_make_sample_writes_to_its_own_folder():
    make = (ROOT / "Makefile").read_text()
    recipe = make.split("\nsample:")[1].split("\n\n")[0]
    steps = [line for line in recipe.splitlines() if "-m src." in line]
    assert len(steps) == 2 and all("BAF_SAMPLE=0.1" in s and "BAF_OUT=$(CURDIR)/results/sample_run" in s for s in steps)


# 13g: the replication reproduces notebook cell 10 of the BAF repo, which reads TPR ("recall") at the ROC point
# and binarizes with ">" for the group FPRs. Lines marked "cell 10" are copied from the notebook (commit 3377cfd).
def test_replication_operating_point_matches_notebook_cell_10():
    rng = np.random.default_rng(0)
    for _ in range(50):
        n = 5000
        y_test = (rng.random(n) < 0.02).astype(int)
        predictions = np.round(rng.normal(y_test * 1.5, 1.0), 2)  # rounded, so ties occur
        fprs, tprs, thresholds = metrics.roc_curve(y_test, predictions)  # cell 10
        threshold = np.min(thresholds[fprs == max(fprs[fprs < 0.05])])  # cell 10
        recall = np.max(tprs[fprs == max(fprs[fprs < 0.05])])  # cell 10
        preds_binary = (predictions > threshold).astype(int)  # cell 10
        nb_fpr = preds_binary[y_test == 0].mean()  # Aequitas fpr = FP / (FP + TN)

        t, tpr = notebook_operating_point(predictions, y_test)
        pred = (predictions > t).astype(float)  # as in src/checks.py
        assert t == threshold and tpr == recall
        assert rates(confusion(pred, y_test, 0.5))["fpr"] == nb_fpr


def test_replication_code_binarizes_like_the_notebook():
    src = (ROOT / "src" / "checks.py").read_text()
    assert "t, tpr_roc = notebook_operating_point(s, y)" in src
    assert "pred = (s > t).astype(float)" in src
    assert "tpr=tpr_roc" in src


# 13h: split months come from MAIN_SPLIT only; no module compares a month with a literal.
def test_split_constants_derive_from_main_split():
    from src import fastboot, schema
    from src.posthoc import hyper, isotonic, mechanism

    assert schema.VALIDATION_MONTH == fastboot.VALIDATION_MONTH == mechanism.VAL == MAIN_SPLIT["validation"][0]
    assert schema.TEST_MONTHS == isotonic.TEST == MAIN_SPLIT["test"]
    assert hyper.EVAL_MONTHS == mechanism.MONTHS == MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]


def test_no_literal_month_comparisons_in_src():
    pattern = re.compile(r"month\w*\s*(==|!=|>=|<=|<|>)\s*\d|\bm\s*(==|!=)\s*\d\b")
    hits = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#")[0]
            if pattern.search(code) and not code.lstrip().startswith(('"', "'")):
                hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert hits == []


# 13i: fixedq reads the isotonic point estimates from BAF_POSTHOC_OUT, the same folder as the isotonic bootstrap.
def test_fixedq_reads_isotonic_metrics_from_posthoc_out(tmp_path):
    code = """
import numpy as np, pandas as pd
from src.posthoc import fixedq
seen = []
class Stop(Exception):
    pass
def fake_load(path, **kw):
    seen.append(str(path))
    return {"boot": np.array({}, dtype=object)}
def fake_read_csv(path, **kw):
    seen.append(str(path))
    raise Stop
fixedq.np.load, fixedq.pd.read_csv = fake_load, fake_read_csv
try:
    fixedq.run("c")
except Stop:
    pass
print("\\n".join(seen))
"""
    seen = _run(code, BAF_POSTHOC_OUT=str(tmp_path), BAF_VARIANTS="Base").split()
    assert seen == [str(tmp_path / "checkpoints" / "isotonic_boot" / "Base.npz"), str(tmp_path / "isotonic_metrics.csv")]
