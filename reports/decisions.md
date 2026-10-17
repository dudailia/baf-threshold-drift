# Decisions for the post hoc queue

Choices made without asking, during the unattended post hoc queue (PROTOCOL.md, "Post hoc analyses"). Where a choice was ambiguous, the more conservative option was taken.

| Task | Decision | Reason |
|---|---|---|
| all | Main-study code is reused; new parameters default to the main-study values, and no main-study command (`make train`, `make evaluate`, `make values`) is run, so results/ is not rewritten. | A change to any main-study result file is a hard stop. |
| all | Paired bootstrap resamples use the same weight keys as the main study (variant, month, chunk), so post hoc and main strategies are evaluated on the same resampled rows of a month. | Makes post hoc against main comparisons paired, as in the main study. |
| all | Primary settings as in the main study: 5% target, older group `customer_age >= 50`, 1,000 resamples, seed 0 intervals, verdict rule from PROTOCOL.md. | Same intervals as the main study, as asked. |
