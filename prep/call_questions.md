# Call prep: hard questions about this study

The ten hardest questions a Feedzai researcher is likely to ask, with what a strong answer must contain. Every number is generated from `results/` and `results_posthoc/` by `src/trace.py`; nothing here is new analysis. Post hoc results (RESULTS_POSTHOC.md) were declared after the main results were seen and are labelled as such.

## 1. The paper sets its threshold on the test labels. Is your "static" comparable to anything in the paper?

A strong answer says that the paper's operating point is the oracle here, on pooled test months (notebook cell 10), so the paper never measures a deployed threshold; that the replication of the paper's setup gives a top-5 TPR of 0.552 with `month` as a feature, inside the loose bound around the Figure 1 reading; and that static is the deployable counterpart, set on a validation month that the paper does not have.

## 2. Your shuffled-label check failed. Why trust any number?

It must concede the failure plainly: pooled TPR 0.117 against the declared 0.05 plus or minus 0.02, with the criterion not redefined. Then the evidence against a leak: 20 shuffles give a LightGBM median of 0.059 (the original was the maximum) and a logistic regression range of 0.026 to 0.069; a label-free density score alone reaches 0.083; the leak audit flags 0 features; a unit test confirms that every fit uses training months only; and an independent recomputation matched every stored metric. The honest conclusion is that the declared null was wrong (fraud applications are atypical), not that the check passed.

## 3. Is the static under-spend real, or an artefact of month 3?

This is the weakest main finding, and the answer must say so. On the main split the miss is -0.87 to -2.32 points in months 5 to 7, with all 18 intervals below zero, and logistic regression agrees. Post hoc, a threshold set on month 4 also under-spends (18 of 18 intervals below zero), but one set on month 2 over-spends by +0.33 to +5.82 points. So "a threshold set once misses its budget" holds on every split; "it under-spends" depends on the validation month. Post hoc, the sign in months 5 to 7 is stable across the five best tuning trials and a strongly regularised model (0 sign changes in 90 cells), no single feature explains the static miss, and with the model held fixed the sign still depends on the threshold month in 9 of 18 cells (RESULTS_POSTHOC.md section 8), so the reversal is not only a training-window effect.

## 4. Why make budget miss primary rather than TPR at 5% FPR?

Because every strategy thresholds the same scores of the same month, all operating points sit on one ROC curve, so a strategy that overshoots the budget buys TPR. TPR comparisons are only meaningful at equal realized FPR; the oracle fixes realized FPR at 5% by construction. The choice was declared before results (PROTOCOL.md, decision log).

## 5. Label-free at the validation alert rate looks best. When does it fail?

It assumes the fraud rate stays near the validation month's. It is within 0.5 points in 22 of 24 variant-months but goes over budget, up to +0.70 points, where the fraud rate falls below month 3's (Variants III to V), as the synthetic mechanism study predicts for a prevalence shift. Top 5% of applications is under budget everywhere for the arithmetic reason that frauds take part of the alerts. Post hoc and exploratory, estimating each month's FPR from isotonic-calibrated probabilities (fitted on month 3 only) stays within 0.5 points in 24 of 24 variant-months, but most of that follows from the FPR identity at this prevalence: the alert share that gives exactly 5% FPR is 5.26% to 6.10% of applications, and a fixed rule that flags the top 5.75% is within 0.5 points in 24 of 24 variant-months too (RESULTS_POSTHOC.md section 7). Calibration adds a modest reduction in the average miss; it was chosen after seeing the results and needs a pre-registered test.

## 6. Do your intervals include threshold-estimation uncertainty, and are they too narrow?

Yes: each resample re-estimates every threshold from its resampled source month. An independent agent's own bootstrap gave widths close to the stored ones (ratio of its widths to the stored widths: median 1.004, range 0.883 to 1.097). Seed spread is reported separately and is small for LightGBM. In 6 of 21,384 interval rows the point estimate falls outside its percentile interval.

## 7. Recalibration does not change the FPR ratio. Is that an artefact of the age split or of the strategies you chose?

Across global-threshold strategies the ratio differs by at most 0.094 within a variant-month under `>= 50`, and by at most 0.110 under `> 50`. Any single global threshold moves both groups along their own score distributions, so it cannot equalise their FPRs; group-wise thresholds (an exploratory diagnostic that uses age at decision time) reach ratios of 0.547 to 0.998.

## 8. Variant IV removes the prevalence disparity after month 5, yet the FPR ratio stays far below 1. Why?

The model was trained only on months with the disparity and has `customer_age` as a feature, so it keeps scoring older applicants higher; the ratio stays between 0.081 and 0.125, and the older group gets about 89% of label-free alerts at 51% of applications. A strong answer also says what was not tested: dropping age as a feature, and retraining on post-change months for fairness.

## 9. Delayed labels: with a realistic lag, or with retraining, would the conclusions change?

Lag 1 swings from -2.09 to +1.24 points; lags 2 and 3 mostly stay under budget (RESULTS.md section 4). Post hoc, retraining on months 0 to t-2 with the threshold from month t-1 ranges from -1.97 to +1.76 points, within 0.5 points in only 5 of 18 variant-months, and has a larger absolute miss than label-free at the validation alert rate in 13 of 18; it adds detection (-0.67 to +6.61 points of TPR over lag 1), not budget control (RESULTS_POSTHOC.md section 4).

## 10. Is the static miss a property of the tuned model, or would a different model drift differently?

Logistic regression shows the same direction (-1.41 to -2.92 points). Post hoc, the five best tuning trials and a strongly regularised model change the sign of the static miss in 0 of 90 month cells from month 5 to month 7, with static misses of -2.16 to -0.35 points across them (RESULTS_POSTHOC.md section 3).

## What the study does not show

- That any of this holds for real fraud data: BAF is synthetic, and all six variants come from one generator.
- That the static miss has a fixed sign: post hoc, it reverses with an earlier validation month.
- Which features drive the negatives' score drift: no single feature explains the static miss.
- Anything about retraining at scale, threshold policies with human review capacity, or costs.
- That the shuffled-label check passed: it did not, against its declared tolerance.
- Anything about fairness interventions beyond the group-wise threshold diagnostic, or about protected attributes other than age.
EOF
echo drafted