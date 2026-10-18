# Code review: leakage and threshold rules

Scope: PROTOCOL.md and every file under `src/` (including `src/posthoc/`), as they stand at commit 0e765ae (src/ is unchanged at 1306af0; the follow-up fixes at the end shift some line numbers in src/fastboot.py, src/schema.py and src/posthoc/). No results, reports, tests, docs or git history were read, and no data file was loaded. Line numbers refer to the current files.

Method: each place where a fitted object, a threshold or a resample is built was traced back to the rows it can see. Where behaviour was not obvious from the code, it was confirmed with read-only Python on small synthetic arrays (listed at the end). No file other than this one was written.

Main split: train months 0 to 2, validation month 3, test months 4 to 7. Post hoc splits were checked against their own declarations in PROTOCOL.md (rolling A: train 0-1, validate 2, test 3-7; rolling B: train 0-3, validate 4, test 5-7; retraining: train 0..t-2, threshold on t-1, apply to t; isotonic: fit on month 3 only; validation-month isolation: threshold on m, apply to t > m >= 3).

## Summary

No path was found by which a month that is not a training month (months 3 to 7 in the main study, or the declared non-training months of a post hoc split) reaches a fitted preprocessing step, a model fit, early stopping or hyperparameter selection, other than the validation month's permitted use for selection. Threshold rules and the bootstrap match the protocol exactly on tied synthetic data. Nothing was found that is wrong. Five suspicious items are listed; none involves test-month leakage, and in the standard full run none would change a number unless the condition named in its entry held.

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

## 1. Scalers

What the code does. The only scaler is the `StandardScaler` inside `LRPrep` (src/preprocess.py:49), placed after the median imputer in a `Pipeline`, inside a `ColumnTransformer` that is fitted once on `apply_sentinels(train)[cols]` (src/preprocess.py:53). `transform` (src/preprocess.py:57-58) only applies it. Every caller passes training rows to `fit`: src/train.py:111 (months 0 to 2), src/diagnostics.py:45 (months 0 to 2). LightGBM gets no scaling. The density score in src/diagnostics.py:59 uses the train-fitted `LRPrep` output on test rows, so nothing is refitted there either.

Verdict: fine.

## 2. Encoders and category maps

What the code does. For LightGBM, `LGBMPrep.fit` stores the sorted list of levels seen in the training rows for each categorical column (src/preprocess.py:27). `transform` casts to `str`, sets any level not in that list to missing, and builds a `pd.Categorical` with exactly the training levels (src/preprocess.py:33-35), so the integer codes are identical in every month and LightGBM's stored `pandas_categorical` list matches. For logistic regression, `OneHotEncoder(handle_unknown="ignore")` is fitted inside the same `ColumnTransformer` on training rows (src/preprocess.py:50, 53); an unseen level becomes an all-zero row. All `fit` calls receive training months only: src/train.py:93, src/checks.py:53 and 92, src/diagnostics.py:44, src/posthoc/rolling.py:49 (split's train months), src/posthoc/retrain.py:34 (months 0..t-2), src/posthoc/hyper.py:49, src/posthoc/mechanism.py:38.

A synthetic check confirmed that a level present only in a test frame becomes missing and that the category list is the training list.

One wording difference: PROTOCOL.md says unseen levels "map to an 'unknown' code". The code maps them to missing. For LightGBM a missing categorical value and an unseen level take the same branch (neither is in the left-hand category set of a split), and for logistic regression the all-zero encoding is the standard unknown treatment, so the behaviour matches the intent. In src/diagnostics.py:88-89 the leak audit target-encodes categoricals with training-month fraud rates, which is in-sample on the training months; that only affects a diagnostic AUC, not any model.

Verdict: fine.

## 3. Imputers, imputation medians and sentinel handling

What the code does. Sentinel handling (src/data.py:94-102) is a fixed rule with no fitted statistics: -1 becomes NaN in the five columns of src/data.py:57-63, and any negative becomes NaN in `intended_balcon_amount` (src/data.py:65). It is applied identically to every month. LightGBM receives the NaN values and handles them natively (src/preprocess.py:31); the replication run keeps raw values on purpose (src/checks.py:53). For logistic regression, `SimpleImputer(strategy="median", add_indicator=True)` is fitted on training rows only (src/preprocess.py:49, 53). A synthetic check confirmed the stored medians come from the training frame. Missing-indicator columns are created only for features that had missing values in training (scikit-learn's default `features="missing-only"`); a feature missing only in later months would be imputed with the training median without an indicator, which is a choice, not a leak.

Verdict: fine.

## 4. Hyperparameter tuning

What the code does. Twenty configurations are drawn once with seed 2022 (src/models.py:17-33; src/train.py:25, 69). Each is trained on months 0 to 2 with seed 0 (src/train.py:74) and scored on month 3 only (src/train.py:75, 96). The selection statistic is TPR on month 3 at the threshold set at 5% FPR on month 3's own negatives by `threshold_at_fpr` (src/train.py:48-50), which is the same rule the static strategy uses. The best trial is the highest month-3 TPR, ties to the earlier trial (src/train.py:82). Months 4 to 7 are never scored during tuning: `prep.transform(val)` is the only evaluation input. Rolling splits tune the same way on their own validation month (src/posthoc/rolling.py:52-63, month 2 for A and month 4 for B). Hyperparameter sensitivity reranks the main tuning log by the same month-3 statistic (src/posthoc/hyper.py:28-32), with the same tie rule as src/train.py:82. Retraining reuses the main study's selected configuration and does not tune (src/posthoc/retrain.py:38).

Note, not a leak: the final seed 0 model is bit-identical to the selected tuning trial (same configuration, same seed, same rows, src/train.py:74 and 102). Seed 0 is therefore the draw that won selection on month 3, while seeds 1 to 4 are fresh draws. Its month-3 TPR is optimistic by selection. Because seed 0 is the reference seed for the bootstrap tables, readers should know this; it does not let any test month influence anything.

Verdict: fine.

## 5. Early stopping

What the code does. There is none. `fit_lgbm` calls `LGBMClassifier(...).fit(X, y)` with no `eval_set` or callbacks (src/models.py:58-59), and the number of trees is the sampled `n_estimators` (src/models.py:23, 39). A search of `src/` finds no `early_stopping`, `eval_set` or `callbacks`. Logistic regression runs to convergence on training rows (src/models.py:62-67).

Verdict: fine.

## 6. Calibration

What the code does. The only calibration is the post hoc isotonic map. `_point` fits `IsotonicRegression` on month 3 scores and labels (src/posthoc/isotonic.py:48-49) and then, for each test month, uses only that month's scores to set the threshold so that the estimated FPR, the sum of (1 - p) over flagged rows divided by the sum over all rows, is at most 5% (src/posthoc/isotonic.py:52-55). Test-month labels are used only to compute the realised metrics (src/posthoc/isotonic.py:34-44). In the bootstrap, month 3 is resampled with the main study's key and the map is refitted per resample (src/posthoc/isotonic.py:66-67), and each test month's threshold uses that month's resampled scores (src/posthoc/isotonic.py:71-73). Rows with zero weight are dropped before the threshold search (src/thresholds.py:24-25); with the point-estimate weights this only removes rows with p = 1, which by monotonicity sit at the top of the score range and are flagged anyway, so the flagged set is the same. No other calibration exists (no `CalibratedClassifierCV`, and LightGBM probabilities are used as raw scores).

Verdict: fine.

## 7. Seed handling

What the code does. LightGBM gets `random_state=seed` with `colsample_bytree=0.8`, and for GBDT `subsample=0.8, subsample_freq=1` (src/models.py:46-54); GOSS has its own sampling. A synthetic check on LightGBM 4.7.0 with one GBDT and one GOSS configuration from `sample_configs(20, 2022)` gave maximum score differences of 0.069 and 0.037 between seeds 0 and 1, and 0.0 between two fits with seed 0, so the seed does change the model and the same seed reproduces it (single thread). Logistic regression with lbfgs ignores the seed (src/models.py:63); src/evaluate.py:51-53 checks for identical scores rather than assuming it.

Reuse across strategies and splits. Bootstrap resample weights are keyed by `(variant, month, chunk)` only (src/fastboot.py:220; src/evaluate.py:63), so every strategy, model, seed, post hoc split and post hoc analysis uses the same resampled rows of a given month. That is what makes the comparisons paired, and nothing combines intervals across seeds, so the shared draws do not inflate any interval. The shuffled-label permutation uses `default_rng(0)` on the training-month labels only (src/checks.py:99-101); the post hoc diagnostic uses `default_rng(k)` for k = 0..19 on the same training labels (src/diagnostics.py:50). Neither touches months 3 to 7. Seed 0 being the selected tuning model is covered under item 4.

Verdict: fine.

## 8. Month indexing

What the code does. The main split is `MAIN_SPLIT` (src/data.py:67): train [0, 1, 2], validation [3], test [4, 5, 6, 7]. Training rows are `month.isin(train)` and evaluation rows are `month.isin(validation + test)` (src/train.py:26, 88-90); both use list membership, so there is no off-by-one. The paper split (src/data.py:68) is train 0 to 5, test 6 and 7. Rolling A and B are written out in src/posthoc/rolling.py:24-27 and match PROTOCOL.md. Retraining uses `month <= t - 2` for training and `[t - 1, t]` for evaluation, with an assertion that the largest training month is t - 2 (src/posthoc/retrain.py:32-35), for t in [5, 6, 7] (src/posthoc/retrain.py:23). The validation-month analysis builds pairs 3 <= m < t <= 7 (src/posthoc/valmonth.py:17, 25-29). Delayed-label source months are `m - k` with k in (1, 2, 3) (src/fastboot.py:24, 163). Months are iterated in sorted order (src/fastboot.py:138), so the validation month's thresholds always exist before any later month uses them. The months stored with predictions come from the frame itself (src/train.py:60), not from a counter.

Verdict: fine. (The fact that the split months are defined in several files is a separate item, 13h.)

## 9. Tie handling in thresholds

What the code does. Every strategy flags `score >= t` (src/thresholds.py:16-17; src/metrics.py:13). `_threshold_for_budget` (src/thresholds.py:20-34) collapses tied scores into one weighted value, walks distinct values from the top, finds the first value whose cumulative weight breaks the budget, and returns `nextafter(that value, +inf)`. That is the smallest representable t for which the weight of {score >= t} is at most the budget, and a tie block is never split. `threshold_at_fpr` applies it to the month's negatives with budget f times the negative count (src/thresholds.py:37-42). `threshold_top_fraction` applies it to all applications with budget f times the count (src/thresholds.py:45-49). The fast evaluator implements the same rule with prefix sums: `_cut` (src/fastboot.py:87-89) returns the largest number of distinct scores whose cumulative weight stays within budget, `threshold_from_cut` (src/fastboot.py:78-80) returns `nextafter` of the first unflagged distinct score, and `count_at_or_above` (src/fastboot.py:75-76) applies a threshold set on another month. Static uses month 3 negatives at f (src/fastboot.py:147-148, 156-157); label-free top uses all of the current month's applications at f (src/fastboot.py:158-159); the validation alert rate rule takes the share of month 3 applications flagged by the static threshold (src/fastboot.py:150) and flags at most that share of the current month (src/fastboot.py:160-161).

Synthetic confirmations. Two negatives tied at the top with a budget of one: nothing flagged (FPR 0, below target, never above). Budget of two with one top score and a tie of two below it: one flagged, FPR 2.5%. One hundred distinct negatives at 5%: five flagged, and the next float down flags six, so t is the smallest valid threshold. Positives do not move `threshold_at_fpr`. For 1,000 distinct scores the label-free rule flags 50, the same as `score >= np.quantile(score, 0.95)`. On 3,000-row months with heavy ties (scores rounded to two decimals), all nine strategies in `src/fastboot.py` matched a direct computation from `src/thresholds.py` with a maximum absolute difference of exactly 0 in realised FPR, TPR and both group FPRs, and the oracle was within budget in every month.

Two notes that are not defects. First, PROTOCOL.md describes the label-free rule as "the 95th percentile"; the code implements "largest set that flags at most 5%, ties not split", which is the same for distinct scores and flags fewer when a tie block straddles the boundary. LightGBM scores are piecewise constant, so tie blocks do occur; the code's rule is the one stated in the thresholds module docstring and the protocol's "ties are handled exactly". Second, the `source_month` stored for `label_free_val_rate` is the current month (src/fastboot.py:161), although the rule also uses month 3's alert rate. That is a metadata label only.

Verdict: fine.

## 10. Delayed-label lag

What the code does. For test month m and lag k, the source is `src = m - k`, used only if `src >= validation_month and src in data` (src/fastboot.py:163-165); otherwise the cell is `None` and is written as unavailable with `source_month = m - k` (src/fastboot.py:167-168, 207-209). With the main study's months 3 to 7 this gives lag 1 for months 4 to 7, lag 2 for 5 to 7 and lag 3 for 6 and 7, exactly as PROTOCOL.md states; the synthetic run reproduced the unavailable cells (lag 2 at month 4, lag 3 at months 4 and 5). The threshold is the 5% FPR threshold on the source month's own labelled scores (src/fastboot.py:165, which reads `oracle_t[(src, f)]`, set at src/fastboot.py:147-148). Because the predictions file holds months 3 to 7 only, a training month can never be a source even if the condition were loosened. In rolling splits the same function receives the split's validation month (src/posthoc/common.py:60; src/posthoc/rolling.py:83), so lag 1 at month 3 in split A uses month 2 (the split's validation month, not a training month) and split B starts at month 5 with source month 4. Retraining sets its threshold on month t - 1, which is outside its training months 0..t-2 (src/posthoc/retrain.py:32-35, 48). The `src >= validation_month` test assumes every month below the validation month is a training month, which holds for every split in this project.

Lag 1 at month 4, lag 2 at month 5 and lag 3 at month 6 use the same month-3 threshold as static, and in the bootstrap they use the same resampled month-3 weights, so they equal static in every resample (confirmed: identical arrays for lag 1 and static at month 4).

Verdict: fine.

## 11. Group FPR counts

What the code does. Ages are binned into under 50, exactly 50 and over 50 (src/fastboot.py:30-33). The older group is bins (1, 2) for `>=50` and bin (2,) for `>50` (src/fastboot.py:27), which reproduces `age >= 50` and `age > 50` for any integer age, not only decade-rounded ones. Rows are split into six cells by label and age bin (src/fastboot.py:53). A group's FPR is flagged negatives in the group divided by all negatives in the group (src/fastboot.py:120-122), negatives being rows with `fraud_bool == 0`; positives are excluded from both terms. `n_pos_*` and `n_neg_*` are recorded for both groups under both definitions (src/fastboot.py:126-127), and cells with fewer than 30 positives are flagged (src/evaluate.py:150-151). The FPR ratio is the smaller group FPR over the larger (src/fastboot.py:128-129), NaN if both are 0. Group-wise static sets one threshold per primary-definition group on month 3 negatives of that group (src/fastboot.py:151-153) and applies each to its own group (src/fastboot.py:173-174); group-wise label-free flags at most 5% of each group's applications in the current month (src/fastboot.py:175-177). These are evaluated under both age definitions while the decision uses the primary one, which is the intended design. The isotonic analysis uses the same bins (src/posthoc/isotonic.py:35) and the mechanism analysis uses `customer_age >= 50` (src/posthoc/mechanism.py:54, 58). The synthetic run matched both group FPRs exactly for every strategy, including both group-wise ones.

Verdict: fine.

## 12. Bootstrap: source data and pairing

What the code does. For each chunk of 20 resamples, one multinomial weight vector per month is drawn from a SHA-256 seed of `(weight_seed, month, chunk_start)` (src/fastboot.py:36-41, 218-220). The same weight dictionary is then used for every strategy in a single pass (src/fastboot.py:221 into 134-189). Inside a resample: static re-estimates its threshold from month 3 with month 3's resample weights; delayed-label lag k from month m - k with that month's weights; label-free top and the oracle from the resampled current month; the validation alert rate rule takes the share from resampled month 3 and applies it to resampled month m; group-wise static uses resampled month 3 per group. No strategy reads a month it may not use. A direct re-implementation of 25 resamples using `src/thresholds.py` with explicit weights reproduced the bootstrap realised FPR of static, label-free top, validation alert rate, delayed lag 1 and the oracle with a maximum absolute difference of exactly 0.

Pairing. Because the weights depend only on variant, month and chunk, both members of every pair in src/evaluate.py:31-36 see the same resampled rows of the test month and the same resampled source months, and the paired difference is taken element by element (src/evaluate.py:81). Post hoc analyses rebuild the same keys: `main_boot` (src/posthoc/common.py:101-112), rolling (src/posthoc/common.py:60), retraining (month t - 1 and t, src/posthoc/retrain.py:48), isotonic (src/posthoc/isotonic.py:66, which writes the key as `((variant,), m, c0)`, the same `repr` as fastboot's) and fixedq (src/posthoc/fixedq.py:41). Since the weights also depend on the row count, pairing with the main study requires the same rows per month in both prediction files. That holds in the full run (both read the whole CSV in the same order). It would not hold if the main predictions came from a sampled run while the post hoc code reads the full file (`load` samples at src/train.py:43-44, `load_variant` in the post hoc code does not); the arrays would still have equal length, so this would pass silently. This is a sample-mode concern only and is folded into 13f.

Verdict: fine.

## 13a. `month` as a feature

What the code does. `_features` drops the label and, unless `include_month=True`, `month` (src/preprocess.py:13-15). `LRPrep` always excludes it (src/preprocess.py:43). The main training asserts that neither `month` nor the label is a column (src/train.py:94); rolling and retraining assert the same for `month` (src/posthoc/rolling.py:50; src/posthoc/retrain.py:35). Only the replication run includes it, by design and with an assertion (src/checks.py:53-54). hyper.py and mechanism.py rely on the default `include_month=False` without an assertion; the default is correct.

Verdict: fine.

## 13b. Features that encode the label

What the code does. No feature is derived from labels anywhere in `src/`; the only label-derived quantities are evaluation metrics and the diagnostic target encoding in src/diagnostics.py:88-89. `x1` and `x2` in Variants III and V are kept as features by design: they are the injected separability bias (PROTOCOL.md, Features table). Whether any raw column in the released files carries label information (for example `device_fraud_count`, which by its datasheet name aggregates fraud labels) cannot be settled from the code; the per-feature AUC audit in src/diagnostics.py:79-102 is the check that would show it, and its output was not read for this review.

Verdict: fine (for the code).

## 13c. Duplicate rows across splits

What the code does. `cross_split_duplicates` hashes every column except `month` (so the label is included) and counts hashes that occur in more than one part of a split (src/audit.py:102-112). It is run for the main split and the paper split only (src/audit.py:179-180).

Why suspicious. Two post hoc fit/threshold boundaries are not covered by either check. Rolling split A trains on months 0-1 and validates on month 2; months 0, 1 and 2 are all in the same part in both the main split and the paper split, so duplicates between {0, 1} and {2} are never counted. Retraining for t = 6 trains on months 0-4 and sets the threshold on month 5; months 4 and 5 are both "test" in the main split and both "train" in the paper split, so duplicates between month 4 and month 5 are never counted. Also, because the label is part of the hash, a feature-identical pair with different labels is not counted (that pair cannot leak a label, so this part is minor).

Failure scenario: if month 1 and month 2 of some variant shared identical rows, rolling split A would select its configuration and set its static threshold on rows the model had trained on, and the audit would report 0 cross-split duplicates.

Would a fix change numbers: no computed metric would change. A month-by-month pairwise duplicate count (8 by 8) would cover every split in the project and could only reveal a problem, not alter a result.

## 13d. Oracle tripwire

What the code does. For every available single-threshold strategy (static, both label-free rules, all delayed lags), it fires if realised FPR is within the target and TPR exceeds the oracle's on the same variant, model, seed, target, age definition and month (src/evaluate.py:112-115). Because every strategy flags `score >= t` on the same scores, any within-budget flagged set is a subset of the oracle's, so this cannot happen without a bug. It also fires if the oracle is over budget (src/evaluate.py:116-118) and if any oracle TPR at 5% exceeds 0.9 (src/evaluate.py:119-121). Group-wise strategies are correctly excluded, since two thresholds can beat a single one. Unavailable cells are filtered first (src/evaluate.py:110). The post hoc isotonic, fixed-quantile and retraining strategies are not covered by any tripwire; isotonic and fixed-quantile use the same single-threshold rule and could be checked against the main oracle in the same way.

Verdict: fine.

## 13e. Shuffled-label check

What the code does. Training rows are months 0 to 2; their labels are permuted once with `default_rng(0)` (src/checks.py:99-101) and passed to `_check_model`, which rebuilds the same training frame in the same row order, fits `LGBMPrep` on it and trains LightGBM (src/checks.py:90-94). Labels of months 3 to 7 are untouched and used only for evaluation. The pass criterion is the oracle TPR at 5% FPR pooled over months 4 to 7 within 0.05 plus or minus 0.02 (src/checks.py:110-120), as declared in PROTOCOL.md. The 20-shuffle diagnostic follows the same confinement (src/diagnostics.py:40-54). The code does what the protocol says. The check's outcome is recorded in PROTOCOL.md's decision log and was not re-examined here.

Verdict: fine.

## 13f. Resume from checkpoints without a provenance check

What the code does. Tuning resumes by skipping the first `len(done)` trials found in `results/checkpoints/tuning/<variant>.jsonl` (src/train.py:68-72) and selects from those records (src/train.py:82) without comparing the stored config, sample fraction or PREDICTIONS.md commit with the current run. Final models are skipped whenever a prediction file exists (src/train.py:98-100, 113-115). Evaluation reloads any checkpoint under `results/checkpoints/eval/` regardless of the number of resamples or code version (src/evaluate.py:57-60). The post hoc code does the same: `main_boot` cache (src/posthoc/common.py:104-107), rolling (src/posthoc/rolling.py:44, 54, 66, 80-81), hyper (src/posthoc/hyper.py:44, 53-56), retraining (src/posthoc/retrain.py:40, 44-46), isotonic (src/posthoc/isotonic.py:88-90).

Why suspicious. The checkpoint paths depend only on `BAF_OUT` (src/config.py:11-17), not on the sample fraction or the number of trials.

Failure scenario: the 10% Base sample run is executed with the default output folder; it writes `results/checkpoints/tuning/Base.jsonl` and `results/predictions/Base/lightgbm_seed*.npz` from sampled data. A later full run then skips all 20 trials, picks the configuration from the sample's month-3 TPRs, and skips every Base model because the prediction files exist, so full-run tables would silently contain sample-run scores. The same applies to evaluation checkpoints after a change to `src/fastboot.py`.

Would a fix change numbers: only if such stale files were present when the reported run was made. The prediction metadata stores `sample_fraction` and `predictions_commit` (src/train.py:104-107, 118-120), so this can be checked from `results/predictions/*/*.json` without rerunning anything. If they all show 1.0 and the expected commit, no number would change. The fix is to store a key (sample fraction, number of trials, config seed, code commit) with every checkpoint and refuse to resume on a mismatch.

## 13g. Replication operating point

What the code does. `notebook_operating_point` picks the ROC point with the largest FPR strictly below 0.05 and returns the minimum threshold at that point and the TPR of that ROC point (src/metrics.py:104-113). scikit-learn's ROC point at threshold t counts scores `>= t`. The replication then binarises with `s > t` (src/checks.py:62) and computes realised FPR and the group FPRs from that binarisation (src/checks.py:63-66), while the reported TPR is the ROC value (src/checks.py:66).

Why suspicious. The ROC point kept by `roc_curve` (with `drop_intermediate=True`) ends on a positive, so the row at score t is a positive. `s > t` drops it. Reported TPR therefore includes one positive (or one tie block) that the binarised predictions do not flag. On synthetic data (20,000 rows, 2% prevalence, 200 repetitions) TPR from the ROC point minus TPR from `s > t` was between 0.0022 and 0.0029, always positive, and the FPR was unchanged.

Failure scenario: a replication row reports TPR from one operating point and FPR ratio from another that has one fewer true positive. With a few thousand positives in months 6 and 7 pooled, the TPR gap is about 1 / (number of positives).

Would a fix change numbers: yes, the replication TPR values would fall by roughly one positive's worth (fourth decimal place at BAF's positive counts). No main-study or post hoc number would change, and the effect is far below the plus or minus 0.05 loose bound. Which TPR the notebook itself reports cannot be settled from the files in scope.

## 13h. Split months defined in several places

What the code does. The validation and test months are defined in `MAIN_SPLIT` (src/data.py:67), again in src/schema.py:16-17, again as the default `VALIDATION_MONTH = 3` in src/fastboot.py:22 (used by the main evaluation through the default argument at src/evaluate.py:63), and hard-coded as 3 or [4, 5, 6, 7] in src/posthoc/common.py:108, src/posthoc/hyper.py:58, src/posthoc/isotonic.py:25, 48 and src/posthoc/mechanism.py:28. All copies agree today.

Why suspicious. CLAUDE.md says the split months are defined in one place in `src/`.

Failure scenario: someone changes `MAIN_SPLIT` to validate on month 2. Training would tune on month 2 and save predictions for months 2 to 7, but evaluation would still take the static threshold from month 3 (and treat month 2 as a test month processed before any validation threshold exists, which raises a KeyError at src/fastboot.py:156, so at least that case would fail loudly). Changing only src/schema.py would change table filters but not the computation.

Would a fix change numbers: no. All values agree now.

## 13i. fixedq reads isotonic point estimates from a fixed path

What the code does. `fixedq` loads the isotonic bootstrap from `CKPT`, which follows `BAF_POSTHOC_OUT` (src/posthoc/fixedq.py:35; src/posthoc/common.py:21-23), but loads the isotonic point estimates from `config.ROOT / "results_posthoc" / "isotonic_metrics.csv"` (src/posthoc/fixedq.py:36), which does not.

Failure scenario: with `BAF_POSTHOC_OUT` pointing at a scratch folder (tests or a fixture), the paired row's `diff` column uses the isotonic point estimate from the real results folder while `lo`, `hi` and the verdict come from the scratch run's bootstrap.

Would a fix change numbers: not in a standard run, where both paths are the same folder. It only matters when the environment variable is set.

## Confirmations run

All with `.venv/bin/python` on in-memory synthetic arrays; no data file was loaded and nothing was written.

1. `threshold_at_fpr` and `threshold_top_fraction` on hand-built tied cases (tie block at the top larger than the budget; tie block straddling the budget; exact budget hit at 5 of 100; positives added; all scores tied). Results as described under item 9.
2. `evaluate_months` point estimates against direct computation from `src/thresholds.py` for all nine strategies on five 3,000-row months with heavy ties: maximum absolute difference 0, delayed-label availability as in PROTOCOL.md, oracle within budget.
3. Bootstrap: 25 resamples rebuilt from `resample_weights` with the same keys and recomputed with weighted `src/thresholds.py` calls for static, both label-free rules, delayed lag 1 and the oracle: maximum absolute difference 0; lag 1 at month 4 identical to static in every resample.
4. LightGBM 4.7.0: seed 0 against seed 1 changes scores for both a GBDT and a GOSS configuration from the study's sampled list; refitting with the same seed reproduces them exactly.
5. `LGBMPrep`: an unseen level becomes missing and the category list is the training list; `month` is not a column. `LRPrep`: imputer medians come from the training frame and the feature list contains no `month`.
6. `notebook_operating_point`: the ROC TPR exceeds the TPR of `score > t` by about one positive in every one of 200 synthetic draws.

## Follow-up by the coordinating session (2026-10-18)

Each suspicious item was checked against the repository and the data. No number in results/ or results_posthoc/ changed.

| Item | Outcome | Evidence or action |
|---|---|---|
| 13c Duplicate rows across splits | resolved, fine | Every variant was loaded with `src.data.load_variant` and each row hashed on all columns except `month`, once with the label and once without. In all six variants, 0 distinct rows appear in more than one month, so no post hoc boundary (rolling A and B, retraining) shares a row between training and threshold months. Script run from the session scratchpad; no file written to results/. |
| 13f Checkpoints without provenance | resolved for the main results, code left as is | All 60 files `results/predictions/*/*.json` record `sample_fraction` 1.0 and `predictions_commit` 0be4b0d. The clean rebuild of 2026-10-17 (`make clean`, which deletes results/checkpoints, then `make all`) reproduced every results file byte for byte (reports/reproducibility.md), so no stale checkpoint fed the main results. Post hoc caches are not cleaned by `make clean`; the post hoc independent check found 0 mismatches. A provenance check on resume would be a behaviour change in the training path and was not made. |
| 13g Replication operating point | confirmed, not fixed | `src/checks.py` reads TPR at the ROC point (`notebook_operating_point`, counts `>= t`) but flags with `s > t` for realized FPR and group FPRs. The reported replication TPR can include one positive the flagged set does not (about 1 divided by the test positives). Fixing it would change results/replication.csv, a hard stop, so the code is unchanged. The loose bound is plus or minus 0.05, so the replication verdict cannot change by this amount. |
| 13h Split months in several places | fixed, no number change | `TEST_MONTHS` and `VALIDATION_MONTH` in src/schema.py, `VALIDATION_MONTH` in src/fastboot.py, the month 3 passed by src/posthoc/common.py and src/posthoc/hyper.py, and `TEST` and month 3 in src/posthoc/isotonic.py now all derive from `MAIN_SPLIT` in src/data.py. The resulting values were asserted equal to the old literals (3 and [4, 5, 6, 7]); `make test` passes. Post hoc splits that differ from the main split by declaration (rolling, valmonth, retraining) keep their own month lists. |
| 13i fixedq fixed path | fixed, no number change | src/posthoc/fixedq.py now reads `isotonic_metrics.csv` from `OUT` (src/posthoc/common.py), which is `results_posthoc/` unless `BAF_POSTHOC_OUT` is set, so the standard run reads the same file as before. |
| Note: seed 0 won tuning | checked, no sign of bias in the static miss | From results/metrics.csv (LightGBM, 5% target), seed 0's static budget miss in months 5 to 7 ranks between 1 and 4 of 5 seeds across the 18 variant-months (most negative rank 1 in 4 cells, rank 4 in 6), so the reference seed is not at an extreme. |
| Note: `device_fraud_count` | resolved, fine | results/diag_leak_audit_all.csv gives it AUC 0.5 on training and test months in every variant: it carries no label information. |
