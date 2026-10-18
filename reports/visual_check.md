# Visual check of figures and the one-page PDF

Done 2026-10-18. Every file in figures/ and reports/one_pager.pdf was rendered to an image and inspected. Checks: legibility at page width, axis labels and units, the oracle labelled as an upper bound wherever it appears, no TPR without its realized FPR, and the PDF on one page with nothing cut off.

## Findings and fixes

| File | Problem found | Fix |
|---|---|---|
| realized_fpr_by_month.png, fpr_ratio_by_month.png | Six panels in one row, 18.6 inches wide. At page width the 9 pt text shrinks to about a third and is unreadable. | Three columns, two rows (src/report_figures.py). |
| tpr_by_month.png | Same width problem, 2 by 6 panels. | Three columns; each variant has its realized FPR panel directly above its TPR panel; shared y scale per metric. |
| all three by-month figures | In month 4, delayed-label lag 1 uses month 3 and equals static, so its diamond hides the static circle; a reader can think static is missing. Bootstrap bars are mostly shorter than the markers, which the title did not say. | Both stated in the figure title. |
| fpr_ratio_by_month.png | Title did not say which age definition, or which direction is fair. | Title names `customer_age >= 50` and says 1 means equal group FPRs. |
| roc_operating_points.png | Seven crowded x tick labels (0.000 to 0.150); axes "FPR" and "TPR" without units, while the other figures use percent; legend wrapped one entry onto its own line. | Ticks every 0.05; axes say "share of negatives" and "share of positives"; legend in three columns; title notes the dotted 5% line and the month 4 overlap. |
| reports/one_pager.pdf | One letter page, all 550 words of reports/one_pager.md present, nothing cut off. The oracle is labelled "an upper bound, not deployable". The shuffled-label sentence gave "pooled TPR 0.117" without its FPR. | Changed to "pooled TPR 0.117 at 5% FPR" in docs/one_pager.template.md, and the same words in the README and call-prep templates; rendered with `make tables`, PDF rebuilt with `make pdf`, still one page. |
| synthetic_mechanism.png | No problem found: realized FPR row above the TPR row, oracle labelled, "Synthetic, not BAF" in the title, units in percent. | None. |

The oracle is labelled "Oracle (upper bound, not deployable)" in every figure legend, and every figure that shows TPR shows realized FPR beside it (the TPR figure in the panel above, the ROC figure on the x axis).

## Numbers unchanged

Before editing, the plotting code was run with `savefig` patched to dump every plotted series (line x and y values, error-bar segments, labels, colours) to JSON; that run reproduced the committed PNGs byte for byte. After the edits the same dump was taken. The JSON files of all four regenerated figures are byte-identical before and after, so only layout and labels changed. `git status` shows no change under results/ or results_posthoc/, and `make check` passes. RESULTS.md and RESULTS_POSTHOC.md are byte-identical after `make tables`; README.md, reports/one_pager.md and prep/call_questions.md differ only by the added words "at 5% FPR".
