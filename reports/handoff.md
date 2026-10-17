# Handoff note

Last updated 2026-10-16, during Stage F to G of the unattended pass. Read CLAUDE.md, PROTOCOL.md and this file before continuing. The running log with timestamps is reports/progress.md.

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
| F post hoc diagnostics | in progress | src/diagnostics.py, tests/test_fit_on_train_only.py |
| G 10% sample | next | `make sample` writes to results/sample_run/ (gitignored); never interpret |
| H Full run | to do | `make train`, `make evaluate` in background; logs in results/logs/; checkpoints in results/checkpoints/ |
| I Independent check | to do | prompt ready in the scratchpad (independent_check_prompt.md); fresh subagent recomputes from results/predictions/ |
| J Secondary analyses | to do | only those declared in PROTOCOL.md; anything else marked post hoc |
| K Write-up | to do | docs/*.template.md rendered by `make tables`, checked by `make check` |

## Decisions in force

- Main split: train 0 to 2, validation 3, test 4 to 7 (my choice, approved). `month` excluded in the main study.
- Older group `customer_age >= 50` primary (audit: 1.24 pt from Table 1 group sizes vs 30.66 for `> 50`); `> 50` is the sensitivity analysis.
- Budget miss (realized FPR - 5%) is the primary comparison; TPR never shown without realized FPR; the oracle is always shown and labelled an upper bound, not deployable.
- 20 LightGBM tuning configurations (seed 2022), 5 seeds, 1,000 paired bootstrap resamples for the 5% target. Fits took 1 to 21 s on 750k rows, so no shrinking of trials was needed so far.
- Shuffled-label check: FAILED against its declared tolerance; the criterion is not redefined (user decision). Diagnostics found no leak; the null was wrong because fraud applications are atypical. State this as a caveat in RESULTS.md and the one-pager.

## Open tripwires

- shuffled-label (Stage F): fired, accepted by the user as a caveat. All other tripwires so far: none fired.

## Next step

Finish the post hoc diagnostics, commit, then run Stage G (`make sample`), check for failed tests, NaN in available rows and missing strategies, then Stage H in the background.
