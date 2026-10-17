# Protocol

This file separates what the BAF paper and repository state from what this study chooses. Each item is marked:

- confirmed (location): the paper, datasheet or repo says this, at the location given.
- corrected (location): a claim in the brief differs from the source; the source's version is given.
- my choice (reason): not specified by the sources, or deliberately changed for this study.

## Sources read

| Source | Version used | Notes |
|---|---|---|
| Paper, arXiv 2211.13358 | v2 PDF (created 2022-11-28) and its LaTeX source from arxiv.org/e-print | Page numbers below are PDF pages of this file (19 pages). |
| Paper copy in repo, `documents/BAF_paper.pdf` | repo commit 3377cfd (2023-12-21) | Same page numbering as arXiv v2. A diff of pages 6 and 7 shows only line-wrapping differences. |
| Datasheet, `documents/datasheet.pdf` | repo commit 3377cfd | Cited as "Datasheet, A<n>, p<n>". |
| Empirical results notebook, `notebooks/empirical_results.ipynb` | repo commit 3377cfd | Cited as "notebook, cell <n>" (0-indexed). The notebook has no saved outputs, so it contains no result numbers. |
| Variant generation notebook, `notebooks/generate_dataset_variants.ipynb`, and `notebooks/mvn.py` | repo commit 3377cfd | Cited as "variants notebook, cell <n>". |

There was no `paper.pdf` in the project folder when this file was written. The checks were made against the arXiv v2 PDF and the repo copy listed above. If you have a different PDF in mind, put it at `paper.pdf` and the page references will be re-checked against it.

Two caveats about the repo notebooks. First, they do not run as written: the variants notebook refers to names that are never defined (`final_dfs`, `big_sample_df`, `minority_positive`), and the empirical notebook uses `deepcopy` without importing it. They show the intended procedure but are not guaranteed to be the exact code that produced the paper's figure. Second, `empirical_results.ipynb` has no saved outputs.

## Verification of the research brief's claims

| # | Claim in the brief | Status | Evidence |
|---|---|---|---|
| 1 | 8 monthly periods; first 6 months train, last 2 test | confirmed (Sec 3.1 p4; Sec 3.2 p6; Sec 4 p8; notebook cell 8) | Sec 3.1: "The dataset comprises eight months of information ranging from February to September." Sec 3.2, Splitting Strategy: "we were able to split the data temporally: the first six months for training, the last two for testing." Notebook cell 8: `df["month"]<6` for train, `df["month"]>=6` for test. Datasheet A7 p3: month "Ranges between [0, 7]". Small inconsistency: Datasheet A11 p4 calls the last two months "validation", the paper calls them "testing". |
| 2 | No validation month defined; validation sets or sliding windows suggested instead | confirmed (Sec 5 p9) | Sec 5: "In this study, we limited our analysis to the original data split, i.e. training models with the initial 6 months of data, and testing on the remainder. These, however, can and should be adapted to other scenarios [...] e.g., having part of the data for validation of the hyperparameters or threshold definition, or having a sliding window approach to train and validate models." A validation month in this study is therefore my choice (see below). |
| 3 | Headline metric TPR at 5% FPR | confirmed (Sec 3.2 p6; Sec 4 p8) | Sec 3.2, Performance Metric: "we select the threshold in order to obtain 5% false positive rate (FPR), and measure the true positive rate (TPR) at that point." |
| 4 | Predictive equality, lowest group FPR over highest group FPR, 1 is best | confirmed (Sec 3.2 p6; notebook cell 13) | Sec 3.2, Fairness Metric: "we measure the ratio between FPRs, i.e., predictive equality [...] The ratio is calculated by dividing the FPR of the group with lowest observed FPR with the FPR of the group with the highest FPR." Notebook cell 13 computes min/max. So the ratio lies in [0, 1] and 1 means equal FPRs. "1 is best" is implied by the definition, not stated in those words. |
| 5 | Age binarized at 50, over 50 vs 50 or under | corrected: the sources disagree (Sec 3.2 p6; notebook cell 10; Datasheet A17 p5; variants notebook cell 7) | Paper Sec 3.2: "separating applicants with age >50 in one group and ≤50 in the other group." Empirical notebook cell 10: `X_test["customer_age"]>=50` labelled "Older". Datasheet A17: "we binarize this feature based on a threshold (< 50, ≥ 50)". Variants notebook cell 7 builds the sampling groups with `customer_age > 50`. Because `customer_age` is rounded to the decade (Datasheet A7 p2), ">50" means 60 and over while ">=50" means 50 and over. These are different groups. The data audit will report the group sizes and prevalences under both definitions and compare them with Table 1. |
| 5b | Group sizes and prevalence by group | confirmed (Table 1 p7; Sec 5 p9; Datasheet A17 p5) | Table 1, Base: majority 77% at 0.9% prevalence, minority 23% at 1.8%. Original data: 80% at 1%, 20% at 2%. Sec 5: "approximately an 80/20 split" and prevalence "approximately 2 times larger for the older group". Table 1 also lists "Global ... 1.8%", which does not match the Base group values (77% x 0.9% + 23% x 1.8% is about 1.1%). The audit will measure it. |
| 6 | Variant definitions | confirmed with one discrepancy (Sec 3.4 and Table 1 p7; variants notebook cells 10 to 19) | See the variants table below. Variant IV: Table 1 gives 50/50 group sizes but variants notebook cell 17 sets `majority_size = 0.9`. The audit will measure which one the released file follows. |
| 7 | 100 LightGBM models with random hyperparameters per dataset, fairness-blind; exact TPR and fairness ratio for Base | partly confirmed, partly corrected (Sec 4 p8; App A.2 p15; notebook cells 10 to 16) | Sec 4: "we sampled 100 hyperparameter configurations of LightGBM [...] and trained them on each dataset", and the analysis is limited to "fairness-blind models". Correction: the paper reports no exact numbers for these models. They appear only as a scatter plot (Figure 1, p8), and the notebook has no saved outputs. Reading Figure 1 by eye (approximate, not a reported value): the top 5 Base models sit near TPR 0.55 and FPR ratio 0.32 to 0.33, and the Base cloud spans roughly TPR 0.47 to 0.56. Other variants by eye: I near 0.53 / 0.65, II near 0.55 / 0.32, III near 0.76 / 0.35, IV near 0.42 to 0.44 / 0.33, V near 0.34 to 0.37 / 0.37. These visual readings are the only available sanity target. They are used as a loose bound of about plus or minus 0.05, not as a pass/fail check (my choice, agreed with the user). |
| 8 | Base top models near 0.3 FPR ratio | confirmed (Sec 4 p8) | Sec 4: "the base dataset alone provides a demanding fairness challenge, with the top performing models lying around 0.3 FPR ratio." |

### Variants (Sec 3.4 and Table 1, p7; variants notebook)

| Variant | Paper description | Table 1 group size (maj / min) | Table 1 prevalence (maj / min) | Code (variants notebook) |
|---|---|---|---|---|
| Base | sampled to the original month frequency and monthly prevalence, no injected bias | 77% / 23% | 0.9% / 1.8% | cells 3 to 6 |
| I | group size disparity aggravated, no prevalence disparity | 90% / 10% | 1.1% / 1.1% | cell 10: majority 0.9, disparity 1 |
| II | prevalence disparity, "one group has five times the fraud rate of the other", equal group sizes | 50% / 50% | 0.4% / 1.9% | cell 12: majority 0.5, disparity 5 |
| III | separability disparity: the task is easier for the majority group through two appended features | 50% / 50% | 1.1% / 1.1% | cells 15, 16: `TypeIIIBiasSampler(..., 0.9, 0.05, ...)`, appended columns named `x1`, `x2` (`mvn.py` line 29) |
| IV | prevalence disparity like II in the first six months, none in the last two | 50% / 50% | 0.3% / 1.7% in train, 1.5% / 1.5% in test | cell 17: `majority_size = 0.9`, disparity `[5,5,5,5,5,5,1,1]` (group size disagrees with Table 1) |
| V | separability disparity in the first six months, removed in the last two; balanced sizes and prevalence | 50% / 50% | 1.1% / 1.1% | cells 18, 19: separability `[0.9]*6 + [0.05]*2` |

Variants IV and V carry their injected bias in months 0 to 5 only and lose it after month 5 (Sec 3.4 p7: Variant IV "features prevalence disparities over the first six months, but no disparity for the remainder"; Variant V: "we add a separability bias component on the first six months, and remove it on the remainder"; variants notebook cells 17 and 19). The shift at month 6 is therefore a removal of bias, not the arrival of a new one. In Variant IV the group prevalences become equal; in Variant V the appended features stop separating the majority group's fraud. Any split must keep months 6 and 7 in the test period so that this shift is observed.

## Answers to the brief's questions

Protected, dropped and missing-coded columns.
The protected attributes named are `customer_age`, `income` and `employment_status` (Sec 3.2 p6). The paper studies age only. Nothing is dropped in the baseline except the label: notebook cell 10 builds `X_train = train_dfs[...].drop(columns=["fraud_bool"])`, so `customer_age` and `month` are both model inputs. Categorical columns are label-encoded with an encoder fit on the training months (notebook cells 7 and 9): `payment_type`, `employment_status`, `housing_status`, `source`, `device_os`. Negative sentinels, per Datasheet A7 (p2 and p3): `prev_address_months_count` (-1 is missing), `current_address_months_count` (-1), `intended_balcon_amount` (negatives are missing), `bank_months_count` (-1), `session_length_in_minutes` (-1), `device_distinct_emails` (-1; the column is `device_distinct_emails_8w` in the config file `notebooks/config-rs.yml`). `velocity_6h` and `credit_risk_score` have negative ranges in A7 but are not described as missing. Datasheet A9 (p4) says "There is no missing information from individual instances", which conflicts with the sentinels in A7. The label column is `fraud_bool` (Datasheet A8 p3, notebook cell 7). The paper text says `"is_fraud"` (Sec 3.1 p4), which does not match the data files.

Is `month` a feature in their baseline?
Yes, implicitly. Notebook cell 10 drops only `fraud_bool`, so `month` is passed to LightGBM. The paper text does not mention it either way.

How is the 5% FPR threshold set, and on which data?
On the test set itself, using the test labels, pooled over months 6 and 7. Notebook cell 10: `fprs, tprs, thresholds = metrics.roc_curve(y_test, predictions)`, then `threshold = np.min(thresholds[fprs==max(fprs[fprs < 0.05])])`, and predictions are binarized as `predictions > threshold`. The paper's operating point is therefore what this study calls the oracle strategy, applied to the two test months pooled. Realized FPR is close to 5% by construction (the largest FPR on the ROC curve strictly below 0.05).

Do they report drift in realized FPR across test months?
No. Results are one aggregate over months 6 and 7 per model (Figure 1, p8; notebook cell 10). Because the threshold is fit on the same test labels, realized FPR cannot drift in their setup. The threshold-drift question is not answered in this paper. I have not surveyed later work that uses BAF, so I can only say it is not addressed in this paper and repo, not that nobody has studied it.

What do the Limitations section and checklist say that this study could address?
Sec 5 (p9) asks for other splits, "having part of the data for validation of the hyperparameters or threshold definition, or having a sliding window approach", and says the age threshold of 50 "is not intended to be mandatory". Setting the threshold on a validation month and measuring how it holds up later responds directly to the first point. The checklist (p14, item 3c) states: "We do not experiment by varying random seeds in the process", and no error bars are reported. Five seeds and bootstrap intervals address that. The paper has no separate Broader Impact section; the checklist points to Sec 5 for negative societal impacts. Sec 3.1 (p4) notes that a positive prediction leads to rejection of the application, which is why FPR by age group is the relevant fairness quantity here.

## Protocol for this study

### Splits

| Item | Status | Decision |
|---|---|---|
| Paper's split (train 0 to 5, test 6 to 7) | confirmed (Sec 3.2 p6) | Used only for the replication sanity check against Figure 1. It leaves 2 test months, fewer than the 4 the brief requires. |
| Main split: train months 0, 1, 2; validation month 3; test months 4, 5, 6, 7 | my choice (approved by the user) | One validation month and four test months, as the brief requires. Months 6 and 7 stay in test, so the Variant IV and V bias removal at month 6 falls inside the test period, with months 4 and 5 as test months while the bias is still present. Cost: about 3/8 of the rows for training instead of 6/8, so absolute TPR will be lower than the paper's. The audit will report row and fraud counts per month to confirm there is enough data. |
| Model trained on months 0 to 2 only, not refit on month 3 after tuning | my choice | The static threshold is set on month 3 scores. Those scores must come from a model that never saw month 3. |
| Rows in more than one split | my choice (check) | Splits are disjoint by month by construction. The audit also hashes all columns and counts exact duplicate rows across splits, and reports the count. |

### Features and preprocessing

| Item | Status | Decision |
|---|---|---|
| Label `fraud_bool` | confirmed (Datasheet A8 p3; notebook cell 7) | |
| Categorical columns | confirmed (notebook cell 7) | `payment_type`, `employment_status`, `housing_status`, `source`, `device_os`. Category lists are fit on training months. Categories unseen in training map to an "unknown" code. |
| `customer_age` as a feature | confirmed (notebook cell 10) | Kept as a feature, as in the paper's fairness-blind baseline. |
| `month` as a feature | confirmed that the paper's code uses it (notebook cell 10); exclusion in the main study is my choice (approved by the user) | Main study: excluded. With training months 0 to 2, every test month (4 to 7) lies outside the training range, so a tree can only treat it as "month 2 or later". That carries no transferable information. Replication run: run twice, once with `month` (to match the paper's code) and once without, so the effect is measured. |
| Appended `x1`, `x2` in Variants III and V | confirmed (`mvn.py` line 29) | Used as features if present in the released files, since they are the injected bias. The audit lists the columns of each file. |
| Missing-value sentinels | confirmed (Datasheet A7 p2, p3) | Converted to NaN: -1 in `prev_address_months_count`, `current_address_months_count`, `bank_months_count`, `session_length_in_minutes`, `device_distinct_emails_8w`; any negative value in `intended_balcon_amount`. |
| Sentinel handling for LightGBM | my choice | NaN handled natively by LightGBM. In the replication run the raw values are kept, to match the notebook. |
| Sentinel handling for logistic regression | my choice | One missing-indicator column per sentinel feature, NaN filled with the training-month median, then standard scaling fit on training months. Categoricals one-hot encoded with categories from training months. |
| `velocity_6h` and `credit_risk_score` negatives | my choice | Kept as values, since the datasheet does not describe them as missing. The audit reports how many there are. |

### Models

| Item | Status | Decision |
|---|---|---|
| LightGBM, fairness-blind | confirmed (Sec 4 p8) | Primary model. |
| Hyperparameter space | confirmed (App A.2 p15; `lightgbm_hyperparameter_space.yaml`) | Same parameters and ranges, except `n_estimators`, which I cap at 2000 instead of 10000 (my choice, compute). |
| Tuning budget | my choice | 20 random configurations per variant (the paper used 100), selected by TPR at 5% FPR on the validation month, with the threshold set on validation scores. No early stopping, so the validation month is used once, for selection. |
| Seed variation | my choice | 5 seeds of the selected configuration. Plain GBDT without subsampling is deterministic, so seeds would change nothing. I fix `feature_fraction=0.8`, plus `bagging_fraction=0.8, bagging_freq=1` for GBDT (GOSS has its own sampling), so the seed actually changes the model. The paper did not vary seeds (checklist p14). |
| Logistic regression | my choice | Sanity baseline: L2, lbfgs, no class weighting. lbfgs on fixed data is deterministic, so the 5 seeds give identical models. I will run it 5 times anyway to show this and report a seed spread of 0 explicitly, rather than invent variation. |
| No resampling or class weights | confirmed for LightGBM (notebook cell 10 uses defaults) | Same for both models. |

### Thresholds

All thresholds use the rule "flag if score >= t". A threshold at FPR target f on a labelled month is the smallest t with FPR(t) <= f on that month's negatives. Ties are handled exactly; the unit tests cover them. This differs slightly from the notebook's `roc_curve` rule with `>` (my choice: one rule, applied the same way by every strategy). The replication run uses the notebook's rule.

| Strategy | Status | Definition |
|---|---|---|
| Static | my choice | t set at 5% FPR on validation month 3, never changed. |
| Label-free, top 5% (primary) | my choice, per your brief | Each test month, t is the score of the 95th percentile of that month's scores, so 5% of applications are flagged. Uses no labels. |
| Label-free, validation alert rate (secondary) | my choice, per your brief | Each test month, flag the same share of applications as the static threshold flagged on month 3. Uses no labels. |
| Delayed-label, lag k = 1, 2, 3 | my choice, per your brief | For test month m, t is set at 5% FPR on the labelled scores of month m - k. Only defined if m - k >= 3, because months 0 to 2 are training months and their scores are in-sample. Cells where m - k < 3 are reported as "not available", not filled with another strategy. Coverage: lag 1 for months 4 to 7; lag 2 for months 5 to 7; lag 3 for months 6 and 7. Note that lag 1 at month 4, lag 2 at month 5 and lag 3 at month 6 all use month 3 and so equal the static threshold by construction. Tables will mark these. |
| Oracle (upper bound, not deployable) | my choice | t set at 5% FPR on the test month's own labels. A pooled version over months 6 and 7 is computed for the replication check, since that is the paper's operating point. |

### Metrics recorded for every variant, model, seed, strategy and test month

| Metric | Status | Definition |
|---|---|---|
| Realized FPR vs the 5% target | my choice | FP / negatives in the month. |
| Budget miss | my choice (defined by the user) | Signed miss = realized FPR - 0.05; absolute miss = abs(realized FPR - 0.05). Reported per strategy, variant, model, seed and test month. Every strategy applies a threshold to the same model's scores on the same month, so every operating point lies on that month's ROC curve. A strategy's TPR is therefore fixed by its realized FPR, and a strategy that overshoots the budget can show higher TPR than the oracle. Budget miss is the primary comparison between strategies; TPR is secondary and only read together with realized FPR. |
| TPR at the applied threshold | confirmed as headline (Sec 3.2 p6) | TP / positives. |
| Alert volume | my choice | Share of applications flagged. |
| FPR per age group and FPR ratio (predictive equality) | confirmed (Sec 3.2 p6; notebook cell 13) | Ratio = min group FPR / max group FPR. |
| Protected group | corrected (see claim 5); choice of primary is my choice (approved by the user), final confirmation pending the audit | Primary: `customer_age >= 50` vs `< 50`, matching the evaluation code that produced Figure 1 (notebook cell 10) and the datasheet (A17). Sensitivity: `customer_age > 50` vs `<= 50`, matching the paper text and the variant sampling code. Both are reported for the headline FPR ratio table. The audit compares group sizes and prevalences under both definitions with Table 1 for each variant. If one definition matches clearly better, the user is told before any modelling, and the final choice is recorded in the Decision log below before the first model run. |
| Precision | my choice | TP / alerts. |
| Counts per month and age group | my choice, per your brief | Positives and negatives per cell. Cells with fewer than 30 positives are flagged, and their TPR is only shown with an interval. |
| Alert share vs application share by age group | my choice, per your brief | Under both label-free strategies: each group's share of all alerts, next to its share of applications. |

### Reporting rules

- TPR is never shown without the realized FPR of the same strategy, variant and month next to it.
- The oracle row is always shown, and always labelled "Oracle (upper bound, not deployable)".

### Figures

| File | Content |
|---|---|
| `figures/realized_fpr_by_month.png` | Realized FPR by test month per strategy, with the 5% target marked. |
| `figures/tpr_by_month.png` | TPR by test month per strategy, with realized FPR shown alongside. |
| `figures/fpr_ratio_by_month.png` | Age FPR ratio by test month per strategy. |
| `figures/roc_operating_points.png` | For each test month, the ROC curve of that month's scores, with each strategy's operating point marked. |

### Uncertainty

| Item | Status | Decision |
|---|---|---|
| Seed spread | my choice | Mean, standard deviation, min and max over 5 seeds of each point estimate. |
| Bootstrap | my choice, per your brief | 1,000 resamples of applications within a month. Each strategy's threshold is re-estimated inside each resample from resampled source data (validation month for static, month m - k for delayed-label, the resampled test month for label-free and oracle), so threshold estimation uncertainty is included. Reported per seed; tables show the reference seed (seed 0), and the full per-seed intervals go to the results CSV. |
| Seed spread and bootstrap kept separate | my choice, per your brief | Never combined into one interval. |
| Strategy comparisons | my choice | Paired bootstrap: same resampled rows for both strategies, interval of the difference. A difference is called inconclusive if that interval contains 0, or if the two marginal intervals overlap heavily. "Overlap heavily" means the overlap of the two marginal 95% intervals is at least 50% of the width of the shorter one (declared 2026-10-16, before any data). Otherwise the difference is reported as "differs". |

### Sanity checks

| Check | Status | Decision |
|---|---|---|
| Replication against Figure 1 | my choice | Paper split, raw sentinels, notebook threshold rule, pooled oracle threshold over months 6 and 7, run once with `month` and once without. Compared with the visual readings in claim 7 as a loose bound of about plus or minus 0.05, not a pass/fail check. I sample 20 configurations, not 100, so my best model may sit lower than the paper's top 5. A result outside the loose bound is investigated and reported to the user before going further. |
| Shuffled labels | my choice, per your brief | Labels permuted within training months only; the model must give TPR close to 5% at 5% FPR on test months. |
| Feature drift | my choice, per your brief | Population stability index for the top 10 LightGBM features by gain, per variant. Reference is the pooled training months; each month 0 to 7 is compared with it. Numeric bins are reference deciles (with NaN as its own bin); categoricals use their categories. |
| 10% sample run | my choice, per your brief | Stratified by month and label, Base only, end to end. Its numbers are pipeline checks and are not interpreted in any file. |

## Pre-declared secondary analyses

Declared on 2026-10-16, before any data file was opened and before any model was run. These are the only secondary analyses. Anything added after seeing results is marked "post hoc" wherever it appears.

| # | Analysis | Scope |
|---|---|---|
| (i) | Age group `> 50` versus `>= 50` | FPR per age group, FPR ratio and alert share versus application share, recomputed with the definition that is not primary, for every variant, strategy and test month. |
| (ii) | Logistic regression versus LightGBM | Every primary metric (budget miss, realized FPR, TPR, alert volume, precision, FPR ratio) for logistic regression, set against the same quantities for LightGBM. |
| (iii) | FPR targets of 1%, 2% and 10% in addition to 5% (exploratory) | Every strategy rerun at each target on the same scores. For target f, the label-free primary strategy flags the top f of each month's scores and the secondary one matches the validation alert rate at f. Budget miss is measured against f. Labelled "exploratory" wherever reported. |
| (iv) | Delayed-label lags 2 and 3 | Lag 1 is part of the primary comparison. Lags 2 and 3 are reported with cells marked "not available" where the source month is a training month. |
| (v) | Group-wise static thresholds (exploratory) | One threshold per age group, set on validation month 3 so that each group's FPR on that month is at most 5% by the rule in the Thresholds section, then held fixed. Added 2026-10-16 before any data was used. |
| (vi) | Group-wise label-free (exploratory) | Each test month, within each age group separately, flag the top 5% of that group's scores. Added 2026-10-16 before any data was used. |

Strategies (v) and (vi) use the protected attribute (age group, primary definition) at decision time. They are reported as diagnostics of where the FPR gap comes from, not as recommendations, and every table or sentence that shows them says so.

## Implementation decisions

Declared 2026-10-16, after the code was tested on synthetic data and before any real data file was opened.

| Item | Status | Decision |
|---|---|---|
| Tuning configurations | my choice | The same 20 configurations (sampled once, seed 2022) are tried on every variant; the one with the highest validation-month TPR at 5% FPR is kept (ties go to the earlier trial). |
| Replication statistic | my choice | The same 20 configurations, seed 0, trained on months 0 to 5 of Base. Compared with Figure 1 is the mean TPR of the 5 configurations with the highest test TPR, which is how Figure 1 highlights its top 5. Within the loose bound means within 0.05 of 0.55. The with-month run is the replication; the without-month run is reported next to it. |
| Shuffled-label check | my choice | Labels permuted within months 0 to 2 (seed 0), Base, first sampled configuration. Passes if the oracle TPR at 5% FPR, pooled over months 4 to 7, is within 0.02 of 0.05 (about 7 binomial standard errors at the pooled positive count). |
| PSI importance | my choice | In Stage F, Base only, a check model (first configuration, real labels, main split). After the full run, all variants, from the tuned seed 0 LightGBM gain importance. |
| Oracle tripwire | my choice | Fires if any single-threshold strategy (static, label-free, delayed-label) has realized FPR within the target and TPR above the oracle's on the same month, model, seed and target, or if the oracle is over budget. This is impossible by construction, so it detects a bug. Group-wise strategies use a different decision rule and are excluded. |
| Too-good tripwire | my choice | Fires if any oracle TPR at 5% FPR exceeds 0.9. |
| Bootstrap scope | my choice | 1,000 paired resamples for the 5% target. Exploratory targets (1%, 2%, 10%) get point estimates and seed spread only. If the logistic regression seeds give identical scores (checked, not assumed), intervals are computed once, for seed 0. |
| Percentile intervals | my choice | Percentile intervals with re-estimated thresholds need not contain the point estimate. The number of interval rows where this happens is recorded in results/manifest.json and reported. |

## Scoring rules for PREDICTIONS.md

Declared 2026-10-16 while the replication check was running, before any main-study model was trained. Every rule uses LightGBM seed means (summary.csv), the 5% target and the primary age definition. "Deployable three" means static, label-free top 5% and delayed-label lag 1. "Label-free" means label-free top 5% (the primary version). Each line is scored hit or miss, with the numbers shown; bootstrap intervals are shown beside them but do not change the score.

| Prediction | Rule |
|---|---|
| 1 | Base, I, II, III: in each of the 16 variant-months, the largest minus the smallest TPR among the deployable three is at most 4 points. Hit if all 16 hold. |
| 2 (first part) | Base, I, II, III: static realized FPR between 4% and 6% in each of the 16 variant-months. |
| 2 (second part) | Base, I, II, III: label-free realized FPR between 4.2% and 4.8% in each of the 16 variant-months. |
| 3, 8 | Variant IV (3) or V (8): absolute difference between the mean static realized FPR over months 6 and 7 and over months 4 and 5 is below 0.5 points. |
| 4, 9 | In each of months 6 and 7: among the deployable three, the largest absolute budget miss is label-free, with a signed miss between -1.0 and -0.5 points, and the smallest is static or delayed-label lag 1. Hit if both months hold. |
| 5, 10 | In each of months 6 and 7: the highest TPR among the deployable three is static or delayed-label lag 1, and that strategy also has the highest realized FPR of the three. Hit if both months hold. |
| 6, 11 | Absolute difference between the mean static FPR ratio over months 6 and 7 and over months 4 and 5 is below 0.05. |
| 7, 12 | In each of months 6 and 7: the label-free FPR ratio is within 0.05 of the static FPR ratio, and the age group with the higher fraud rate in that month receives at least 65% of label-free alerts. Hit if both months hold. |
| A, B | Variant IV (A) or V (B): for each of static, label-free top 5%, label-free validation alert rate, delayed-label lag 1 and the oracle, mean TPR over months 6 and 7 is below mean TPR over months 4 and 5, and every such loss exceeds the largest gap between strategies (largest minus smallest TPR among the same five) in any test month. |

## Data files

The loader does not assume file names. It lists every file in `data/raw/`, and the mapping from file name to variant is written explicitly in `src/` only after the actual Kaggle names have been seen. It stops if it does not find exactly six variant files.

## Decision log

| Date | Decision |
|---|---|
| 2026-10-16 | `month` excluded in the main study; replication run with and without it. |
| 2026-10-16 | Main split: train 0 to 2, validation 3, test 4 to 7 (my choice). |
| 2026-10-16 | Protected group: `>= 50` primary, `> 50` sensitivity, subject to the audit check against Table 1. |
| 2026-10-16 | Figure 1 readings are a loose sanity bound (about plus or minus 0.05), not pass/fail. |
| 2026-10-16 | Final protected group definition: older group `customer_age >= 50` (primary), `> 50` as the pre-declared sensitivity analysis. Evidence (reports/data_audit.md, results/audit.json): mean absolute difference between the measured older-group share and Table 1 across all variant subsets is 1.24 points for `>= 50` and 30.66 points for `> 50`; under `>= 50` every subset is within 5 points (largest, Base: 18.3% measured against 23%). Recorded before the first model run. |

| 2026-10-16 | Shuffled-label check: FAILED, tripwire fired. Pooled oracle TPR at 5% FPR over months 4 to 7 was 0.1172 against the declared 0.05 +- 0.02. The pass criterion is not redefined (user decision). Diagnostics found no leak; the failure traces to a wrong null hypothesis: fraud applications are atypical, so a model fitted to random labels can exceed 5% TPR at 5% FPR. This remains a caveat on all main results. |
| 2026-10-16 | Post hoc, added after the tripwire fired, with no pass/fail threshold: (a) 20 label shuffles on Base for LightGBM and logistic regression on the main split, with min, median and max TPR at 5% FPR next to the real-label models and a label-free density score; (b) a univariate AUC leak audit per feature on training and test months, flagging AUC above 0.75 or below 0.25 for review; (c) a unit test that every fitted preprocessing step uses training months only. |

Audit observations that differ from the documentation (none is a tripwire): the released files match Table 1's group sizes under `>= 50`, although the variant-generation notebook (cell 7) builds its groups with `> 50`; Variant IV has 50/50 groups as Table 1 says, not the `majority_size = 0.9` of notebook cell 17; Variant IV's test-month prevalence is about 1.1% in both groups, not the 1.5% in Table 1's parentheses; Base's older-group prevalence is 2.3%, not Table 1's 1.8%. Base monthly fraud rates (0.87% to 1.47%) lie inside the 0.85% to 1.5% range stated in Sec 3.1 (p4). Variants III, IV and V share one monthly fraud-rate profile and Base, I and II another.
