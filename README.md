# Threshold drift on the BAF dataset suite
On the BAF suite (six variants from one generator), a LightGBM threshold set once at 5% FPR misses its budget in later months, and the direction depends on the validation month: set on month 3 it under-spends by 0.87 to 2.32 points of FPR in months 5 to 7 (seed 0 95% intervals 0.23 to 0.32 points wide), and post hoc, trained on months 0 and 1 and set on month 2, it over-spends (amendment in RESULTS.md).
With the threshold month at 3, re-targeting each month to the validation month's alert rate, without labels, stays within 0.5 points of 5% in 22 of 24 variant-months; the global-threshold strategies differ in age-group FPR ratio by at most 0.094 in any variant-month, and the shuffled-label sanity check failed its declared tolerance (a caveat, see RESULTS.md).

This is a small study on Feedzai's public Bank Account Fraud suite (Jesus et al., NeurIPS 2022, arXiv 2211.13358). It asks how far realized FPR, TPR and alert volume drift after a threshold is set once at 5% FPR, how unevenly that falls across age groups, and which recalibration strategy keeps the alert budget on target: static, label-free (top 5% of each month, or the validation month's alert rate), delayed-label (lags 1 to 3) and an oracle that is an upper bound, not deployable.

## Files

| File | Content |
|---|---|
| PROTOCOL.md | The paper's protocol, confirmed against the paper and repo, and every choice made here, with the decision log |
| PREDICTIONS.md | Predictions written before any model was run; never edited |
| RESULTS.md | Tables and figures, one line of interpretation each, and the scored predictions |
| reports/one_pager.md | One page: question, setup, findings, limits |
| reports/data_audit.md | Row counts, fraud rate by month, sentinels, age definitions against Table 1, split overlap |
| reports/related_work.md | Work on BAF and on threshold drift, each source opened when the review was written |
| reports/mechanism.md | Synthetic mechanism study (synthetic, not BAF) |
| reports/progress.md, reports/handoff.md | Timestamped log of the run and the current state |
| src/, tests/ | Code and unit tests |
| results/ | Every number, stamped with the predictions commit |
| figures/ | Realized FPR, TPR and FPR ratio by month, ROC operating points |

## Reproduce

Put the six CSV files from the Kaggle page linked in the BAF repository (`Base.csv`, `Variant I.csv` to `Variant V.csv`) in `data/raw/`, then:

```
make setup   # creates .venv and installs the pinned requirements.txt
make all     # tests, audit, checks, training, evaluation, figures, tables and the number check
```

`make train` and `make evaluate` refuse to run unless PREDICTIONS.md is committed and unchanged. Long steps checkpoint per variant, model and seed under `results/checkpoints/` and resume if interrupted. `make all` rewrites RESULTS.md, README.md and the one-pager from `docs/*.template.md` and fails if any number in them does not trace to `results/`. `data/` is in .gitignore, so data are not committed (reports/hygiene.md).
