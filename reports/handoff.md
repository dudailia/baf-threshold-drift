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
