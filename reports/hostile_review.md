# Hostile review: threshold drift on BAF

Reviewer stance: Feedzai research scientist, read before agreeing to a call. Files read: README.md, REVIEWING.md, reports/one_pager.md, RESULTS.md, src/ and src/posthoc/. Nothing else was opened and nothing was run.

## 1. Ten questions for the call

1. The label-free strategies set each month's threshold from that whole month's scores (src/fastboot.py:158-161, and group-wise label-free at 175-177). An account-opening decision is made when the application arrives, before the month's top 5% is known. Would you rerun label-free with the previous month's score quantile? Why: this same-month information is the one advantage the winning strategy has over static and delayed-label, and delayed-label lag 1 swings from -2.09 to +1.24 points (RESULTS.md section 2) on exactly the month-to-month shift that a lagged quantile would also face.
2. `velocity_4w` has a PSI of 0.58 to 2.44 against its own pooled training months and 3.35 to 5.09 later (RESULTS.md section 1, PSI table). Did you drop `velocity_6h`, `velocity_24h` and `velocity_4w` together and rerun the static miss? Why: with `month` removed (src/preprocess.py:13-15) these act as a clock, trees clamp values beyond the training range, and that alone could produce the miss and its sign flip across splits.
3. Static realized FPR in Base is 5.08, 3.08, 4.02, 2.99 for months 4 to 7 (RESULTS.md section 3). Is this drift at all, or are months 5 and 7 simply months where negatives score low? Why: the series is not monotone, and `credit_risk_score` PSI jumps between months 2 and 3 in every variant (Base: 0.017 to 0.287), which looks like a generator boundary at month 3, the month you chose for validation.
4. The shuffled-label check and the 20 repeat shuffles use the first sampled configuration (src/checks.py:102, src/diagnostics.py:43), not the tuned one. What are that configuration's `min_data_in_leaf` and `n_estimators`, and what does the check give with the tuned configuration? Why: the check as run says nothing about the model behind the results.
5. src/checks.py:101 permutes labels across months 0 to 2 pooled; RESULTS.md section 1 says "shuffled within months 0 to 2". Which one ran? Why: the two nulls differ when monthly prevalence differs.
6. src/config.py:25-26 and src/checks.py:170 make a fired tripwire exit non-zero, and the comment says only the synthetic fixture turns that off. How did `make all` finish and reproduce every file (REVIEWING.md section 4) after the shuffled tripwire fired? Why: either the real run set the fixture flag or the Makefile ignores the failure.
7. Variants III, IV and V have PSI values equal to three or four decimals (for example `credit_risk_score` month 0: 0.0299, 0.0298, 0.0298), and Base, I and II are close to each other. How many independent draws does "18 of 18 intervals below zero" contain? Why: it looks like two draws times three months.
8. The headline quotes seed 0 intervals 0.23 to 0.32 points wide, yet changing the validation month flips the sign (RESULTS.md amendment). Why headline an interval that conditions on the one split, when the split is the dominant source of uncertainty?
9. The FPR ratio comparisons across strategies (one-pager Finding 3, RESULTS.md sections 5 and 6) are made at different realized FPRs. Did you compare at matched realized FPR? Why: the ratio moves with the operating point, so "differs" verdicts on the ratio partly restate the budget miss.
10. Delayed-label lag 1 assumes month m-1 labels are complete at the start of month m (src/fastboot.py:162-166). What label maturity did you assume? Why: real account-opening fraud labels arrive over months, so lag 1 is optimistic.

## 2. The three claims I trust least

"set on month 3 it under-spends by 0.87 to 2.32 points of FPR (seed 0 95% intervals 0.23 to 0.32 points wide)" (README.md, line 2; one-pager Finding 1). The intervals resample applications given one model, one split and one tuning run. The sign reverses on another split, the monthly series is not monotone, and the six variants are about two independent draws. The narrow interval gives a precision the finding does not have.

"re-targeting to the validation month's alert rate stays within 0.5 points of 5% in 22 of 24 variant-months" (README.md, paragraph 2; RESULTS.md section 2). It uses the full current month's scores (look-ahead in a real-time setting), it is arithmetic when prevalence and TPR hold still (the one-pager says so), and it fails exactly where prevalence moves (Variant V months 6 and 7, +0.60 and +0.70). The provenance of the 0.5 point tolerance is not in the files I was given.

"The diagnostics found no leak" (RESULTS.md section 1; one-pager Limits: "no leak was found"). The diagnostics are a univariate AUC screen, which cannot see a multivariate leak, a unit test I could not see, and shuffles run on a configuration that is not the main model. The "wrong null" explanation (atypical frauds) was not tested: no one checked whether the high-TPR shuffles score by density. Absence of evidence is presented close to evidence of absence.

## 3. Leakage, look-ahead and unfair comparisons

Same-month look-ahead for label-free (src/fastboot.py:158-161, 175-177). Confident it is information unavailable at decision time unless decisions are batched at month end, which is not how account opening works. To settle it, rerun with the month m-1 score quantile and compare budget miss against static.

Delayed-label label maturity (src/fastboot.py:162-166). Confident it is optimistic for delayed-label. It does not change the ranking, since delayed-label already loses, but it inflates delayed-label's case.

Model selection and threshold on the same month (src/train.py:65-83 selects by TPR at 5% FPR on month 3; src/fastboot.py:156-157 sets static there). Seed 0 is the selected fit (src/train.py:74) and carries every bootstrap interval. Suspicious only: the effect is probably small and hits static and validation-rate equally, but not label-free top 5%. To settle it, compare seed 0 intervals with seeds 1 to 4.

Shuffled check not run on the main model (src/checks.py:101-102; src/diagnostics.py:43). Confident it is a gap in the check, not a leak. To settle it, rerun 20 shuffles with each variant's tuned configuration.

Test-month selection in the one-pager. The 5.75% fixed rule is the best of five chosen on the test months (src/posthoc/values.py:266). It is disclosed, but it sits in a headline finding. The "9 of 12" valmonth count is on seed means, not intervals (src/posthoc/values.py:247-248).

Counting identical cells as evidence (src/values.py:54-59). The "inconclusive in 15" for delayed-label lag 1 includes six month-4 cells that equal static by construction. Confident; the real denominator is 18.

Weak traceability check (src/trace.py:74-85, 136-139). A number passes if it matches any value in any results CSV, times 1 or 100, at the precision shown. With 21,384 interval rows in ci.csv alone, almost any two-decimal number passes. Confident the checker proves less than "every number traces" implies; the templates that would prove correspondence were not given.

Single-feature mechanism test (src/posthoc/mechanism.py:62-67). It replaces one feature at a time with marginal draws from month 3, which breaks dependence between features and cannot detect a joint effect of the velocity family. The one-pager claim "no single feature among the ten most important explains the static miss" is true but weak.

Minor bug: src/posthoc/fixedq.py:36 reads `ROOT/results_posthoc` even when `BAF_POSTHOC_OUT` is set, so a test run can read real results.

## 4. First hour with code and data

1. From the saved predictions, run label-free with the previous month's quantile and with the previous month's alert rate; compare budget miss to the current table.
2. For each test month, compute the share of rows with any velocity feature beyond the training-month maximum; retrain the main split and split A without the three velocity features and recompute static miss.
3. Read the Makefile for tripwire handling, then rerun the shuffled check with the tuned configuration.
4. Measure overlap between variant files (identical feature tuples, per-month score correlation for the same model) to fix the effective number of replications.
5. Recompute the FPR ratio at matched realized FPR across strategies.
6. Insert a deliberately wrong number into RESULTS.md and run `make check`.

## 5. What I could not resolve

Whether the 0.5 point tolerance, the half-overlap verdict rule and the allowance for current-month scores were declared before results (PROTOCOL.md, not given). The unit test said to confirm preprocessing uses training months only (tests/). The Makefile's handling of fatal tripwires. How RESULTS_POSTHOC.md sections 2 and 8 phrase the replacement and valmonth results. The synthetic mechanism study (reports/mechanism.md). What the "separate agent" in the independent check saw and did not see. Monthly fraud rates and the month 3 profile (reports/data_audit.md). The pre-registration timing (git history). Whether the 20-configuration search and the 2,000-tree cap matter against the paper's search (reports/deviations.md). The figures.

## 6. Resolution from the repository (added by the coordinating session, 2026-10-18)

The reviewer saw only five sources. Each concern was then checked against the whole repository, the results files and, where needed, the data. Nothing in results/ or results_posthoc/ changed. Every question missing from prep/call_questions.md was added there, under "Added after the cold read", with what a strong answer needs.

| Concern | Status | Evidence |
|---|---|---|
| Q1 label-free uses the whole current month's scores | confirmed, by design; deployable variant not run | Declared before data (PROTOCOL.md, Thresholds). Static and delayed-label lack this information, so the comparison favours label-free. A previous-month or running quantile was not run. |
| Q2 velocity features as a clock | open | Single-feature replacement only (RESULTS_POSTHOC.md section 2). Joint replacement or dropping the three velocity features was not run. |
| Q3 non-monotone series, month 3 as a generator boundary | partly resolved | Post hoc, with the model fixed, the sign depends on the threshold month in 9 of 18 cells (RESULTS_POSTHOC.md section 8), so month 3 is not the only month with this behaviour. Whether the generator has a boundary at month 3 is open. |
| Q4 shuffled check on the first sampled configuration | confirmed, as declared | PROTOCOL.md, Implementation decisions. A check with each tuned configuration was not run. |
| Q5 pooled or within-month permutation | resolved | src/checks.py permutes the pooled rows of months 0 to 2. RESULTS.md now says "permuted across the pooled rows of months 0 to 2" instead of "shuffled within months 0 to 2". |
| Q6 how `make all` finished | resolved | The Makefile prefixes the shuffled check with `-`, with a comment citing the user's decision; the fired state is in results/tripwires.json. |
| Q7 effective number of replications | partly resolved | The shared base and the two fraud-rate profiles are disclosed (one-pager, reports/data_audit.md). The effective number of independent replications was not measured. |
| Q8 headline intervals conditioned on one split | resolved in the documents | The one-pager and the RESULTS.md amendment say that the direction depends on the validation month. |
| Q9 FPR ratio at matched FPR | open | Not computed. |
| Q10 label maturity for delayed-label | confirmed limitation, open | Not modelled; lags 2 and 3 also assume complete labels. |
| Least-trusted claim 2, origin of the 0.5-point band | confirmed | The band first appears at the write-up (commit 125042c), after results; PROTOCOL.md does not declare it. Only the user's predictions 3 and 8 used 0.5 points earlier. Added as a call question. |
| Least-trusted claim 3, "no leak was found" | strengthened, not settled | The fresh code review (reports/code_review.md) found no path from non-training months into any fit, and in this session 0 rows were found identical across any two months in any variant. The "wrong null" explanation stays untested, as the documents already say. |
| Tuning and static threshold share month 3; seed 0 is the selected trial | checked | Seed 0's static miss in months 5 to 7 ranks between 1 and 4 of 5 seeds across the 18 variant-months (results/metrics.csv), so it is not at an extreme. |
| 5.75% rule chosen on test months | resolved in the documents | The one-pager says "chosen after seeing these test months". |
| "inconclusive in 15" includes identical cells | confirmed, fixed in prose | All six month 4 cells are identical by construction. RESULTS.md now says so next to the count; the count is unchanged. |
| Weak traceability check | partly wrong | Rendering refuses any number typed into a template unless it is a declared text constant in the results manifests (src/trace.py, `render_text`), and result numbers are written from named keys. `make check` alone is weak, as the reviewer says. |
| Single-feature mechanism test | confirmed limitation | As Q2. |
| src/posthoc/fixedq.py fixed path | confirmed, fixed | Reads from `OUT` now; the default is the same folder, so no number changes. |

Concerns that cannot be resolved from the repository without new analysis: Q1 (lagged label-free quantile), Q2 (joint velocity features), Q3 (generator boundary at month 3), Q4 (shuffles with the tuned configurations and with a within-month permutation), Q7 (effective number of replications), Q9 (FPR ratio at matched FPR), Q10 (partial labels), and the untested "wrong null" explanation for the shuffled-label failure.
