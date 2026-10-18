# Threshold drift on the BAF dataset suite
On the BAF suite (six variants from one generator), a LightGBM threshold set once at 5% FPR misses its budget in months 5 to 7, and the direction depends on the validation month: set on month 3 it under-spends by {{value:derived/static/miss_m567/max|apt2}} to {{value:derived/static/miss_m567/min|apt2}} points of FPR (seed 0 95% intervals {{value:main/static_ci_width_m567/min|apt2}} to {{value:main/static_ci_width_m567/max|apt2}} points wide), and post hoc, trained on months 0 and 1 and set on month 2, it over-spends.
Biggest caveat: the shuffled-label sanity check failed its declared tolerance (pooled TPR {{value:check/shuffled/4-7 pooled/oracle_tpr|f3}} at 5% FPR, against 0.05 plus or minus 0.02) with no leak found and the cause not established, and BAF is synthetic, so month-to-month shifts may reflect the generator rather than applicant behaviour.

This is a small study on Feedzai's public Bank Account Fraud suite (Jesus et al., NeurIPS 2022, arXiv 2211.13358). It asks how far realized FPR, TPR and alert volume drift after a threshold is set once at 5% FPR, how unevenly that falls across age groups, and which recalibration strategy keeps the alert budget on target: static, label-free (top 5% of each month, or the validation month's alert rate), delayed-label (lags 1 to 3) and an oracle that is an upper bound, not deployable. With the threshold month at 3, re-targeting to the validation month's alert rate stays within 0.5 points of 5% in {{value:derived/label_free_val_rate/absmiss_all/n_within_0.5pt|int}} of {{value:derived/label_free_val_rate/absmiss_all/n_cells|int}} variant-months, and the global-threshold strategies differ in age-group FPR ratio by at most {{value:derived/ratio_spread_across_strategies/max|f3}} in any variant-month. RESULTS.md opens with an amendment that corrects the original "under-spends" claim.

## Data

The data are not in this repository. Download the BAF suite from Kaggle, dataset `sgpjesus/bank-account-fraud-dataset-neurips-2022` (linked from github.com/feedzai/bank-account-fraud), under its license (`CC BY-NC-ND 4.0`, datasheet). Unzip it and put these six files, with exactly these names, in `data/raw/`:

```
data/raw/Base.csv
data/raw/Variant I.csv
data/raw/Variant II.csv
data/raw/Variant III.csv
data/raw/Variant IV.csv
data/raw/Variant V.csv
```

With the Kaggle command line and a token in `~/.kaggle/kaggle.json`: `kaggle datasets download -d sgpjesus/bank-account-fraud-dataset-neurips-2022 -p data/raw --unzip`. Each file has 1,000,000 rows; `make audit` checks the names, row counts, months and columns and stops if anything is off. `data/` is in .gitignore, so data are not committed (reports/hygiene.md).

## Reproduce

```
make setup   # creates .venv and installs the pinned requirements.txt
make all     # tests, audit, checks, training, evaluation, figures, tables and the number check
```

`make train` and `make evaluate` refuse to run unless PREDICTIONS.md is committed and unchanged. Long steps checkpoint per variant, model and seed under `results/checkpoints/` and resume if interrupted. `make all` rewrites RESULTS.md, README.md and the one-pager from `docs/*.template.md` and fails if any number in them does not trace to `results/`. A clean rebuild takes about an hour (reports/reproducibility.md).

## Reviewing

See [REVIEWING.md](REVIEWING.md) for a ten-minute check (pre-registration, the tripwire that fired, main versus post hoc files, rebuild commands) and [reports/deviations.md](reports/deviations.md) for every departure from the brief and the paper.

## Files

| File | Content |
|---|---|
| PROTOCOL.md | The paper's protocol, confirmed against the paper and repo, and every choice made here, with the decision log |
| PREDICTIONS.md | Predictions written before any model was run; never edited |
| RESULTS.md | Main results, one line of interpretation per table or figure, the scored predictions, and the amendment |
| RESULTS_POSTHOC.md | Post hoc analyses, declared after the main results |
| reports/one_pager.md, reports/one_pager.pdf | One page: question, setup, findings, limits |
| REVIEWING.md, reports/deviations.md | How to check the work; departures from the brief and the paper |
| reports/data_audit.md | Row counts, fraud rate by month, sentinels, age definitions against Table 1, split overlap |
| reports/related_work.md | Work on BAF and on threshold drift, each source opened when the review was written |
| reports/mechanism.md | Synthetic mechanism study (synthetic, not BAF) |
| reports/decisions.md, reports/progress.md, reports/handoff.md | Choices made without the user, timestamped log, current state |
| src/, tests/ | Code and unit tests |
| results/, results_posthoc/ | Every number, stamped with the predictions commit |
| figures/ | Realized FPR, TPR and FPR ratio by month, ROC operating points |

## License

Code and documents: MIT (LICENSE). The BAF data are not included and remain under their own license.
