# Deviations from the brief and from the paper

Every point where this study departs from the original brief or from the paper's protocol (Jesus et al. 2022, arXiv 2211.13358, and the repository's notebooks), with the reason and the commit where it was made or recorded. Choices made without the user are also in reports/decisions.md.

## Protocol

| # | Brief or paper | What was done | Reason | Commit |
|---|---|---|---|---|
| 1 | Paper: train months 0 to 5, test months 6 and 7, no validation month. | Train months 0 to 2, validate on month 3, test months 4 to 7. The paper's split is used only for the replication check. | The brief required at least four test months; the user approved this split. It trains on about 3/8 of the rows instead of 6/8, so absolute TPR is lower than the paper's. | 6afb14a |
| 2 | Paper and notebook: the 5% FPR threshold is set on the pooled test labels of months 6 and 7. | The static threshold is set on validation month 3; the paper's rule appears here as the oracle (per test month), labelled an upper bound. | The research question is about a threshold set before deployment. | a2b9b31 |
| 3 | Paper's code: `month` is a model feature. | `month` is excluded in the main study; the replication was run with and without it. | Test months never appear in training, so a tree cannot use `month` meaningfully (user decision). | 6afb14a |
| 4 | Paper text: older group is age > 50. | Older group is `customer_age >= 50`; `> 50` is a pre-declared sensitivity analysis. | The evaluation notebook and the datasheet (answer A17) use >= 50, and the audit found >= 50 matches Table 1's group sizes (1.24 points against 30.66). | 6afb14a, 11f2b3d |
| 5 | Paper: 100 random LightGBM configurations, `n_estimators` up to 10,000, no seed variation. | 20 configurations, `n_estimators` capped at 2,000, `feature_fraction` 0.8 and bagging fixed so that 5 seeds differ. | Compute budget; seeds would otherwise not change the model. This changes the model family relative to the paper's. | a2b9b31 |
| 6 | Notebook threshold rule: ROC point with FPR strictly below 5%, flag `score > t`. | Main study flags `score >= t`, the largest set with FPR at most 5%, ties never split. The notebook's rule is used only in the replication. | One rule for every strategy. Placing thresholds at the lowest flagged score instead changes 217 of 1,200 static and delayed-label rows in the third decimal. | a2b9b31 |
| 7 | Paper: sentinel values left as they are. | Documented sentinels converted to missing (LightGBM native handling; logistic regression uses train medians and missing indicators). Raw values kept in the replication. | Datasheet answer A7 documents them as missing. | a2b9b31 |
| 8 | Brief: check baseline TPR against the paper's reported numbers. | The paper reports no numeric TPR for these models (Figure 1 only, notebook has no outputs), so the check uses by-eye readings of Figure 1 as a loose bound of plus or minus 0.05, not pass/fail. | No numbers exist to match. | 6afb14a |
| 9 | Brief: label-free = top 5% of each month's scores, or the quantile matching the validation alert rate. | Top 5% is the primary label-free strategy; the validation alert rate is a secondary strategy. | User decision. | a2b9b31 |
| 10 | Brief: compare strategies on FPR, TPR, alert volume, FPR ratio and precision. | Budget miss (realized FPR minus 5%) became the primary comparison; TPR is always shown with realized FPR. | User decision: all strategies sit on the same month's ROC curve, so overspending buys TPR. | d333b4e |
| 11 | Brief: delayed-label with the previous month's labels. | Lags 1, 2 and 3; cells whose source month is a training month are reported as not available. | User decision; lags 2 and 3 are pre-declared secondary analyses. | a2b9b31, 6c47f4c |
| 12 | Brief: 5 seeds per model and variant. | Logistic regression gives identical scores for every seed, so its seed spread is 0 and its bootstrap is computed once. | Deterministic solver; checked, not assumed. | c370195 |
| 13 | Brief: 1,000 bootstrap resamples. | 1,000 paired resamples per month for the 5% target; intervals reported for seed 0; exploratory targets have point estimates and seed spread only. | Compute; declared before data. | c370195 |
| 14 | Brief: four strategies. | Added group-wise static and group-wise label-free (exploratory diagnostics that use age) and FPR targets of 1%, 2% and 10% (exploratory). | Pre-declared secondary analyses. | 6c47f4c, 30f88f9 |
| 15 | Brief: run the 10% sample and show the outputs before scaling. | The sample ran inside an unattended pass; its outputs were logged (reports/progress.md) and not interpreted, with no stop for review. | User instruction for the unattended pass. | f39b485 |

## Checks

| # | What was declared | What happened | Commit |
|---|---|---|---|
| 16 | Shuffled-label check: pooled TPR at 5% FPR must be within 0.05 plus or minus 0.02. | FAILED: 0.1172. The tripwire fired and the criterion was not redefined (user decision). Post hoc diagnostics (20 shuffles, leak audit, train-only test) found no leak; the median shuffle (0.0589) was inside the tolerance and the failing run was the maximum, so the cause is not established. It stays a caveat on every result. | 6d0ce24, 3fa2ccf |
| 17 | Replication within the loose Figure 1 bound. | Passed (top-5 mean TPR 0.552 with `month`). It selects the top 5 configurations by test TPR, as Figure 1 does, which is selection on the test set. | 6d0ce24 |

## Post hoc additions (declared after main results were seen)

| # | Addition | Result in one line | Commits |
|---|---|---|---|
| 18 | Rolling-origin splits (train 0-1/validate 2; train 0-3/validate 4). | Static over-spends when set on month 2 and under-spends when set on month 4. | 25e8629, cd843c6, bb31c6b |
| 19 | Mechanism: threshold quantiles, KS, single-feature replacement. | No single feature among the ten most important explains the static miss. | 25e8629, f563cdd, 50cef9e |
| 20 | Hyperparameter sensitivity (four other top-5 trials, one regularised model). | Sign of the static miss in months 5 to 7 unchanged in 90 of 90 cells. | f563cdd, f6ed963 |
| 21 | Retraining on months 0 to t-2 with a month t-1 threshold. | No better budget control; higher TPR mostly at higher realized FPR. | f563cdd, e5935e1 |
| 22 | Isotonic estimated-FPR targeting. | Within 0.5 points in 24 of 24 variant-months. | f563cdd, 89a7e0c |
| 23 | Validation month with the model held fixed. | The sign of the static miss still depends on the threshold month. | 97e059a, 666150a |
| 24 | Fixed top-q label-free rules as a control for isotonic targeting. | A fixed top 5.75% rule is also within 0.5 points in 24 of 24; most of the isotonic result is the FPR identity. | 97e059a, 666150a |
| 25 | Synthetic mechanism study, related-work review, call prep, independent recomputation checks, two claims audits, hygiene and reproducibility checks. | Not in the brief; added on the user's later instructions. | 13e37ad, cdf1317, 471c3c0, 4d640ce, 31d8e3d, de62d43, 60a0962, 10627b9, ddf647b, 9817602 |

## Corrections to published text

| # | Original | Correction | Commits |
|---|---|---|---|
| 26 | README, one-pager and RESULTS.md said the static threshold "under-spends" in months 5 to 7. | Amendment 2026-10-17: the direction depends on the validation month. The original wording is quoted in the amendment. | 994ac07, fd04d89 |
| 27 | RESULTS.md said `credit_risk_score` "drifts most in every variant", consistent with the static misses. | First correction said it had the largest PSI in every variant and that replacing it "does not reduce" the miss; both were wrong. Final text: `velocity_4w` is the largest among the ten features in psi.csv in four variants, `credit_risk_score` in two, and replacing either leaves most of the miss in place. | 994ac07, de62d43, 60a0962 |
| 28 | Other prose found unsupported by two independent claims audits (rounded bounds stated as "at most", causal wording, retraining and calibration claims, scope). | Reworded without changing numbers. | de62d43, 60a0962 |

## Changes to code or plan after main results

| # | Change | Effect | Commit |
|---|---|---|---|
| 29 | Evaluator: a delayed-label source month must be among the evaluated months (needed for non-consecutive month pairs). | None on main results: the clean rebuild reproduced every result file exactly. | 4aa5b8f, ddf647b |
| 30 | `make clean` keeps results/independent_check.csv and results_posthoc/. | They are not produced by `make all`; the post hoc results were not rerun after the clean rebuild. | 9398c8c |
| 31 | After the clean rebuild, three files that differed only in a timestamp, a key order and fit times were restored to their committed versions. | No number changed; differences recorded in reports/reproducibility.md. | ddf647b |
| 32 | Main documents render from results/ and results_posthoc/ together. | Lets the amendment's post hoc numbers be traced; main-only numbers come from results/. | 994ac07 |
| 33 | Checker scripts' absolute paths replaced by repo-relative paths. | Scripts otherwise verbatim; earlier commits still hold the absolute paths (history not rewritten). | ebd72dc |
