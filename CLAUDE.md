# Project rules for baf-threshold-study

Research project on Feedzai's Bank Account Fraud (BAF) suite: drift of a threshold set once at 5% FPR, and recalibration strategies. Readers are Feedzai research scientists. Rigor beats breadth. A short correct result beats a long impressive one.

Read PROTOCOL.md before changing any split, metric, group definition or threshold rule.

## Leakage rules

- Splits are by month only. A row belongs to exactly one split. The split months are defined in PROTOCOL.md and in one place in `src/`.
- Preprocessing (encoders, scalers, imputation medians, category lists, sentinel handling statistics) is fit on training months only, then applied unchanged to validation and test months.
- Hyperparameter tuning uses the validation month only. Test months never enter training, encoding, tuning or model selection.
- A threshold strategy may only use data that would exist at deployment time for that month. Static uses the validation month. Label-free uses the current month's scores and no labels. Delayed-label with lag k uses labelled scores from month m minus k, and only if that month is not a training month (in-sample scores are not allowed as a threshold source).
- The `month` column is not a model feature in the main study (see PROTOCOL.md for the reason and the replication exception).
- The shuffled-label check must give TPR close to 5% at 5% FPR. If it does not, stop and find the leak before reporting anything.
- Data never goes into git. `data/` is in .gitignore.

## Oracle labelling rule

- The oracle strategy sets the threshold on the test month's own labels. It is an upper bound, never a deployable method.
- Every table, figure legend, file and sentence that mentions it calls it "Oracle (upper bound, not deployable)" or, where space is tight, "Oracle (upper bound)".
- Never rank the oracle alongside deployable strategies as if it were a candidate, and never describe a deployable strategy as "matching" or "beating" the oracle without the interval evidence.

## Reporting rules

- Every number in RESULTS.md, README.md and reports/one_pager.md comes from a run executed in the current session, produced by `make all`. If something did not run, say so. Never estimate, extrapolate or round up.
- Numbers from the 10% sample are pipeline checks only. Do not interpret them in any file.
- Report seed spread (across 5 seeds) and bootstrap 95% intervals (1,000 resamples of applications within a month) separately. Never merge them into one interval.
- If intervals overlap heavily, or the paired-bootstrap interval of a difference contains 0, call the difference inconclusive.
- For every month and age group, record positive and negative counts. Flag cells with fewer than 30 positives and never report a TPR for such a cell without its interval.
- Budget miss (realized FPR - 5%, signed and absolute) is the primary comparison between strategies. TPR is never shown without the realized FPR next to it, because all strategies sit on the same month's ROC curve and an overshoot buys TPR.
- The oracle row is always shown and labelled as an upper bound.
- No claims of beating the paper or of state of the art. Report null and negative results.
- PREDICTIONS.md is written from the user's own predictions, committed before any modelling run, and never edited afterwards.

## Writing rules

- Plain language. No em dashes. No hype words: robust, novel, groundbreaking, leverage, seamless (and similar).
- No bold-label bullet stacks.
- One line of interpretation per table or figure in RESULTS.md.
- README.md puts the headline result in its first three lines.

## Working rules

- Code is written from scratch for this project. Do not copy code from the user's other projects.
- Pin package versions in requirements.txt. `make all` rebuilds every number and figure from `data/raw/`.
- Commit after each working stage with a clear message.
