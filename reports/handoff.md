# Handoff note

Last updated 2026-10-16, after Stage K (write-up); waiting for the user's review. Read CLAUDE.md, PROTOCOL.md and this file before continuing. The running log with timestamps is reports/progress.md.

## State

| Stage | Status | Where |
|---|---|---|
| 0 Protocol | done | PROTOCOL.md (a2b9b31, then amended through the decision log) |
| A Related work | done | reports/related_work.md (c1b553f) |
| B Group-wise strategies declared | done | PROTOCOL.md (30f88f9) |
| C Predictions pre-registered | done, never edit | PREDICTIONS.md (0be4b0d); guard src/guard.py (a4169f9) |
| Pipeline code | done, tested on synthetic fixture only | src/ (c370195) |
| D Data | done | data/raw/: Base.csv, Variant I.csv to Variant V.csv; mapped in src/data.py |
| E Audit | done, no tripwires | reports/data_audit.md, results/audit.json (11f2b3d) |
| Scoring rules for predictions | done, declared before results | PROTOCOL.md, src/predictions_eval.py (290a3c0) |
| F Replication | done, within loose bound | results/replication.csv (6d0ce24) |
| F Shuffled-label check | FAILED, tripwire fired, kept as a caveat | results/shuffled.csv, results/tripwires.json (6d0ce24) |
| F PSI (Base, check model) | done | results/psi.csv (recomputed for all variants with tuned models after H) |
| F post hoc diagnostics | done | src/diagnostics.py, tests/test_fit_on_train_only.py (3fa2ccf) |
| G 10% sample | done, clean | results/sample_run/ (gitignored; never interpreted) |
| H Full run | done, no evaluation tripwires | results/*.csv, figures/ (9c04644) |
| I Independent check | done, 0 mismatches | results/independent_check.csv, reports/independent_check/ (4d640ce, 5d0954c) |
| J Secondary analyses | done, only pre-declared ones | RESULTS.md section 8 |
| K Write-up | done | README.md, RESULTS.md, reports/one_pager.md from docs/*.template.md; `make check` passes |

## Decisions in force

- Main split: train 0 to 2, validation 3, test 4 to 7 (my choice, approved). `month` excluded in the main study.
- Older group `customer_age >= 50` primary (audit: 1.24 pt from Table 1 group sizes vs 30.66 for `> 50`); `> 50` is the sensitivity analysis.
- Budget miss (realized FPR - 5%) is the primary comparison; TPR never shown without realized FPR; the oracle is always shown and labelled an upper bound, not deployable.
- 20 LightGBM tuning configurations (seed 2022), 5 seeds, 1,000 paired bootstrap resamples for the 5% target. Fits took 1 to 21 s on 750k rows, so no shrinking of trials was needed so far.
- Shuffled-label check: FAILED against its declared tolerance; the criterion is not redefined (user decision). Diagnostics found no leak; the null was wrong because fraud applications are atypical. State this as a caveat in RESULTS.md and the one-pager.

## Open tripwires

- shuffled-label (Stage F): fired, accepted by the user as a caveat. All other tripwires so far: none fired.

## Next step

Wait for the user's review of README.md, RESULTS.md and reports/one_pager.md. To change prose, edit docs/*.template.md and run `make tables check`; never edit the rendered files or PREDICTIONS.md.

## Post hoc queue (overnight, started 2026-10-16 after commit 125042c)

Everything here is post hoc (PROTOCOL.md, "Post hoc analyses"). Outputs: results_posthoc/ and RESULTS_POSTHOC.md (rendered from docs/RESULTS_POSTHOC.template.md by `python -m src.trace render`). Decisions: reports/decisions.md. Never touch results/, PREDICTIONS.md or the scoring rules (hard stops).

| Task | Status | Code | Outputs |
|---|---|---|---|
| setup | done (25e8629) | PROTOCOL.md section, reports/decisions.md | |
| 1 rolling-origin | done | src/posthoc/rolling.py | rolling_*.csv. Split A (validate on month 2): static OVER budget in all 18 cells of months 5-7 (CI above 0), contradicting the main under-spend; split B (validate on month 4): under budget in 18 of 18, as in the main study. |
| 2 mechanism | done | src/posthoc/mechanism.py | mechanism_*.csv. Refit exact. KS small; replacing any single top-10 feature with month-3 draws does not shrink the static miss except phone_home_valid slightly; credit_risk_score replacement does not shrink it (weakens a main RESULTS.md 'consistent with' sentence). |
| 3 hyperparameters | done | src/posthoc/hyper.py | hyper_*.csv. Static miss in months 5-7 negative for every configuration (0 sign changes in 90 cells); size -0.35 to -2.16 pt; 3 sign changes in month 4 only. |
| 4 retraining | done | src/posthoc/retrain.py | retrain_*.csv. Miss -1.97 to +1.76 pt (5 of 18 within 0.5 pt); validation-rate label-free smaller absolute miss in 13 of 18; TPR vs lag 1 -0.7 to +6.6 pt. |
| 5 isotonic | done | src/posthoc/isotonic.py | isotonic_*.csv. Within 0.5 pt in 24 of 24 variant-months (miss -0.36 to +0.16); smaller absolute miss than top 5% in 24/24, than static in 19, vs validation rate 9 smaller / 9 larger / 6 inconclusive. |
| 6 call prep | done | docs/call_questions.template.md | prep/call_questions.md (rendered and checked by src/trace.py) |
| 7 independent check | done, 0 mismatches in 1,890 rows | reports/independent_check_posthoc/check.py | results_posthoc/independent_check.csv |

Post hoc findings that contradict the main study so far: the sign of the static miss depends on the validation month (task 1, split A); credit_risk_score drift alone does not explain the static miss (task 2), against the main RESULTS.md PSI sentence. Not a contradiction but an extension: isotonic label-free targeting (task 5) holds the budget in 24 of 24 variant-months.

Hard stops fired: none. Verified: no change since 125042c to results/, RESULTS.md, README.md, reports/one_pager.md, PREDICTIONS.md, their templates or src/predictions_eval.py; PROTOCOL.md only appended.

Queue finished. Next step: the user's review of RESULTS_POSTHOC.md section 7 and a decision on whether to reword the main documents' 'under-spends' statement (left unchanged on purpose).

## Revision queue (2026-10-17, authorized prose rewording)

| Step | Status | Notes |
|---|---|---|
| 1 amendment | amendment in RESULTS.md, README headline reworded, credit_risk_score sentence reworded; one-pager reworded in step 6 | originals quoted in the amendment; git history at 125042c |
| 2 validation month (post hoc 6) | done | RESULTS_POSTHOC.md section 8: with the model fixed, the sign depends on the threshold month in 9 of 18 cells; month 5 thresholds over-spend |
| 3 isotonic control (post hoc 7) | done | RESULTS_POSTHOC.md section 7: fixed top 5.75% within 0.5 pt in 24 of 24; most of the isotonic result is the FPR identity |
| 4 clean rebuild | to do, after text is final | make clean, make all |
| 5 claims audit | to do | fresh subagent |
| 6 one-pager | to do | |
| 7 hygiene | done | reports/hygiene.md: personal email in commit metadata (all commits), absolute paths in the verbatim checker scripts; no credentials, IDs, phone numbers, data or other-project references |
