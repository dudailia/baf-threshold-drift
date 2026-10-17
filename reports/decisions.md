# Decisions for the post hoc queue

Choices made without asking, during the unattended post hoc queue (PROTOCOL.md, "Post hoc analyses"). Where a choice was ambiguous, the more conservative option was taken.

| Task | Decision | Reason |
|---|---|---|
| all | Main-study code is reused; new parameters default to the main-study values, and no main-study command (`make train`, `make evaluate`, `make values`) is run, so results/ is not rewritten. | A change to any main-study result file is a hard stop. |
| all | Paired bootstrap resamples use the same weight keys as the main study (variant, month, chunk), so post hoc and main strategies are evaluated on the same resampled rows of a month. | Makes post hoc against main comparisons paired, as in the main study. |
| all | Primary settings as in the main study: 5% target, older group `customer_age >= 50`, 1,000 resamples, seed 0 intervals, verdict rule from PROTOCOL.md. | Same intervals as the main study, as asked. |
| 1 | Same 20 configurations (seed 2022) as the main study, tuned on each split's validation month by TPR at 5% FPR; 5 seeds; intervals for seed 0 only, seed spread from all 5. | Same tuning budget and intervals as the main study, as asked. |
| 1 | All strategies are computed, but only static, label-free top 5%, delayed-label lag 1 and the oracle are stored and reported. | Exactly the strategies named in the task. |
| 1 | "Later months" is read as months 5 to 7, the months where the main study found the under-spend; split A's months 3 and 4 are reported too. | Keeps the robustness question identical to the main finding and hides nothing. |
| 2 | LightGBM seed 0 of the main study. The model is refit (same data, configuration and seed) because models were not saved; the refit is checked against the saved scores and the difference is reported. | Predictions alone cannot be rescored with replaced features. |
| 2 | Five independent replacement draws per feature and month, mean and range reported; raw values (including sentinels) are drawn, then preprocessed as in training. One feature is replaced at a time; joint effects are not tested. | Single draws are noisy; joint replacement was not asked for. |
| 3 | Top 5 tuning trials by validation TPR (ties to the earlier trial); rank 1 reuses the main study's saved predictions. Strongly regularised model: 200 trees, depth 3, 8 leaves, at least 2,000 rows per leaf, learning rate 0.05, GBDT. 5 seeds each; seed 0 intervals and a paired comparison against the main model. | Rank 1 is the main model by construction; the regularised setting is far from every tuned configuration. |
| 4 | 5 seeds, each with the main study's configuration for that variant (identical across seeds). The retrained threshold is set on month t-1 with that month's labels, the same information as delayed-label lag 1. | No re-tuning, as asked. |
| 5 | Isotonic regression clipped to [0, 1]; in the bootstrap, month 3 is resampled and the isotonic map refitted in every resample. | Includes calibration uncertainty in the intervals. |
