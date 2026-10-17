# Reproducibility check

Run on 2026-10-17: `make clean`, then `make all` from `data/raw/` with no checkpoints, predictions or results left from earlier runs. `make clean` kept only `data/`, `results/independent_check.csv` (an external audit record that `make all` does not produce) and `results_posthoc/` (post hoc analyses, not part of `make all`).

Wall time of `make all`: 3,656 seconds (about 61 minutes), started 14:39:13 and finished 15:40:09, exit code 0. All 103 tests passed, the audit fired no tripwire, the shuffled-label check fired its known tripwire (recorded and accepted, PROTOCOL.md decision log), evaluation fired none, and `make check` passed for all five rendered documents.

Comparison of every regenerated file with the committed version (`git status` after the rebuild):

| File | Difference | Kind |
|---|---|---|
| results/manifest.json | the `generated` timestamp | metadata |
| results/tripwires.json | the order of two keys (`psi`, `evaluation`); same contents | metadata |
| results/replication_trials.csv | the `fit_seconds` column only (wall-clock fit times, largest change about 75 seconds); every TPR, FPR and ratio value is identical | timing |
| every other file in results/, figures/, reports/data_audit.md, reports/mechanism.md, RESULTS.md, README.md, reports/one_pager.md, RESULTS_POSTHOC.md, prep/call_questions.md | none (byte-identical) | |

No result changed. The three files above were restored to their committed versions after the comparison, so that `results/` stays as committed. The post hoc results in `results_posthoc/` were computed from the earlier predictions; since every main result regenerated identically, they were not rerun.

## Fresh-clone test (2026-10-17)

The repository was cloned at commit ebd72dc into a new, empty folder, `data/raw` was symlinked from the original checkout, and a new virtual environment was built from requirements.txt alone. In the clone: `make test` passed (103 tests), `make audit` fired no tripwire, and `make sample` (the 10% stratified Base pipeline) completed with no evaluation tripwire. The clone's reports/data_audit.md and results/audit.json are byte-identical to the committed ones, and the clone's working tree stayed clean (the sample outputs go to the ignored results/sample_run/). Nothing failed because a file was untracked or ignored, so no fix was needed.
