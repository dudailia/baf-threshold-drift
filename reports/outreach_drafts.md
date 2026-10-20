# Outreach drafts

Drafts supplied by the user on 2026-10-19, checked number by number against results/ and results_posthoc/ (values.json keys, which the traced documents print). Marks: MATCH (same value and meaning), MISMATCH (wrong), QUALIFIED (right value, but the amendment, a post hoc split or an audit narrows what it means). Every final message is under 600 characters with the repository URL in place, and has no em dashes. The original text is kept verbatim, with its [repo link] placeholder, below each check table; the URL replaces the placeholder in the final texts.

## Jean V. Alves (Feedzai)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| 5% FPR | PROTOCOL.md primary target | 0.05 | MATCH |
| under-spent by 0.87 to 2.32 points in months 5 to 7 | results/values.json derived/static/miss_m567/max, /min; RESULTS.md line 230 | -0.0087, -0.0232 | QUALIFIED: true only for the threshold set on month 3, which the draft did not say |
| set on a different month it over-spent instead | results_posthoc/values.json rolling/A/static/miss_all/min, /max; RESULTS.md Amendment | +0.0033 to +0.0582 | QUALIFIED: post hoc split A, where the model was also retrained on months 0 and 1 and the threshold set on month 2 |
| Jan to Jun 2027, 20 minutes; FiFAR and capacity; right to work | not study numbers |  | not checked against the repo |

Original (519 characters):

> Hi Jean, thanks for connecting. Your FiFAR work treats analyst capacity as a hard limit, so this result from my BAF study seemed relevant: a threshold set once at 5% FPR under-spent its budget by 0.87 to 2.32 points in months 5 to 7, and set on a different month it over-spent instead. Repo: [repo link]. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes to tell me where the protocol is weakest?

Final (rewritten; 584 characters):

Hi Jean, thanks for connecting. Your FiFAR work treats analyst capacity as a hard limit, so this result from my BAF study seemed relevant: a threshold set at 5% FPR on month 3 under-spent its budget by 0.87 to 2.32 points in months 5 to 7, and post hoc, trained on months 0 and 1 and set on month 2, it over-spent. Repo: https://github.com/dudailia/baf-threshold-drift. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes to tell me where the protocol is weakest?

## Vasco Pearson (Feedzai)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| 5% FPR | PROTOCOL.md primary target | 0.05 | MATCH |
| flipping in 9 of 18 variant-months | results_posthoc/values.json valmonth/n_test_cells_sign_depends_on_m, valmonth/n_test_cells_multi_m; RESULTS_POSTHOC.md section 8 | 9, 18 | QUALIFIED: post hoc; counts the sign of the seed-mean miss, not intervals, over the 18 variant-months that have more than one possible threshold month |
| (rewrite) set on month 5 over-spends in 9 of its 12 later cells | results_posthoc/values.json valmonth/m5/n_positive, valmonth/m5/n | 9, 12 | MATCH |
| (rewrite) set on month 3 or 4 under-spends in months 5 to 7 | results_posthoc/values.json valmonth/m3/t5..t7/miss/max, valmonth/m4/miss/max | all < 0 (max -0.0087, -0.0101) | MATCH |
| one sanity check failed | results/tripwires.json key shuffled; RESULTS.md | fired | MATCH |

Original (481 characters):

> Hi Vasco, thanks for connecting. I ran a threshold study on the BAF suite. The result I trust most: with the model held fixed, whether a 5% FPR threshold under- or over-spends its budget later depends on the month it was set on, flipping in 9 of 18 variant-months. One of my own sanity checks failed, and the repo says so. Repo: [repo link]. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes to pick it apart?

Final (rewritten; 536 characters):

Hi Vasco, thanks for connecting. I ran a threshold study on the BAF suite. The result I trust most (post hoc): with the model held fixed, a 5% FPR threshold set on month 3 or 4 under-spends its budget in months 5 to 7, while one set on month 5 over-spends in 9 of its 12 later cells. One of my own sanity checks failed, and the repo says so. Repo: https://github.com/dudailia/baf-threshold-drift. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes to pick it apart?

## Francisco Souza e Silva (Feedzai)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| 89% of label-free alerts | results/values.json derived/Variant IV/label_free_top/alert_share_old_m67/max; reports/one_pager.md | 0.894 | QUALIFIED: months 6 and 7 only, label-free top 5%, about 89% |
| 51% of applications | results/values.json derived/Variant IV/application_share_old_m67/max | 0.506 | QUALIFIED: months 6 and 7 only |
| FPR ratio moved by at most 0.094 | results/values.json derived/ratio_spread_across_strategies/max; RESULTS.md line 573 | 0.0937 | MATCH |
| Recalibration holds the budget | results/values.json derived/delayed_lag1/miss_all/min, /max; RESULTS.md line 234 | -0.0209 to +0.0124 | MISMATCH: lag 1 swings -2.09 to +1.24 points and top 5% is under budget in every variant-month; rewritten |

Original (493 characters):

> Hi Francisco, thanks for connecting. One result from my BAF threshold study: in Variant IV the older age group received 89% of label-free alerts while making up 51% of applications, and switching between global threshold rules moved the age FPR ratio by at most 0.094. Recalibration holds the budget and leaves the group split where it was. Repo: [repo link]. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes this month?

Final (rewritten; 566 characters):

Hi Francisco, thanks for connecting. One result from my BAF threshold study: in Variant IV, months 6 and 7, the older age group received about 89% of label-free top 5% alerts while making up 51% of applications, and switching between global threshold rules moved the age FPR ratio by at most 0.094. Recalibration changes the budget miss and leaves the group split where it was. Repo: https://github.com/dudailia/baf-threshold-drift. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes this month?

## João David (Feedzai)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| monthly retraining raised detection | results_posthoc/values.json retrain/tpr_minus_lag1/min, /max; RESULTS_POSTHOC.md section 4 | -0.0067 to +0.0661 | MISMATCH: TPR against lag 1 ranges from -0.67 to +6.61 points, not always higher; rewritten with the range |
| higher realized FPR than lag 1 in 16 of 18 | results_posthoc/values.json retrain/vs_lag1/n_higher_fpr, retrain/vs_lag1/n | 16, 18 | MATCH (seed means) |
| correlated at 0.81 | results_posthoc/values.json retrain/vs_lag1/corr_tpr_gain_fpr_gain | 0.8106 | MATCH |
| gain at equal budget not established | RESULTS_POSTHOC.md section 4, Reading |  | MATCH; retraining is post hoc, now said |

Original (463 characters):

> Hi João, thanks for connecting. A result from my BAF threshold study that surprised me: monthly retraining raised detection, and it also ran at a higher realized FPR than lag-1 recalibration in 16 of 18 cells, with the two gains correlated at 0.81. At equal budget the gain is not established. Repo: [repo link]. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes to tell me what I'm missing?

Final (rewritten; 548 characters):

Hi João, thanks for connecting. A result from my BAF threshold study that surprised me: monthly retraining (post hoc) changed TPR by -0.67 to +6.61 points against lag-1 recalibration, but ran at a higher realized FPR in 16 of 18 variant-months, with the TPR and FPR differences correlated at 0.81. At equal budget the gain is not established. Repo: https://github.com/dudailia/baf-threshold-drift. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes to tell me what I'm missing?

## Inês Oliveira e Silva (Feedzai)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| top 5.75%, within 0.5 points in 24 of 24 | results_posthoc/values.json fixedq/top_5.75pct/n_within_0.5pt, fixedq/top_5.75pct/n | 24, 24 | MATCH; chosen post hoc, as the draft says |
| 5% FPR budget | PROTOCOL.md primary target | 0.05 | MATCH |
| isotonic matched it | results_posthoc/values.json isotonic/n_within_0.5pt, isotonic/n | 24, 24 | MATCH |
| added little | results_posthoc/values.json fixedq/isotonic/mean_abs_miss, fixedq/best_rule/mean_abs_miss, fixedq/top_5.5pct/iso_smaller, iso_larger, inconclusive | 0.0014 vs 0.0018; 9 / 9 / 6 | MATCH (paired comparison with the best fixed share is inconclusive) |

Original (492 characters):

> Hi Inês, thanks for connecting. A small result from my BAF threshold study: a rule that flags the top 5.75% of each month's applications (chosen post hoc) stayed within 0.5 points of a 5% FPR budget in 24 of 24 variant-months. Isotonic calibration matched it and added little. Most of that is arithmetic at BAF's fraud rate, and the write-up says so. Repo: [repo link]. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes?

Final (unchanged; 528 characters):

Hi Inês, thanks for connecting. A small result from my BAF threshold study: a rule that flags the top 5.75% of each month's applications (chosen post hoc) stayed within 0.5 points of a 5% FPR budget in 24 of 24 variant-months. Isotonic calibration matched it and added little. Most of that is arithmetic at BAF's fraud rate, and the write-up says so. Repo: https://github.com/dudailia/baf-threshold-drift. I'm looking for a Jan to Jun 2027 research co-op in Lisbon, with the right to work in Portugal. Would you have 20 minutes?

## Danielle Caled (Riskified)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| 5% FPR | PROTOCOL.md primary target | 0.05 | MATCH |
| last month's labels swung from -2.09 to +1.24 points | results/values.json derived/delayed_lag1/miss_all/min, /max; RESULTS.md line 234 | -0.0209, +0.0124 | MATCH |
| validation alert rate within 0.5 points in 22 of 24 | results/values.json derived/label_free_val_rate/absmiss_all/n_within_0.5pt, /n_cells; RESULTS.md line 230 | 22, 24 | MATCH |

Original (505 characters):

> Hi Danielle, thanks for connecting. Chargeback labels arrive late, so this result from my study on Feedzai's public BAF data may be relevant: recalibrating a 5% FPR threshold on last month's labels swung from -2.09 to +1.24 points around budget, while a label-free rule matching the validation alert rate stayed within 0.5 points in 22 of 24 variant-months. Repo: [repo link]. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 co-op in Lisbon. Would you have 20 minutes?

Final (unchanged; 541 characters):

Hi Danielle, thanks for connecting. Chargeback labels arrive late, so this result from my study on Feedzai's public BAF data may be relevant: recalibrating a 5% FPR threshold on last month's labels swung from -2.09 to +1.24 points around budget, while a label-free rule matching the validation alert rate stayed within 0.5 points in 22 of 24 variant-months. Repo: https://github.com/dudailia/baf-threshold-drift. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 co-op in Lisbon. Would you have 20 minutes?

## João Margato (Riskified)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| bias removed after month 5 | PROTOCOL.md, Variants (Sec 3.4 p7; variants notebook cells 18, 19) |  | MATCH (Variant V) |
| detection drops for every threshold strategy | results/values.json derived/Variant V/<strategy>/tpr_m45, tpr_m67 for static, label_free_top, label_free_val_rate, delayed_lag1, oracle | 0.726->0.300, 0.723->0.328, 0.753->0.356, 0.724->0.346, 0.751->0.336 | MATCH |
| the oracle included (75.1% to 33.6% TPR) | results/values.json derived/Variant V/oracle/tpr_m45, tpr_m67; RESULTS.md line 402 | 0.7506, 0.3359 | QUALIFIED: means of months 4 and 5 against months 6 and 7, at 5% FPR; CLAUDE.md requires the label Oracle (upper bound) and the FPR next to a TPR; rewritten |
| Recalibration can hold an alert budget | RESULTS.md line 234 |  | QUALIFIED: not every recalibration rule holds it; rewritten |

Original (477 characters):

> Hi João, thanks for connecting. One result from my study on Feedzai's public BAF fraud data: when the injected bias is removed after month 5, detection drops for every threshold strategy, the oracle included (75.1% to 33.6% TPR in Variant V). Recalibration can hold an alert budget. It can't repair a ranking that has gone stale. Repo: [repo link]. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 co-op in Lisbon. Would you have 20 minutes?

Final (rewritten; 569 characters):

Hi João, thanks for connecting. One result from my study on Feedzai's public BAF fraud data: in Variant V, when the injected bias is removed after month 5, TPR drops for every threshold strategy. The Oracle (upper bound) at 5% FPR falls from 75.1% TPR in months 4 and 5 to 33.6% in months 6 and 7. Recalibration moves the operating point; it can't repair a ranking that has gone stale. Repo: https://github.com/dudailia/baf-threshold-drift. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 co-op in Lisbon. Would you have 20 minutes?

## Pankaj Dhariwal (Hesper AI)

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| 5% FPR | PROTOCOL.md primary target | 0.05 | MATCH |
| under-spent by up to 2.32 points in later months | results/values.json derived/static/miss_m567/min | -0.0232 | QUALIFIED: threshold set on month 3, months 5 to 7 |
| over-spent by up to 5.82 when set on another month | results_posthoc/values.json rolling/A/static/miss_all/max | +0.0582 | QUALIFIED: post hoc split A, model trained on months 0 and 1, threshold on month 2 |
| A fixed alert share held budget far better | results/values.json derived/label_free_val_rate/absmiss_all/n_within_0.5pt; results_posthoc/values.json fixedq/top_5.75pct/n_within_0.5pt | 22 of 24; 24 of 24 (post hoc) | QUALIFIED: 'far better' is not a traced comparison; rewritten as the 22 of 24 count for the deployable rule |

Original (487 characters):

> Hi Pankaj, thanks for connecting. I recently finished a threshold study on Feedzai's public bank fraud data. Short version: a threshold set once at 5% FPR under-spent its budget by up to 2.32 points in later months, or over-spent by up to 5.82 when set on another month. A fixed alert share held budget far better. Repo: [repo link]. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 co-op. Would you have 20 minutes to tell me what Hesper is building?

Final (rewritten; 579 characters):

Hi Pankaj, thanks for connecting. I finished a threshold study on Feedzai's public bank fraud data. Short version: a threshold set at 5% FPR on month 3 under-spent by up to 2.32 points in months 5 to 7; post hoc, trained on months 0 and 1 and set on month 2, it over-spent by up to 5.82. Matching month 3's alert rate stayed within 0.5 points in 22 of 24 variant-months. Repo: https://github.com/dudailia/baf-threshold-drift. I'm a mathematics and business student at Northeastern looking for a Jan to Jun 2027 co-op. Would you have 20 minutes to tell me what Hesper is building?

## LinkedIn post

| Claim in draft | Source | Value | Mark |
|---|---|---|---|
| 5% false positive rate | PROTOCOL.md primary target | 0.05 | MATCH |
| set on month 3, under-spent by 0.87 to 2.32 points in months 5 to 7 | results/values.json derived/static/miss_m567/max, /min | -0.0087, -0.0232 | MATCH |
| set on month 2, over-spent by up to 5.82 | results_posthoc/values.json rolling/A/static/miss_all/max | +0.0582 | QUALIFIED: post hoc, model trained on months 0 and 1 |
| bootstrap intervals 0.23 to 0.32 points wide | results/values.json main/static_ci_width_m567/min, /max; RESULTS.md line 230 | 0.0023, 0.0032 | MATCH (seed 0 intervals for the month 3 static threshold, months 5 to 7); moved next to that result |
| 15 predictions | PREDICTIONS.md (12 answers plus A and B); results/predictions_scored.csv; values pred/n_total | 14 predictions, 15 scored lines | MISMATCH: 14 predictions, scored as 15 lines (prediction 2 has two parts); rewritten |
| 7 held | results/values.json pred/n_hit | 7 | MATCH (7 of 15 lines) |
| the repo explains why [the sanity check failed] | reports/one_pager.md Limits; RESULTS.md |  | MISMATCH: the cause is not established; rewritten as 'the repo reports it' |
| last week; Jesus et al., NeurIPS 2022 | commits 2026-10-16 to 2026-10-19; PROTOCOL.md sources |  | 'last week' removed; citation MATCH |

Original (596 characters):

> I spent the last week on a threshold study using Feedzai's public Bank Account Fraud dataset suite (Jesus et al., NeurIPS 2022). The question: if you set a fraud model's threshold once for a 5% false positive rate, does it stay on budget? On BAF it didn't. Set on month 3, it under-spent by 0.87 to 2.32 points in months 5 to 7. Set on month 2, it over-spent by up to 5.82. Bootstrap intervals were 0.23 to 0.32 points wide. I wrote down 15 predictions before training anything. 7 held. One of my own sanity checks failed, and the repo explains why. Code, data audit and every number: [repo link]

Final (rewritten; 599 characters):

I ran a threshold study on Feedzai's public Bank Account Fraud suite (Jesus et al., NeurIPS 2022). Does a fraud threshold set once at a 5% false positive rate stay on budget? On BAF it didn't. Set on month 3, it under-spent by 0.87 to 2.32 points in months 5 to 7 (bootstrap intervals 0.23 to 0.32 points wide). Post hoc, trained on months 0 and 1 and set on month 2, it over-spent by up to 5.82. I wrote down 14 predictions before training anything, scored as 15 lines; 7 held. One sanity check failed, and the repo reports it. Code and every number: https://github.com/dudailia/baf-threshold-drift
