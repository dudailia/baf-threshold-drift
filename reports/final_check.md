# Final check

Run on 2026-10-19 against commit d942846 (working tree clean at the start). Every block below is the command as typed and its raw output, captured to a file and pasted unchanged, with two substitutions so this file does not put the username back into the repository: the absolute repository path is shown as `<repo>/`, and the file owner in `ls -l` is shown as `<user>`. The two searches whose pattern contained the username were run with `$USER` in its place. Choices made during this check are in reports/decisions.md (rows starting "final").

| Item | Verdict |
|---|---|
| 1 Reviews | PASS |
| 2 Tests and traces | PASS |
| 3 Pre-registration | FAIL |
| 4 Data and privacy | PASS |
| 5 Outreach numbers | FAIL |
| 6 Visual check | PASS |
| 7 Publish | NOT RUN (items 3 and 5 failed) |

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
- In the one-pager, "TPR" appears three times: in the question, in the formula, and as the shuffled-label value "pooled TPR 0.117 at 5% FPR". That last value is the TPR at a threshold set on the same months' own labels at 5% FPR (src/checks.py:111-113, column `oracle_tpr_at_5pct_fpr`), so 5% is the FPR it was read at.

The PDF was not rebuilt, because reports/one_pager.md, the PDF and figures/ are unchanged since 1306af0 (the visual check), when the PDF was last built from that text.

## 7. Publish

Not run, because items 3 and 5 failed. Nothing was created on GitHub, no remote was added and nothing was pushed. `gh auth status` was run read-only so that the instructions below are correct. It reports a login to github.com as account dudailia, protocol https, with the `repo` scope. The repository's branch is `main`; there is no `master` branch.
