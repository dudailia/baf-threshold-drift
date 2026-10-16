# Progress log

| Date | Stage | Entry |
|---|---|---|
| 2026-10-16 | 0 | PROTOCOL.md written from arXiv v2, repo commit 3377cfd, datasheet and notebooks. |
| 2026-10-16 | 0 | Threshold, metric, data and audit code with 26 unit tests. No data accessed. |
| 2026-10-16 | 1 | Interview revised by the user: budget miss is the primary comparison. PROTOCOL.md gains the budget miss metric, the TPR-with-FPR and oracle reporting rules, and figures/roc_operating_points.png. No data accessed. Waiting for answers to the revised interview. |
| 2026-10-16 | 1 | Fact check of Variant IV and V generation code (notebook cells 7 to 9, 17 to 19; mvn.py) reported to the user. PREDICTIONS.md not written: waiting for the user to confirm the answers as final. |
| 2026-10-16 | queue 4 | PROTOCOL.md: pre-declared secondary analyses (age definition, LR vs LightGBM, FPR targets 1/2/10% exploratory, lags 2 and 3). No data accessed. |
| 2026-10-16 | queue 2 | Synthetic mechanism study (src/synthetic.py, 8 tests, reports/mechanism.md, figures/synthetic_mechanism.png). Synthetic, not BAF. FPR identity holds to 1.4e-17. No data accessed. |
| 2026-10-16 | queue 3 | Traceability tooling: src/trace.py (render from docs/*.template.md, number checker, fresh-render diff), src/tables.py (format-only tables from results/summary, ci, paired, metrics), src/schema.py, src/figures.py (roc_operating_points). 26 new tests on fake results. make tables and make check added to make all. PROTOCOL.md: 'overlap heavily' defined as at least 50% of the shorter interval. No data accessed. |
| 2026-10-16 | queue 1 | reports/related_work.md: 30 verified items, 4 not verified. No prior work measures monthly threshold drift or compares recalibration strategies on BAF; closest is Pombal et al. 2022 (private data, simulated label noise). Spot-checked 8 URLs and the Pombal et al. full text. LibKey connector not authenticated, so not used. No data accessed. |
| 2026-10-16 18:30 | A | Corrected Pombal et al. (2206.13183) in related_work.md from a re-read of Sec 4.1 to 4.3: non-public data, drift from selective labels in a retraining loop, strategies compared (global, group-wise, retrain each window, drop old data). Verdict rewritten; added a paragraph on how this study differs. (elapsed 0m56s) |
| 2026-10-16 18:30 | B | PROTOCOL.md: exploratory secondary strategies (v) group-wise static and (vi) group-wise label-free, diagnostics only. No data accessed. (elapsed 0m11s) |
| 2026-10-16 18:31 | C | PREDICTIONS.md committed verbatim as 0be4b0d ('Pre-register predictions'). src/guard.py (4 tests) wired into make train and make evaluate; results writers will stamp the hash. (elapsed 1m02s) |
