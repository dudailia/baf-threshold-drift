# Call prep: hard questions about this study

The hardest questions a Feedzai researcher is likely to ask, with what a strong answer must contain. The questions after question 10 were added from a cold read by a fresh reviewer who saw only the README, REVIEWING.md, the one-pager, RESULTS.md and src/ (reports/hostile_review.md). Every number is generated from `results/` and `results_posthoc/` by `src/trace.py`; nothing here is new analysis. Post hoc results (RESULTS_POSTHOC.md) were declared after the main results were seen and are labelled as such.

## 1. The paper sets its threshold on the test labels. Is your "static" comparable to anything in the paper?

A strong answer says that the paper's operating point is the oracle here, on pooled test months (notebook cell 10), so the paper never measures a deployed threshold; that the replication of the paper's setup gives a top-5 TPR of 0.552 with `month` as a feature, inside the loose bound around the Figure 1 reading; and that static is the deployable counterpart, set on a validation month that the paper does not have.

## 2. Your shuffled-label check failed. Why trust any number?

It must concede the failure plainly: pooled TPR 0.117 at 5% FPR against the declared 0.05 plus or minus 0.02, with the criterion not redefined. Then the evidence against a leak: 20 shuffles give a LightGBM median of 0.059 (the original was the maximum) and a logistic regression range of 0.026 to 0.069; a label-free density score alone reaches 0.083; the leak audit flags 0 features; a unit test confirms that every fit uses training months only; and an independent recomputation matched every stored metric. The honest conclusion is that a wrong null (fraud applications are atypical) is one possible explanation, not established, since the median shuffle was inside the tolerance; the check did not pass.

## 3. Is the static under-spend real, or an artefact of month 3?

This is the weakest main finding, and the answer must say so. On the main split the miss is -0.87 to -2.32 points in months 5 to 7, with all 18 intervals below zero in six variants sharing one base, and logistic regression agrees. Post hoc, a threshold set on month 4 also under-spends (18 of 18 intervals below zero), but one set on month 2 over-spends by +0.33 to +5.82 points. So "a threshold set once misses its budget" holds from month 5 on in every split; "it under-spends" depends on the validation month. Post hoc, the sign in months 5 to 7 is stable across the five best tuning trials and a strongly regularised model (0 sign changes in 90 cells, six variants sharing one base), no single feature explains the static miss, and with the model held fixed the sign still depends on the threshold month in 9 of 18 cells (RESULTS_POSTHOC.md section 8), so the reversal is not only a training-window effect.

## 4. Why make budget miss primary rather than TPR at 5% FPR?

Because every strategy thresholds the same scores of the same month, all operating points sit on one ROC curve, so a strategy that overshoots the budget buys TPR. TPR comparisons are only meaningful at equal realized FPR; the oracle fixes realized FPR at 5% by construction. The choice was declared before results (PROTOCOL.md, decision log).

## 5. Label-free at the validation alert rate looks best. When does it fail?

It assumes the fraud rate stays near the validation month's. It is within 0.5 points in 22 of 24 variant-months but goes over budget, up to +0.70 points, where the fraud rate falls below month 3's (Variants III to V), as the synthetic mechanism study predicts for a prevalence shift. Top 5% of applications is under budget everywhere for the arithmetic reason that frauds take part of the alerts. Post hoc and exploratory, estimating each month's FPR from isotonic-calibrated probabilities (fitted on month 3 only) stays within 0.5 points in 24 of 24 variant-months, but most of that follows from the FPR identity at this prevalence: the alert share that gives exactly 5% FPR is 5.26% to 6.10% of applications, and a fixed rule that flags the top 5.75% is within 0.5 points in 24 of 24 variant-months too (RESULTS_POSTHOC.md section 7). Calibration gives a lower average miss, but the paired comparison with the best fixed share is inconclusive; it was chosen after seeing the results and needs a pre-registered test.

## 6. Do your intervals include threshold-estimation uncertainty, and are they too narrow?

Yes: each resample re-estimates every threshold from its resampled source month. An independent agent's own bootstrap gave widths close to the stored ones (ratio of its widths to the stored widths: median 1.004, range 0.883 to 1.097). Seed spread is reported separately and is small for LightGBM. In 6 of 21,384 interval rows the point estimate falls outside its percentile interval.

## 7. Recalibration does not change the FPR ratio. Is that an artefact of the age split or of the strategies you chose?

Across global-threshold strategies the ratio differs by at most 0.094 within a variant-month under `>= 50`, and by at most 0.110 under `> 50`. Any single global threshold moves both groups along their own score distributions, so it did not equalise their FPRs here; group-wise thresholds (an exploratory diagnostic that uses age at decision time) reach ratios of 0.547 to 0.998.

## 8. Variant IV removes the prevalence disparity after month 5, yet the FPR ratio stays far below 1. Why?

The model was trained only on months with the disparity and has `customer_age` as a feature, and one possible reading, not tested here, is that it keeps scoring older applicants higher for that reason; the ratio stays between 0.081 and 0.125, and the older group gets about 89% of label-free alerts in months 6 and 7 at 51% of applications. A strong answer also says what was not tested: dropping age as a feature, and retraining on post-change months for fairness.

## 9. Delayed labels: with a realistic lag, or with retraining, would the conclusions change?

Lag 1 swings from -2.09 to +1.24 points; lags 2 and 3 mostly stay under budget (RESULTS.md section 4). Post hoc, retraining on months 0 to t-2 with the threshold from month t-1 ranges from -1.97 to +1.76 points, within 0.5 points in only 5 of 18 variant-months, and has a larger absolute miss than label-free at the validation alert rate in 13 of 18; it shows -0.67 to +6.61 points of TPR over lag 1, mostly at a higher realized FPR (16 of 18 variant-months), and no better budget control (RESULTS_POSTHOC.md section 4).

## 10. Is the static miss a property of the tuned model, or would a different model drift differently?

Logistic regression shows the same direction (-1.41 to -2.92 points). Post hoc, the other four of the five best tuning trials and a strongly regularised model change the sign of the static miss in 0 of 90 month cells from month 5 to month 7, with static misses of -2.16 to -0.35 points across them (RESULTS_POSTHOC.md section 3).

## Added after the cold read

### Label-free sets each month's threshold from that whole month's scores. Is that look-ahead?

Yes, in a streaming setting, and a strong answer concedes it. The rule was declared before data (PROTOCOL.md, Thresholds: the 95th percentile of that month's scores), so it describes decisions made at month end, or a deployment that knows the month's score distribution in advance. Static and delayed-label do not get this information, so the comparison favours label-free. A deployable version would use the previous month's score quantile or a running quantile; that was not run. It would face the month-to-month score shifts that moved delayed-label lag 1 from -2.09 to +1.24 points, but how much was not measured.

### With `month` dropped, do the velocity features act as a clock?

A strong answer says this is open. `velocity_4w` has the largest PSI of the top 10 features in Base, II, III and IV (RESULTS.md section 1), and trees cannot extrapolate: a value beyond the training range lands in the edge leaf. The post hoc mechanism test replaced one feature at a time with month 3 draws (RESULTS_POSTHOC.md section 2), which breaks the dependence between the three velocity features and cannot see a joint effect. Dropping `velocity_6h`, `velocity_24h` and `velocity_4w` together, or replacing them jointly, was not run.

### The shuffled-label check used the first sampled configuration, not the tuned model. What did it test?

As declared before data (PROTOCOL.md, Implementation decisions: Base, first sampled configuration), it tests the pipeline (preprocessing, splits, thresholds) with one fixed LightGBM configuration, not the tuned model behind the results; the 20 repeat shuffles use the same configuration. The permutation is over the pooled rows of months 0 to 2 (src/checks.py), so it does not keep each training month's prevalence. Logistic regression, which needs no tuning, gives a TPR of 0.026 to 0.069 at 5% FPR over the same shuffles. Rerunning the check with each variant's tuned configuration, and with a within-month permutation, was not done.

### A fired tripwire exits non-zero. How did `make all` finish and reproduce every file?

The Makefile runs the shuffled check with a leading `-`, which ignores its exit status, with a comment citing the user's decision to keep the failure as a caveat (PROTOCOL.md decision log). The fired state is written to results/tripwires.json; every other check still stops the build. "Reproduced every file" means the outputs are byte-identical, not that the check passed.

### How many independent pieces of evidence are behind "every static interval below zero in months 5 to 7"?

Fewer than 18, and a strong answer says so. The six variants come from one generator and one base; Variants III, IV and V share one monthly fraud-rate profile and Base, I and II another (reports/data_audit.md). The intervals resample applications given one model, one split and one tuning run, so they measure only the resampling part of the uncertainty. The split matters more: with the threshold set on month 2 the sign reverses (question 3 above). The headline holds for the month 3 split; the effective number of independent replications was not measured.

### FPR ratios are compared across strategies at different realized FPRs. Were they compared at matched FPR?

No. Each strategy's ratio is read at its own realized FPR, and the ratio moves with the operating point, so part of any ratio difference restates the budget miss. Across global-threshold strategies the ratio differs by at most 0.094 within a variant-month. A comparison at matched realized FPR was not run.

### Delayed-label assumes month m - k labels are complete when month m starts. Is that realistic?

No: BAF gives final labels, while real application-fraud labels mature over months. Partial labels were not modelled. Lags 2 and 3 are the only proxy for slower labels here (RESULTS.md section 4), and they assume complete labels too.

### Where does the "within 0.5 points" band come from?

A strong answer concedes that it was chosen at the write-up, after the results were seen (commit 125042c), not declared in PROTOCOL.md; the only earlier 0.5-point thresholds are in the user's predictions 3 and 8. The declared primary comparison is the signed and absolute budget miss with paired intervals, which the band only summarises; counts at other bands were not computed.

### What does `make check` actually prove?

Two things, and a strong answer separates them. At render time (`make tables`, src/trace.py), every result number is written by a named-value placeholder from results/values.json or results_posthoc/values.json, and rendering refuses any number typed into a template unless it is declared as a text constant (months, targets, tolerances, counts of configurations and resamples) in the results manifests; so each result number corresponds to its key by construction. `make check` then confirms only that every printed number exists somewhere in the results files at the precision shown, which almost any short number does; on its own it would be weak. The independent recomputation of every stored metric is the stronger evidence (REVIEWING.md).

## What the study does not show

- That any of this holds for real fraud data: BAF is synthetic, and all six variants come from one generator.
- That the static miss has a fixed sign: post hoc, it reverses with an earlier validation month.
- Which features drive the negatives' score drift: no single feature explains the static miss.
- Anything about retraining at scale, threshold policies with human review capacity, or costs.
- That the shuffled-label check passed: it did not, against its declared tolerance.
- Anything about fairness interventions beyond the group-wise threshold diagnostic, or about protected attributes other than age.
