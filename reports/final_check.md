# Final check

Run on 2026-10-19 against commit d942846 (working tree clean at the start). Every block below is the command as typed and its raw output, captured to a file and pasted unchanged, with two substitutions so this file does not put the username back into the repository: the absolute repository path is shown as `<repo>/`, and the file owner in `ls -l` is shown as `<user>`. The two searches whose pattern contained the username were run with `$USER` in its place. Choices made during this check are in reports/decisions.md (rows starting "final").

First pass (2026-10-19, commit ef8221b) and second pass (2026-10-19, after the user's decisions A to E):

| Item | First pass | Second pass |
|---|---|---|
| 1 Reviews | PASS | PASS: the five suspicious items are resolved (1b): four fine, 13h wrong and fixed with no number changed |
| 2 Tests and traces | PASS | PASS (110 tests, rerun in 1b) |
| 3 Pre-registration | FAIL | original criterion still FAIL; criterion narrowed after the original failed: PASS (3b) |
| 4 Data and privacy | PASS | PASS; history accepted by the user as is (decision C) |
| 5 Outreach numbers | FAIL (no drafts received) | PASS after rewrites (5b) |
| 6 Visual check | PASS | PASS |
| 7 Publish | NOT RUN | PASS: public repository https://github.com/dudailia/baf-threshold-drift; a fresh clone passes `make test` (7b) |

## 1. Reviews

Both review files exist, so no new reviewer was run. The leakage review has 0 items marked wrong (16 fine, 5 suspicious). The cold read's missing questions are in the call prep under "Added after the cold read".

```
$ ls -l reports/hostile_review.md reports/code_review.md
-rw-r--r--  1 <user>  staff  35678 18 Oct 00:15 reports/code_review.md
-rw-r--r--  1 <user>  staff  13708 18 Oct 00:15 reports/hostile_review.md

$ git log --format="%h %s" -- reports/hostile_review.md reports/code_review.md
849ef64 Leakage code review: nothing wrong, five suspicious items followed up
e083103 Hostile cold read: reviewer file, resolution table, nine questions added to the call prep

$ sed -n 13,36p reports/code_review.md
| Item | Verdict | Main references |
|---|---|---|
| 1. Scalers | fine | src/preprocess.py:47-53 |
| 2. Encoders, category maps, unseen categories | fine | src/preprocess.py:25-36, 50 |
| 3. Imputers, medians, sentinels | fine | src/data.py:94-102; src/preprocess.py:49, 53 |
| 4. Hyperparameter tuning | fine | src/train.py:65-83, 96; src/posthoc/rolling.py:52-63 |
| 5. Early stopping | fine | src/models.py:58-59 |
| 6. Calibration (isotonic) | fine | src/posthoc/isotonic.py:28-31, 47-75 |
| 7. Seed handling | fine | src/models.py:36-55; src/train.py:74, 102; src/checks.py:99-103 |
| 8. Month indexing | fine | src/data.py:67-68; src/train.py:26, 88-90; src/fastboot.py:162-168; src/posthoc/retrain.py:32-35 |
| 9. Tie handling in thresholds | fine | src/thresholds.py:20-49; src/fastboot.py:75-89, 147-161 |
| 10. Delayed-label lag | fine | src/fastboot.py:162-168, 208 |
| 11. Group FPR counts | fine | src/fastboot.py:27-33, 105-131, 170-180 |
| 12. Bootstrap source data and pairing | fine | src/fastboot.py:36-41, 134-189, 216-228; src/posthoc/isotonic.py:60-75 |
| 13a. `month` as a feature | fine | src/preprocess.py:13-15; src/train.py:94 |
| 13b. Features that encode the label | fine | src/preprocess.py:13-15; src/diagnostics.py:79-102 |
| 13c. Duplicate rows across splits | suspicious | src/audit.py:102-112, 179-180 |
| 13d. Oracle tripwire | fine | src/evaluate.py:105-122 |
| 13e. Shuffled-label check | fine | src/checks.py:97-122; src/diagnostics.py:49-54 |
| 13f. Resume from checkpoints without provenance check | suspicious | src/train.py:68-72, 98-100, 113-115; src/evaluate.py:57-60; src/posthoc/common.py:104-107 |
| 13g. Replication operating point (TPR and FPR from different rules) | suspicious | src/checks.py:61-67; src/metrics.py:104-113 |
| 13h. Split months defined in several places | suspicious | src/data.py:67; src/schema.py:16-17; src/fastboot.py:22; src/posthoc/common.py:108; src/posthoc/hyper.py:58; src/posthoc/isotonic.py:25, 48 |
| 13i. fixedq reads isotonic point estimates from a fixed path | suspicious | src/posthoc/fixedq.py:36 against src/posthoc/common.py:21 |


$ grep -c -E "^Verdict: wrong|\| wrong \|" reports/code_review.md
0

$ grep -o -E "^Verdict: [a-z]+|\| (fine|suspicious|wrong) \|" reports/code_review.md | sort | uniq -c
  16 | fine |
   5 | suspicious |
  16 Verdict: fine

$ grep -n "Added after the cold read" prep/call_questions.md docs/call_questions.template.md
prep/call_questions.md:45:## Added after the cold read
docs/call_questions.template.md:45:## Added after the cold read
```

Verdict: PASS. Neither file is missing and no item is "wrong".

### 1b. The five suspicious items, resolved

Decision B (2026-10-19): show the code, test each item directly, and resolve it to fine or wrong. Code excerpts with file and line:

```
## 13c
$ grep -n -A11 'def cross_split_duplicates' src/audit.py
102:def cross_split_duplicates(df, split):
103-    """Rows identical in every column except month that occur in more than one split."""
104-    feats = df.drop(columns=["month"])
105-    h = pd.util.hash_pandas_object(feats, index=False).to_numpy()
106-    part = np.full(len(df), "", dtype=object)
107-    for name, months in split.items():
108-        part[df["month"].isin(months).to_numpy()] = name
109-    frame = pd.DataFrame({"h": h, "part": part})
110-    frame = frame[frame["part"] != ""]
111-    n_parts = frame.groupby("h")["part"].nunique()
112-    return int((n_parts > 1).sum())
113-

$ grep -n 'cross_split_duplicates(' src/audit.py
102:def cross_split_duplicates(df, split):
179:    stats = dict(within_file_duplicates=full_dupes, cross_split_main=cross_split_duplicates(df, MAIN_SPLIT),
180:                 cross_split_paper=cross_split_duplicates(df, PAPER_SPLIT))

## 13f
$ sed -n 11,17p src/config.py
    11	OUT = Path(os.environ.get("BAF_OUT", ROOT))
    12	RESULTS = OUT / "results"
    13	REPORTS = OUT / "reports"
    14	FIGURES = OUT / "figures"
    15	DOCS = Path(os.environ.get("BAF_DOCS", ROOT / "docs"))
    16	PREDICTIONS_DIR = RESULTS / "predictions"
    17	CHECKPOINTS = RESULTS / "checkpoints"

$ sed -n 65,72p src/train.py; sed -n 97,100p src/train.py
    65	def tune(variant, Xtr, ytr, Xval, yval, commit):
    66	    ckpt = config.CHECKPOINTS / "tuning" / f"{variant}.jsonl"
    67	    ckpt.parent.mkdir(parents=True, exist_ok=True)
    68	    done = [json.loads(line) for line in ckpt.read_text().splitlines()] if ckpt.exists() else []
    69	    configs = sample_configs(config.N_TRIALS, CONFIG_SEED)
    70	    for i, cfg in enumerate(configs):
    71	        if i < len(done):
    72	            continue
    97	    log(f"{variant} best trial {best['trial']} val TPR@5%FPR {best['val_tpr_at_5pct_fpr']:.4f}")
    98	    for seed in config.SEEDS:
    99	        if pred_path(variant, "lightgbm", seed).exists():
   100	            continue

$ sed -n 56,60p src/evaluate.py
    56	def evaluate_one(variant, model, seed, n_boot):
    57	    ckpt = config.CHECKPOINTS / "eval" / f"{variant}__{model}__seed{seed}.npz"
    58	    if ckpt.exists():
    59	        z = np.load(ckpt, allow_pickle=True)
    60	        return pd.DataFrame(list(z["point"])), pd.DataFrame(list(z["ci"])), pd.DataFrame(list(z["paired"]))

$ grep -n -A3 '^sample:' Makefile
63:sample: guard
64-	BAF_SAMPLE=0.1 BAF_VARIANTS=Base BAF_OUT=$(CURDIR)/results/sample_run $(PY) -m src.train
65-	BAF_SAMPLE=0.1 BAF_VARIANTS=Base BAF_OUT=$(CURDIR)/results/sample_run $(PY) -m src.evaluate
66-

## 13g
$ sed -n 104,113p src/metrics.py
   104	def notebook_operating_point(scores, labels):
   105	    """Threshold rule of the BAF empirical results notebook (cell 10), for replication only.
   106	
   107	    Picks the ROC point with the largest FPR strictly below 0.05 on the given
   108	    labelled data and returns (threshold, TPR at that ROC point). The notebook
   109	    binarizes with ``score > threshold``.
   110	    """
   111	    fprs, tprs, thresholds = skm.roc_curve(labels, scores)
   112	    best = fprs == fprs[fprs < 0.05].max()
   113	    return float(np.min(thresholds[best])), float(np.max(tprs[best]))

$ grep -n 'notebook_operating_point(s, y)\|pred = (s > t)\|tpr=tpr_roc' src/checks.py
61:            t, tpr_roc = notebook_operating_point(s, y)
62:            pred = (s > t).astype(float)  # notebook binarizes with ">"
66:            rec = dict(with_month=with_month, trial=i, tpr=tpr_roc, realized_fpr=r["fpr"], fpr_young=fy, fpr_old=fo,

$ python3 -I -c '<print the threshold, recall and FPR lines of cell 10>' notebooks/empirical_results.ipynb   # feedzai/bank-account-fraud at 3377cfd, downloaded 2026-10-19, SHA-256 8964df82c3ab1417aeaf39b15d1146d13eddb9813f1d8f014f59387c79b920be (same file on main)
cell10:37: fprs, tprs, thresholds = metrics.roc_curve(y_test, predictions)
cell10:39: threshold = np.min(thresholds[fprs==max(fprs[fprs < 0.05])])
cell10:40: recall = np.max(tprs[fprs==max(fprs[fprs < 0.05])])
cell10:43: preds_binary = (predictions > threshold).astype(int)
cell10:61: results["recall"] = recall
cell10:64: results["fpr Older"] = aequitas_results[aequitas_results["attribute_value"] == "Older"][["fpr"]].values[0][0]
cell10:65: results["fpr Younger"] = aequitas_results[aequitas_results["attribute_value"] == "Younger"][["fpr"]].values[0][0]

## 13h
$ git diff -U0 -- src/checks.py src/posthoc/mechanism.py src/posthoc/values.py src/tables.py
diff --git a/src/checks.py b/src/checks.py
index 835e8dd..d642010 100644
--- a/src/checks.py
+++ b/src/checks.py
@@ -107 +107,2 @@ def shuffled(commit):
-    t_static = threshold_at_fpr(s[m == 3], y[m == 3], 0.05)
+    val = MAIN_SPLIT["validation"][0]
+    t_static = threshold_at_fpr(s[m == val], y[m == val], 0.05)
diff --git a/src/posthoc/mechanism.py b/src/posthoc/mechanism.py
index db291eb..6ae800b 100644
--- a/src/posthoc/mechanism.py
+++ b/src/posthoc/mechanism.py
@@ -28 +28,2 @@ N_DRAWS = 5
-MONTHS = [3, 4, 5, 6, 7]
+MONTHS = MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]  # split months are defined once, in src/data.py
+VAL = MAIN_SPLIT["validation"][0]
@@ -44,2 +45,2 @@ def run(c):
-        neg3 = score[(month == 3) & (label == 0)]
-        t = threshold_at_fpr(score[month == 3], label[month == 3], TARGET)
+        neg3 = score[(month == VAL) & (label == 0)]
+        t = threshold_at_fpr(score[month == VAL], label[month == VAL], TARGET)
@@ -50 +51 @@ def run(c):
-                               realized_fpr=fpr, one_minus_fpr=1 - fpr, ks_vs_month3_negatives=float(ks_2samp(neg3, neg).statistic) if m != 3 else 0.0))
+                               realized_fpr=fpr, one_minus_fpr=1 - fpr, ks_vs_month3_negatives=float(ks_2samp(neg3, neg).statistic) if m != VAL else 0.0))
@@ -53 +54 @@ def run(c):
-        ref = neg_rows[neg_rows.month == 3]
+        ref = neg_rows[neg_rows.month == VAL]
diff --git a/src/posthoc/values.py b/src/posthoc/values.py
index e078652..1073337 100644
--- a/src/posthoc/values.py
+++ b/src/posthoc/values.py
@@ -11,0 +12 @@ from src.posthoc.common import OUT
+from src.schema import TEST_MONTHS, VALIDATION_MONTH
@@ -83 +84 @@ def build():
-        cols = [f"psi_month_{m}" for m in range(3, 8)]
+        cols = [f"psi_month_{m}" for m in [VALIDATION_MONTH] + TEST_MONTHS]
@@ -129 +130 @@ def _mechanism(q, f, rc, d):
-    test = q[q.month >= 4]
+    test = q[q.month.isin(TEST_MONTHS)]
diff --git a/src/tables.py b/src/tables.py
index eccd69c..179a932 100644
--- a/src/tables.py
+++ b/src/tables.py
@@ -18,0 +19 @@ from src.schema import (
+    VALIDATION_MONTH,
@@ -89,2 +90,2 @@ class _Cells:
-        if s.startswith("delayed") and r is not None and r.available and r.source_month == 3:
-            return " (equals static: source month 3)"
+        if s.startswith("delayed") and r is not None and r.available and r.source_month == VALIDATION_MONTH:
+            return f" (equals static: source month {VALIDATION_MONTH})"

$ grep -n 'MAIN_SPLIT\[' src/schema.py src/fastboot.py src/posthoc/hyper.py src/posthoc/isotonic.py src/posthoc/mechanism.py src/checks.py
src/fastboot.py:24:VALIDATION_MONTH = MAIN_SPLIT["validation"][0]
src/checks.py:91:    train = df[df["month"].isin(MAIN_SPLIT["train"])]
src/checks.py:99:    train = df[df["month"].isin(MAIN_SPLIT["train"])]
src/checks.py:104:    ev = df[df["month"].isin(MAIN_SPLIT["validation"] + MAIN_SPLIT["test"])]
src/checks.py:107:    val = MAIN_SPLIT["validation"][0]
src/checks.py:110:    test = np.isin(m, MAIN_SPLIT["test"])
src/checks.py:111:    for label, mask in [(str(k), m == k) for k in MAIN_SPLIT["test"]] + [("4-7 pooled", test)]:
src/checks.py:134:            prep, model = _check_model(df, df.loc[df["month"].isin(MAIN_SPLIT["train"]), LABEL].to_numpy(),
src/checks.py:139:        ref = X[X["month"].isin(MAIN_SPLIT["train"])]
src/posthoc/hyper.py:26:EVAL_MONTHS = MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]
src/posthoc/hyper.py:48:                        tr = df[df.month.isin(MAIN_SPLIT["train"])]
src/schema.py:18:TEST_MONTHS = list(MAIN_SPLIT["test"])  # split months are defined once, in src/data.py
src/schema.py:19:VALIDATION_MONTH = MAIN_SPLIT["validation"][0]
src/posthoc/mechanism.py:28:MONTHS = MAIN_SPLIT["validation"] + MAIN_SPLIT["test"]  # split months are defined once, in src/data.py
src/posthoc/mechanism.py:29:VAL = MAIN_SPLIT["validation"][0]
src/posthoc/mechanism.py:38:        train = df[df.month.isin(MAIN_SPLIT["train"])]

## 13i
$ grep -n 'isotonic_boot\|isotonic_metrics' src/posthoc/fixedq.py; grep -n '^OUT\|^CKPT' src/posthoc/common.py
35:        iso_boot = np.load(CKPT / "isotonic_boot" / f"{v}.npz", allow_pickle=True)["boot"].item()
36:        iso_point = pd.read_csv(OUT / "isotonic_metrics.csv")
22:OUT = Path(os.environ.get("BAF_POSTHOC_OUT", config.ROOT / "results_posthoc"))
24:CKPT = OUT / "checkpoints"
```

New unit tests (tests/test_review_items.py), the red checks showing that they fail on the old code, and the evidence that no number changed:

```
$ .venv/bin/python -m pytest -v tests/test_review_items.py 2>&1 | grep -E "PASSED|FAILED|passed|failed"
tests/test_review_items.py::test_checkpoint_paths_follow_baf_out PASSED  [ 14%]
tests/test_review_items.py::test_make_sample_writes_to_its_own_folder PASSED [ 28%]
tests/test_review_items.py::test_replication_operating_point_matches_notebook_cell_10 PASSED [ 42%]
tests/test_review_items.py::test_replication_code_binarizes_like_the_notebook PASSED [ 57%]
tests/test_review_items.py::test_split_constants_derive_from_main_split PASSED [ 71%]
tests/test_review_items.py::test_no_literal_month_comparisons_in_src PASSED [ 85%]
tests/test_review_items.py::test_fixedq_reads_isotonic_metrics_from_posthoc_out PASSED [100%]
============================== 7 passed in 1.90s ===============================

# red check: the same tests against the 13h code before this commit
$ git stash push -q -- src/checks.py src/posthoc/mechanism.py src/posthoc/values.py src/tables.py; .venv/bin/python -m pytest -q tests/test_review_items.py 2>&1 | grep -E "^FAILED|passed|failed|^E .*first extra"; git stash pop -q
E         Left contains 7 more items, first extra item: 'src/checks.py:107: t_static = threshold_at_fpr(s[m == 3], y[m == 3], 0.05)'
FAILED tests/test_review_items.py::test_split_constants_derive_from_main_split
FAILED tests/test_review_items.py::test_no_literal_month_comparisons_in_src
2 failed, 5 passed in 1.45s

# red check: fixedq reading isotonic_metrics.csv from the fixed path of the code before 849ef64
$ sed -i "" "s#pd.read_csv(OUT / \"isotonic_metrics.csv\")#pd.read_csv(config.ROOT / \"results_posthoc\" / \"isotonic_metrics.csv\")#" src/posthoc/fixedq.py; .venv/bin/python -m pytest -q tests/test_review_items.py -k fixedq 2>&1 | grep -E "^FAILED|passed|failed"; git checkout -q src/posthoc/fixedq.py
FAILED tests/test_review_items.py::test_fixedq_reads_isotonic_metrics_from_posthoc_out
1 failed, 6 deselected in 1.30s

# no number changes: post hoc values rebuilt into a scratch copy of results_posthoc/ with the new code, and the documents re-rendered
$ rsync -a --exclude predictions --exclude checkpoints --exclude logs results_posthoc/ <scratch>/; rm <scratch>/values.json
$ BAF_POSTHOC_OUT=<scratch> .venv/bin/python -m src.posthoc.values > /dev/null; echo "exit=$?"
exit=0
$ cmp <scratch>/values.json results_posthoc/values.json; echo "exit=$?"
exit=0
$ make tables; git status --short -- RESULTS.md README.md reports/one_pager.md RESULTS_POSTHOC.md prep/call_questions.md results results_posthoc; echo "exit=$?"
exit=0
```

Targeted checks on the real data and checkpoints (scripts in reports/final_check/; they read files and write nothing):

```
$ .venv/bin/python -m reports.final_check.duplicates
Base         with label     rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Base         without label  rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant I    with label     rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant I    without label  rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant II   with label     rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant II   without label  rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant III  with label     rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant III  without label  rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant IV   with label     rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant IV   without label  rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant V    with label     rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
Variant V    without label  rows 1,000,000 month pairs 28 pairs with shared rows 0 max shared 0
exit=0

$ .venv/bin/python -m reports.final_check.provenance
prediction metadata files: 60
sample_fraction: {1.0: 60}
predictions_commit: {'0be4b0ddf844b12493d29d3585329fa792f203ab': 60}
Base         tuning trials 20 (ids 0..19) commits ['0be4b0d'] | n_train in metadata [397039] vs data months 0-2 397,039 | rows per prediction file [602961] vs data months 3-7 602,961 | lightgbm config = best tuning trial True
Variant I    tuning trials 20 (ids 0..19) commits ['0be4b0d'] | n_train in metadata [397039] vs data months 0-2 397,039 | rows per prediction file [602961] vs data months 3-7 602,961 | lightgbm config = best tuning trial True
Variant II   tuning trials 20 (ids 0..19) commits ['0be4b0d'] | n_train in metadata [397038] vs data months 0-2 397,038 | rows per prediction file [602962] vs data months 3-7 602,962 | lightgbm config = best tuning trial True
Variant III  tuning trials 20 (ids 0..19) commits ['0be4b0d'] | n_train in metadata [327917] vs data months 0-2 327,917 | rows per prediction file [672083] vs data months 3-7 672,083 | lightgbm config = best tuning trial True
Variant IV   tuning trials 20 (ids 0..19) commits ['0be4b0d'] | n_train in metadata [327918] vs data months 0-2 327,918 | rows per prediction file [672082] vs data months 3-7 672,082 | lightgbm config = best tuning trial True
Variant V    tuning trials 20 (ids 0..19) commits ['0be4b0d'] | n_train in metadata [327918] vs data months 0-2 327,918 | rows per prediction file [672082] vs data months 3-7 672,082 | lightgbm config = best tuning trial True
Base         main_boot cells 20 max |cache - metrics.csv| 9.02e-17 resamples per array [1000]
Variant I    main_boot cells 20 max |cache - metrics.csv| 1.11e-16 resamples per array [1000]
Variant II   main_boot cells 20 max |cache - metrics.csv| 9.71e-17 resamples per array [1000]
Variant III  main_boot cells 20 max |cache - metrics.csv| 9.71e-17 resamples per array [1000]
Variant IV   main_boot cells 20 max |cache - metrics.csv| 9.71e-17 resamples per array [1000]
Variant V    main_boot cells 20 max |cache - metrics.csv| 9.02e-17 resamples per array [1000]
exit=0
```

Full suite after the change:

```
$ make test; echo "exit=$?"
.venv/bin/python -m pytest -q
........................................................................ [ 65%]
......................................                                   [100%]
110 passed in 28.21s
exit=0
$ make check; echo "exit=$?"
.venv/bin/python -m src.trace check
check: <repo>/RESULTS.md ok
check: <repo>/README.md ok
check: <repo>/reports/one_pager.md ok
check: <repo>/RESULTS_POSTHOC.md ok
check: <repo>/prep/call_questions.md ok
exit=0
```

| Item | Resolution | Evidence |
|---|---|---|
| 13c Duplicate rows across splits | fine | `cross_split_duplicates` (src/audit.py:102-112) is called only for the main and paper splits (src/audit.py:179-180). A direct count over all 28 month pairs of every variant finds 0 shared rows, with and without the label. So no split in the project, including rolling A and B and retraining, shares a row between a fitting month and a threshold or test month. |
| 13f Resume from checkpoints | fine | Checkpoint and prediction paths follow `BAF_OUT` (src/config.py:11-17; test). The only reduced run, `make sample`, writes to results/sample_run (Makefile:63-65; test). All 60 prediction metadata files record sample_fraction 1.0 and commit 0be4b0d. Every variant has 20 tuning trials, the full training row count, the full row count for months 3 to 7, and the final config equal to the best tuning trial. The post hoc main_boot cache equals results/metrics.csv to 1e-16, with 1,000 resamples per array. The clean rebuild (reports/reproducibility.md) produced results/ byte-identically with no checkpoint present. Nothing in this item can carry a test month into fitting. A stale checkpoint could only enter by a manual run that sets `BAF_SAMPLE` without `BAF_OUT`. |
| 13g Replication operating point | fine | Notebook cell 10 of the BAF repo stores `recall = np.max(tprs[...])` from the ROC curve (cell10:40). It computes the group FPRs from `preds_binary = (predictions > threshold)` (cell10:43, 64-65). Cell 13 plots that `recall` in Figure 1. src/checks.py:61-66 does the same, so the mixed rule is the paper's own, copied on purpose, and the comparison with Figure 1 is like for like. The test copies the cell 10 lines and matches them exactly on 50 tied synthetic draws. results/replication.csv is unchanged. |
| 13h Split months in several places | wrong, fixed, no number changed | The 849ef64 fix was incomplete. Literal months remained in src/checks.py:107 (shuffled check), src/posthoc/mechanism.py:28, 44-45, 50, 53, src/posthoc/values.py:83, 129 and src/tables.py:89. These lines now use `MAIN_SPLIT` (via src/schema.py where it was already imported). New tests assert that the constants equal `MAIN_SPLIT`, and that no line in src/ compares a month with a literal; on the old code they fail and list the 7 lines. The new values equal the old literals (3, and 3 to 7), so no output can change. src/posthoc/values.py was rerun into a scratch copy and its values.json is byte-identical. `make tables` leaves every rendered document unchanged. src/checks.py and src/posthoc/mechanism.py were not rerun, because that needs model fits; their change replaces 3 with an expression the test asserts equals 3. Declared post hoc splits (rolling, valmonth, retraining) and reporting windows (months 5 to 7, 6 and 7) keep their own lists, as PROTOCOL.md declares them separately. |
| 13i fixedq fixed path | fine (fixed in 849ef64, now tested) | src/posthoc/fixedq.py reads `CKPT / "isotonic_boot"` and `OUT / "isotonic_metrics.csv"`, both under `BAF_POSTHOC_OUT`. The test runs `fixedq.run` with that variable set to a scratch folder and checks both paths; it fails on the pre-849ef64 line. |

Verdict for item 1 after B: PASS. No item is left wrong. The one wrong item (13h) is fixed with no change to any number in results/ or results_posthoc/.

## 2. Tests and traces

```
$ make test; echo "exit=$?"
.venv/bin/python -m pytest -q
........................................................................ [ 69%]
...............................                                          [100%]
103 passed in 27.77s
exit=0
$ make check; echo "exit=$?"
.venv/bin/python -m src.trace check
check: <repo>/RESULTS.md ok
check: <repo>/README.md ok
check: <repo>/reports/one_pager.md ok
check: <repo>/RESULTS_POSTHOC.md ok
check: <repo>/prep/call_questions.md ok
exit=0
```

Verdict: PASS. Both commands exit 0 (103 tests passed; all five traced documents ok).

## 3. Pre-registration

```
$ git log --format="%H %ad %s" --date=iso -- PREDICTIONS.md
0be4b0ddf844b12493d29d3585329fa792f203ab 2026-10-16 18:31:15 -0400 Pre-register predictions

$ git log --reverse --format="%H %ad %s" --date=iso -- results/ | head -1
13e37ade02c2217595bcede3059e681eb62ee6ce 2026-10-16 16:03:13 -0400 Add synthetic mechanism study of threshold strategies under controlled shifts

$ git show --stat --format="%H %s" 13e37ade -- results/
13e37ade02c2217595bcede3059e681eb62ee6ce Add synthetic mechanism study of threshold strategies under controlled shifts

 results/synthetic/mechanism.csv | 96 +++++++++++++++++++++++++++++++++++++++++
 1 file changed, 96 insertions(+)

$ git merge-base --is-ancestor 0be4b0d 13e37ade; echo "exit=$?"
exit=1

$ git merge-base --is-ancestor 13e37ade 0be4b0d; echo "exit=$?"
exit=0

$ git diff --stat 0be4b0d HEAD -- PREDICTIONS.md; echo "lines=$(git diff 0be4b0d HEAD -- PREDICTIONS.md | wc -l)"
lines=       0

$ git diff --exit-code 0be4b0d -- PREDICTIONS.md; echo "exit=$?"
exit=0

$ git log --reverse --format="%h %ad %s" --date=iso -- results/ ":(exclude)results/synthetic" | head -1
11f2b3d 2026-10-16 20:56:50 -0400 Run data audit; record final age-group definition before modelling

$ git merge-base --is-ancestor 0be4b0d 11f2b3d; echo "exit=$?"
exit=0
```

Verdict: FAIL. The first commit that wrote a file in results/ is 13e37ad (results/synthetic/mechanism.csv, 2026-10-16 16:03), and it is an ancestor of the commit that added PREDICTIONS.md, 0be4b0d (18:31): `git merge-base --is-ancestor 0be4b0d 13e37ade` exits 1. PREDICTIONS.md itself is unchanged since 0be4b0d (diff empty, exit 0).

What the earlier file is: output of src/synthetic.py, a simulation that draws scores from `np.random.default_rng` and reads no BAF data. data/raw/ did not exist until after the pre-registration commit (reports/progress.md, 2026-10-16 18:32: "data/raw/ does not exist"). The first results/ commit outside results/synthetic/ is 11f2b3d (the data audit), and 0be4b0d is its ancestor (exit 0). The criterion as written is not met, and it is not redefined here. Whether a synthetic simulation counts as "a file in results/" for pre-registration is your call.

### 3b. Criterion narrowed after the original failed

The user's decision A (2026-10-19): keep the FAIL above and add this narrower check. The narrower criterion was set after the original failed. Here, 0be4b0d (the commit that added PREDICTIONS.md) must be an ancestor of the first commit that wrote any BAF-derived result, and of every later commit that touches results/ or results_posthoc/.

```
$ git log --reverse --format="%h %ad %s" --date=iso -- results/ ":(exclude)results/synthetic" | head -1
11f2b3d 2026-10-16 20:56:50 -0400 Run data audit; record final age-group definition before modelling

$ git merge-base --is-ancestor 0be4b0d 11f2b3d; echo "exit=$?"
exit=0

$ for c in $(git log --reverse --format=%h -- results/ results_posthoc/); do git merge-base --is-ancestor 0be4b0d $c; echo "$c exit=$? $(git log -1 --format=%s $c | cut -c1-70)"; done
13e37ad exit=1 Add synthetic mechanism study of threshold strategies under controlled
11f2b3d exit=0 Run data audit; record final age-group definition before modelling
6d0ce24 exit=0 Run Stage F checks: replication within bound, shuffled-label tripwire 
3fa2ccf exit=0 Record shuffled-label check as failed; add post hoc diagnostics and ha
9c04644 exit=0 Run full study on all six variants; results, figures and scored predic
4d640ce exit=0 Add independent recomputation check: zero mismatches
5d0954c exit=0 Fix differing-row count in independent check summary
125042c exit=0 Write README, RESULTS and one-pager from templates; every number trace
bb31c6b exit=0 Post hoc task 1: rolling-origin results
87dc9a3 exit=0 Post hoc write-up: section 1 (rolling-origin)
50cef9e exit=0 Post hoc task 2: mechanism results (exploratory)
284e2ed exit=0 Draft call prep template; post hoc values read the main independent-ch
f6ed963 exit=0 Post hoc task 3: hyperparameter sensitivity results and write-up
e5935e1 exit=0 Post hoc task 4: retraining results and write-up (exploratory)
89a7e0c exit=0 Post hoc task 5: isotonic label-free targeting results and write-up (e
31d8e3d exit=0 Post hoc tasks 6 and 7 complete: independent check, contradictions sec
994ac07 exit=0 Add Amendment 2026-10-17 to RESULTS.md and reword the README headline
666150a exit=0 Post hoc analyses 6 and 7: validation month with fixed model; fixed-sh
de62d43 exit=0 Fix prose flagged by an independent claims audit; tighten the one-page
d80a5ea exit=0 Limits: quote the data origin (Kaggle page, datasheet A6 and A14) and 
60a0962 exit=0 Fix prose flagged by a second claims audit

$ git log --format="%h %s" -- results/synthetic/
13e37ad Add synthetic mechanism study of threshold strategies under controlled shifts

$ git show 13e37ad:src/synthetic.py | grep -n -E "read_csv|load_variant|data/raw|RAW_DIR|default_rng"
57:    rng = np.random.default_rng(seed)

$ head -3 results/synthetic/mechanism.csv
scenario,month,strategy,fpr,tpr,alert_share,prevalence,fpr_old,alert_share_old,application_share_old,fpr_young,alert_share_young,application_share_young,fpr_ratio,budget_miss,identity_fpr
(0) no shift,0,static,0.049999898902280966,0.6017682814514643,0.055991,0.010858,0.08933450230395955,0.35166366023110857,0.19979,0.04026821092668212,0.6483363397688914,0.80021,0.4507576567636771,-1.0109771903660247e-07,0.049999898902280966
(0) no shift,0,label_free_top,0.044206999601674984,0.5777307054706208,0.05,0.010858,0.0800473025323166,0.35564,0.19979,0.035339828843393976,0.64436,0.80021,0.4414868174867807,-0.005793000398325018,0.04420699960167499

$ git check-ignore -v data/raw/Base.csv; echo "exit=$?"
.gitignore:1:data/	data/raw/Base.csv
exit=0

$ git log --all --format=%h -- data/ | wc -l
       0

$ git merge-base --is-ancestor 290a3c0 6d0ce24; echo "exit=$?"
exit=0

$ git show 13e37ad:src/synthetic.py | grep -n -E "^(import|from) "
12:from dataclasses import dataclass, replace
14:import numpy as np
15:import pandas as pd
17:from src.metrics import confusion, fpr_ratio, rates
18:from src.thresholds import flag, threshold_at_fpr, threshold_top_fraction
```

Verdict for the narrowed criterion: PASS. Every commit that touches results/ or results_posthoc/ has 0be4b0d as an ancestor (exit 0), except 13e37ad. That commit (exit 1) predates PREDICTIONS.md and writes only results/synthetic/mechanism.csv. The file holds simulated data from src/synthetic.py, which imports only numpy, pandas and the project's metric and threshold functions, and reads no file. data/raw/ is in .gitignore and no commit has ever touched data/, so git cannot show when the BAF CSV files arrived on disk. The evidence that they arrived after the pre-registration is the log line in reports/progress.md, not git. REVIEWING.md section 1 now says exactly this.

## 4. Data and privacy

```
$ git ls-files data/

$ git ls-files -z | xargs -0 ls -l | sort -k5 -n -r | head -5 | awk '{print $5, $9}'
8132745 results/summary.csv
7254593 results/metrics.csv
3458487 results/ci.csv
2040860 results/paired.csv
1058083 results/values.json

$ git grep -n -I "/Users/" -- . ; echo "exit=$?"
reports/hygiene.md:11:| Absolute paths with the username | Absolute paths under `/Users/<username>/` appear in the independent checkers' scripts, kept verbatim as records; one also contains a `/private/tmp/` scratch path that includes the username. They are present in 21 commits (main check) and 3 commits (post hoc check). | reports/independent_check/bootstrap.py, compare.py, recompute.py; reports/independent_check_posthoc/check.py | Fixed on 2026-10-17: the paths are now relative to the repository root (the post hoc checker writes to the ignored `checker_output/`), and the post hoc checker was rerun from the repository root with 0 mismatches. Earlier commits still contain the absolute paths unless history is rewritten. |
exit=0

$ git grep -n -I -E "(^|[^0-9.])00[0-9]{7}([^0-9]|$)" -- . ":(exclude)results" ":(exclude)results_posthoc" ; echo "exit=$?"
exit=1

$ git grep -c -I -E "(^|[^0-9.])00[0-9]{7}([^0-9]|$)" -- results results_posthoc ; echo "exit=$?"
exit=1

$ git grep -n -I -E "\(?[0-9]{3}\)?[-. ][0-9]{3}[-. ][0-9]{4}|\+1[ -]?[0-9]{3}" -- . ; echo "exit=$?"
reports/related_work.md:15:4. *TEMPLAR fraud: a verifier grounded calibrated and cost sensitive framework for transaction fraud detection.* Hossain, Akter, Chy et al. Discover Data, 2026. Opened: https://api.openalex.org/works/doi:10.1007/s44248-026-00117-y. It combines several model components with calibration and a validation-selected cost-sensitive threshold, evaluated on BAF Base and IEEE-CIS with chronological splits and a "temporal future-slice" test. It sets a threshold on validation and tests it later on BAF, but it reports AUROC, AUC-PR, F1 and savings rather than realized FPR against a budget, and does not compare recalibration strategies or look at age groups (abstract only).
exit=0

$ git grep -n -I -i -E "AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|sk-[A-Za-z0-9]{20,}|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY|(password|passwd|secret|api_key|apikey|access_token|auth_token)[\"' ]*[:=]|kaggle\.json|KAGGLE_KEY" -- . ; echo "exit=$?"
README.md:20:With the Kaggle command line and a token in `~/.kaggle/kaggle.json`: `kaggle datasets download -d sgpjesus/bank-account-fraud-dataset-neurips-2022 -p data/raw --unzip`. Each file has 1,000,000 rows; `make audit` checks the names, row counts, months and columns and stops if anything is off. `data/` is in .gitignore, so data are not committed (reports/hygiene.md).
docs/README.template.md:20:With the Kaggle command line and a token in `~/.kaggle/kaggle.json`: `kaggle datasets download -d sgpjesus/bank-account-fraud-dataset-neurips-2022 -p data/raw --unzip`. Each file has 1,000,000 rows; `make audit` checks the names, row counts, months and columns and stops if anything is off. `data/` is in .gitignore, so data are not committed (reports/hygiene.md).
reports/progress.md:16:| 2026-10-16 18:32 | D | STOPPED. data/raw/ does not exist; kaggle CLI not installed (PATH, anaconda, venv); no token at ~/.kaggle/kaggle.json or ~/.config/kaggle/; no KAGGLE_ environment variables; no BAF CSVs found by name under the home directory. Stages E to K not started. (elapsed 0m32s) |
exit=0

$ git grep -n -I -E "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" -- . ; echo "exit=$?"
reports/hygiene.md:8:| Personal email in files | No personal email in any tracked file, in any commit. The only email address ever committed is `t@example.com` in tests/test_guard.py. | | None needed. |
tests/test_guard.py:15:    git(tmp_path, "config", "user.email", "t@example.com")
exit=0

$ git grep -n -I -i "$USER\|icloud\|northeastern.edu" -- . ; echo "exit=$?"
reports/hygiene.md:7:| Personal email | Every commit's author and committer email is a personal address (an icloud.com address). | Git commit metadata, all commits | None. Removing it requires rewriting history (for example `git filter-repo --mailcallback` or a `.mailmap` plus a rewrite), which is irreversible; left for the owner to decide before publishing. Setting `git config user.email` to a GitHub noreply address would avoid it in future commits. |
exit=0

$ git grep -n -I -E "(^|[^0-9.])[0-9]{9}([^0-9]|$)" -- . ":(exclude)results" ":(exclude)results_posthoc" | cut -c1-120 ; echo "exit=$?"
reports/data_audit.md:10:| Base.csv | 213427735 | 7bf10a37ce07e72e14c1b09e5efee3d27261baff4facc7da767b0474dcf9b809 |
reports/data_audit.md:11:| Variant I.csv | 213400445 | 48c637a255d1fa4515da4286ccb99251412a6d905937ec7c108838ddfc1674bd 
reports/data_audit.md:12:| Variant II.csv | 213537521 | 60bcd971cf28779abb183c3286990cff9a87275bd8b83d9f6054a396c95cc736
reports/data_audit.md:13:| Variant III.csv | 252204320 | 64693e549cff7ef802cf043fc7c937839e5929966e33a0852953b3f4c432133
reports/data_audit.md:14:| Variant IV.csv | 213538370 | c6cddebbad34fa262a278deeb7985e7b669a64308d26e480d8eb85bfd08dac75
reports/data_audit.md:15:| Variant V.csv | 252214315 | 470899bbef97c32a100528d63e863e1b1036df9501df6ef8140e7ec13b7365b4 
reports/decisions.md:28:| datasheet | Datasheet downloaded on 2026-10-17 from raw.githubusercontent.com/feedzai/bank-acc
reports/handoff.md:89:| 1 datasheet check | done | datasheet re-downloaded (same file, SHA-256 prefix 367846738d63ed35);
reports/progress.md:18:| 2026-10-16 20:55 | D | Files in data/raw (listed, not assumed): Base.csv (213427735 bytes), Var
exit=0

$ git check-ignore -v data/.gitkeep; echo "exit=$?"
.gitignore:1:data/	data/.gitkeep
exit=0

$ git rev-list --all | xargs git grep -l -I "/Users/$USER" | wc -l
      94

$ git log --format="%ae %ce" | sort | uniq -c | sed -E "s/[^ @]+@/<redacted>@/g"
  64 <redacted>@icloud.com <redacted>@icloud.com
```

Verdict: PASS for tracked files. `git ls-files data/` prints nothing: no file under data/ is tracked, and there is no data/.gitkeep either, because .gitignore ignores the whole data/ directory. Every other hit is a false positive. The `/Users/` hit is the placeholder `/Users/<username>/` in reports/hygiene.md. The phone-pattern hit is part of a DOI (s44248-026-00117-y). The credential hits are the documented path `~/.kaggle/kaggle.json`, with no key in it. The only email is `t@example.com` in a test. The 9-digit hits are file sizes in bytes and parts of SHA-256 hashes. I do not know your student ID or phone number, so I searched for patterns (9-digit numbers, Northeastern-style IDs starting with 00, US phone formats) and not for the literal values.

Not covered by this item, but it matters for item 7: pushing publishes the full history. Your personal icloud.com address is the author and committer email on all 64 commits. Older versions of 94 files still contain absolute paths with your username (they were fixed in ebd72dc without a history rewrite). Removing either one means rewriting history, which is a hard stop in this task.

## 5. Outreach numbers

```
$ git grep -n -I -i -E "outreach|\[repo link\]" -- . ; echo "exit=$?"
exit=1

$ find . -path ./.venv -prune -o -path ./data -prune -o -iname "*outreach*" -print -o -iname "*draft*" -print
```

Verdict: FAIL. The task message ends with "Drafts:" and has no text after it, so I had no drafts to check. No outreach draft exists anywhere in the repository either (both searches above are empty). reports/outreach_drafts.md records this and is otherwise empty. I did not write drafts myself, because they would not be your drafts and could not be checked against your wording. Every number, MATCH or MISMATCH mark, and rewrite in this item depends on the drafts.

### 5b. Drafts received (decision D)

The nine drafts are in reports/outreach_drafts.md. Each number there has its source file, values.json key and value, and a mark. Traced values used:

```
$ .venv/bin/python <scratchpad>/keys.py
derived/static/miss_m567/min = -0.0232379823320203
derived/static/miss_m567/max = -0.0086930039918289
derived/static/ci_m567_below_zero = 18
derived/static/ci_m567_n = 18
main/static_ci_width_m567/min = 0.002286251607781103
main/static_ci_width_m567/max = 0.0031835009345387993
rolling/A/static/miss_all/min = 0.0033186605879578
rolling/A/static/miss_all/max = 0.0581662560698357
valmonth/m5/n_positive = 9
valmonth/m5/n = 12
valmonth/n_test_cells_sign_depends_on_m = 9
valmonth/n_test_cells_multi_m = 18
derived/ratio_spread_across_strategies/max = 0.09371185199349974
derived/Variant IV/label_free_top/alert_share_old_m67/max = 0.8941798941798942
derived/Variant IV/application_share_old_m67/max = 0.5057828527760633
retrain/vs_lag1/n_higher_fpr = 16
retrain/vs_lag1/n = 18
retrain/vs_lag1/corr_tpr_gain_fpr_gain = 0.8106284768077181
retrain/tpr_minus_lag1/min = -0.0067064083457525
retrain/tpr_minus_lag1/max = 0.0660569105691056
retrain/miss/min = -0.0196607687781381
retrain/miss/max = 0.0175706066455518
fixedq/top_5.75pct/n_within_0.5pt = 24
fixedq/top_5.75pct/n = 24
isotonic/n_within_0.5pt = 24
isotonic/n = 24
derived/delayed_lag1/miss_all/min = -0.0208649597584659
derived/delayed_lag1/miss_all/max = 0.0124355778781461
derived/label_free_val_rate/absmiss_all/n_within_0.5pt = 22
derived/label_free_val_rate/absmiss_all/n_cells = 24
derived/Variant V/oracle/tpr_m45 = 0.75064154138363
derived/Variant V/oracle/tpr_m67 = 0.3359222378195005
derived/Variant V/static/tpr_m45 = 0.7256586476500125
derived/Variant V/static/tpr_m67 = 0.3002478505000877
derived/Variant V/label_free_top/tpr_m45 = 0.7230099208825781
derived/Variant V/label_free_top/tpr_m67 = 0.32811896824004205
derived/Variant V/label_free_val_rate/tpr_m45 = 0.7525152602934608
derived/Variant V/label_free_val_rate/tpr_m67 = 0.3555572615078668
derived/Variant V/delayed_lag1/tpr_m45 = 0.7240938190360036
derived/Variant V/delayed_lag1/tpr_m67 = 0.34569442007369716
pred/n_hit = 7
pred/n_total = 15
```

Summary of the marks (full tables in reports/outreach_drafts.md):

| Draft | Result | Changed sentence |
|---|---|---|
| Jean V. Alves | QUALIFIED | the threshold month (3) was missing; "set on a different month it over-spent" was post hoc split A, with the model trained on months 0 and 1 |
| Vasco Pearson | QUALIFIED | "flipping in 9 of 18" counts seed-mean signs over the 18 variant-months with more than one threshold month, post hoc; replaced by the month 3 or 4 against month 5 result (9 of 12) |
| Francisco Souza e Silva | QUALIFIED and MISMATCH | 89% and 51% hold for months 6 and 7 and top 5% only; "Recalibration holds the budget" is false for lag 1 (-2.09 to +1.24) and top 5% |
| João David | MISMATCH | "retraining raised detection": the TPR difference against lag 1 runs from -0.67 to +6.61 points |
| Inês Oliveira e Silva | MATCH | none |
| Danielle Caled | MATCH | none |
| João Margato | QUALIFIED | 75.1% and 33.6% are oracle means for months 4 and 5 against 6 and 7; "Oracle (upper bound)" and "at 5% FPR" added; "can hold an alert budget" was too broad |
| Pankaj Dhariwal | QUALIFIED | threshold month and post hoc context added; "far better" replaced by the traced 22 of 24 |
| LinkedIn post | QUALIFIED and MISMATCH | 14 predictions scored as 15 lines (not 15 predictions); "the repo explains why" replaced by "reports it" (the cause is not established); post hoc context for 5.82 |

Verdict: PASS after rewrites. Every number in the final drafts matches its source, and the needed context is in the text. Each message is under 600 characters with the repository URL in place (largest: 599). None has an em dash.

## 6. Visual check

```
$ pdfinfo reports/one_pager.pdf | grep -E "Pages|Page size"
Pages:           1
Page size:       612 x 792 pts (letter)

$ pdftoppm -r 110 -png reports/one_pager.pdf <scratchpad>/img/one_pager; ls <scratchpad>/img
one_pager-1.png

$ git diff --exit-code 1306af0 HEAD -- reports/one_pager.md reports/one_pager.pdf figures/; echo "exit=$?"
exit=0

$ git status --short reports/one_pager.md reports/one_pager.pdf figures/; echo "exit=$?"
exit=0

$ pdftotext -layout reports/one_pager.pdf - | tail -6
it stays a caveat. BAF is synthetic: per the datasheet (answers A6, p1, and A14, p4) and the Kaggle page, it was sampled
from a CTGAN trained on noise-perturbed bank data, so month-to-month shifts may reflect the generator rather than
applicant behaviour. One main split, no retraining in the main study; no single feature among the ten most important
explains the static miss. The contribution is a measurement on BAF and a month-by-month strategy comparison by
budget miss, not the observation that thresholds drift.

$ pdftotext -layout reports/one_pager.pdf - | grep -n -i -E "oracle|TPR"
2:Question. A fraud model’s threshold is set once at 5% FPR. How far do realized FPR, TPR and alert volume drift later,
8:month), and an oracle on each month’s own labels (an upper bound, not deployable). The primary comparison is budget
18:the alerts. Since FPR = (alert share - TPR x prevalence) / (1 - prevalence), 5% FPR here means flagging 5.26% to 6.10%
25:Limits. The shuffled-label check failed its declared tolerance (pooled TPR 0.117 at 5% FPR, against 0.05 plus or minus

$ for f in figures/*.png; do sips -g pixelWidth -g pixelHeight "$f" | tr "
" " "; echo; done
figures/fpr_ratio_by_month.png   pixelWidth: 1530   pixelHeight: 810 
figures/realized_fpr_by_month.png   pixelWidth: 1530   pixelHeight: 810 
figures/roc_operating_points.png   pixelWidth: 1920   pixelHeight: 2520 
figures/synthetic_mechanism.png   pixelWidth: 2250   pixelHeight: 840 
figures/tpr_by_month.png   pixelWidth: 1530   pixelHeight: 1440 
```

Opened and inspected: the rendered one-pager page, plus figures/realized_fpr_by_month.png, tpr_by_month.png, roc_operating_points.png, fpr_ratio_by_month.png and synthetic_mechanism.png.

Verdict: PASS.
- The PDF has one letter page. The last line of the Limits paragraph is on the page, and the lower third of the page is empty.
- No figure has a clipped title, axis label, panel or legend.
- The oracle has a label in every place it appears. Each of the five figure legends reads "Oracle (upper bound, not deployable)", and the one-pager reads "an oracle on each month's own labels (an upper bound, not deployable)".
- Every TPR value has its FPR next to it. tpr_by_month.png pairs each TPR panel with the realized FPR panel above it. roc_operating_points.png puts FPR on the x axis. synthetic_mechanism.png shows realized FPR above TPR.
- In the one-pager, "TPR" appears three times: in the question, in the formula, and as the shuffled-label value "pooled TPR 0.117 at 5% FPR". That last value is the TPR at a threshold set on the same months' own labels at 5% FPR (src/checks.py:112-114 after the 13h edit, column `oracle_tpr_at_5pct_fpr`), so 5% is the FPR it was read at.

The PDF was not rebuilt, because reports/one_pager.md, the PDF and figures/ are unchanged since 1306af0 (the visual check), when the PDF was last built from that text.

## 7. Publish

Not run, because items 3 and 5 failed. Nothing was created on GitHub, no remote was added and nothing was pushed. `gh auth status` was run read-only so that the instructions below are correct. It reports a login to github.com as account dudailia, protocol https, with the `repo` scope. The repository's branch is `main`; there is no `master` branch.

### 7b. Publish (decision E)

A, B and D pass, and decision C accepts the history as it is (email and old absolute paths, no rewrite), so the repository was published. The local branch is `main`; there is no `master`. The token line of `gh auth status` is left out.

```
$ gh auth status 2>&1 | grep -v Token
github.com
  ✓ Logged in to github.com account dudailia (keyring)
  - Active account: true
  - Git operations protocol: https

$ gh repo view dudailia/baf-threshold-drift --json url 2>&1; echo "exit=$?"
GraphQL: Could not resolve to a Repository with the name 'dudailia/baf-threshold-drift'. (repository)
exit=1

$ gh repo create dudailia/baf-threshold-drift --public; echo "exit=$?"
https://github.com/dudailia/baf-threshold-drift
exit=0

$ git remote add origin https://github.com/dudailia/baf-threshold-drift.git; git remote -v
origin	https://github.com/dudailia/baf-threshold-drift.git (fetch)
origin	https://github.com/dudailia/baf-threshold-drift.git (push)

$ git push -u origin main 2>&1; echo "exit=$?"
To https://github.com/dudailia/baf-threshold-drift.git
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
exit=0

$ git push origin --tags 2>&1; echo "exit=$?"
To https://github.com/dudailia/baf-threshold-drift.git
 * [new tag]         v1.0-for-review -> v1.0-for-review
exit=0

$ git ls-remote origin
027daf2b74962f3dd0acbe6b26f61e931a57b95a	HEAD
027daf2b74962f3dd0acbe6b26f61e931a57b95a	refs/heads/main
4356450d737b81cb929c9f65e57d37b53a02ee0f	refs/tags/v1.0-for-review
0e765ae8f7611c3385183f064f3c66ab09b25740	refs/tags/v1.0-for-review^{}

$ git rev-parse HEAD v1.0-for-review^{commit}
027daf2b74962f3dd0acbe6b26f61e931a57b95a
0e765ae8f7611c3385183f064f3c66ab09b25740

$ gh repo view dudailia/baf-threshold-drift --json url,visibility,defaultBranchRef
{"defaultBranchRef":{"name":"main"},"url":"https://github.com/dudailia/baf-threshold-drift","visibility":"PUBLIC"}
```

Fresh clone into a new temporary directory, new venv from requirements.txt, `make test`:

```
$ D=$(mktemp -d <scratchpad>/clone.XXXXXX); git clone https://github.com/dudailia/baf-threshold-drift.git "$D/r" 2>&1; echo "exit=$?"
Cloning into '<clone>/r'...
exit=0

$ git -C "$D/r" log --oneline -1; git -C "$D/r" tag; ls "$D/r/data" 2>&1
027daf2 Resolve the five suspicious leakage items; narrowed pre-registration check; check outreach drafts
v1.0-for-review
ls: <clone>/r/data: No such file or directory

$ cd "$D/r" && make setup > ../setup.log 2>&1; echo "exit=$?"; tail -1 ../setup.log
exit=0
[notice] To update, run: <clone>/r/.venv/bin/python3 -m pip install --upgrade pip

$ cd "$D/r" && make test; echo "exit=$?"
.venv/bin/python -m pytest -q
........................................................................ [ 65%]
......................................                                   [100%]
110 passed in 86.76s (0:01:26)
exit=0

$ cd "$D/r" && git status --short; echo "exit=$?"
exit=0
```

Verdict: PASS. The repository is public at https://github.com/dudailia/baf-threshold-drift, with `main` (027daf2) and tag v1.0-for-review (still on 0e765ae). The clone has no data/ folder and passes all 110 tests. `[repo link]` is replaced with that URL in the final texts of reports/outreach_drafts.md. The commit that adds this section and the URL is pushed after it; its hash is in `git log origin/main`.

