# Pre-registered predictions

Written by Ilia Duda before any data file was opened and before any model was run. Recorded word for word as supplied on 2026-10-16. This file is not edited after its first commit.

Interview questions (asked by the assistant; the answers below are the user's own words):

1. (a1) Base and Variants I to III: how far apart will the strategies be on TPR? Number range and confidence (50 to 90%).
2. (a2) Base and Variants I to III: how far apart will the strategies be on static realized FPR? Number range and confidence.
3. (b1) Variant IV: static realized FPR in months 6 and 7 versus months 4 and 5: which way, how much? Confidence?
4. Variant IV, months 6 and 7: which deployable strategy (static, label-free, delayed-label lag 1) has the largest budget miss, |realized FPR - 5%|, and which has the smallest? Confidence?
5. Variant IV, months 6 and 7: which of the three has the highest TPR, and is that because it stays on budget or because it overshoots? Confidence?
6. (b4) Variant IV: does the age FPR ratio under the static threshold rise or fall after month 5? Confidence?
7. Variant IV, months 6 and 7: under label-free, is the age FPR ratio closer to 1 or further from 1 than under static, and which age group gets a larger share of alerts than its share of applications? Confidence?
8. (b5) Variant V: static realized FPR in months 6 and 7 versus months 4 and 5: which way, how much? Confidence?
9. Variant V, months 6 and 7: largest and smallest budget miss among the three deployable strategies? Confidence?
10. Variant V, months 6 and 7: highest TPR among the three, and is that because it stays on budget or because it overshoots? Confidence?
11. (b8) Variant V: does the age FPR ratio under the static threshold rise or fall after month 5? Confidence?
12. Variant V, months 6 and 7: under label-free, age FPR ratio closer to or further from 1 than under static, and which age group gets a larger share of alerts than its share of applications? Confidence?

## Answers

1. Base and Variants I to III, TPR: in every test month, the three deployable strategies are within 4 points of each other on TPR. 60%.
2. Base and Variants I to III, static realized FPR: stays between 4% and 6% in every test month. No view on direction. 65%. Label-free realized FPR is below 5% in every test month, by 0.2 to 0.8 points. 85%.
3. Variant IV, static realized FPR: months 6 and 7 differ from months 4 and 5 by less than 0.5 points. 65%.
4. Variant IV budget miss: largest is label-free, under budget by about 0.5 to 1 point. Smallest is static or delayed-label. 55%.
5. Variant IV TPR: highest is static or delayed-label, because they sit closer to or above 5% FPR. 60%.
6. Variant IV static age FPR ratio: changes by less than 0.05 after month 5. 60%.
7. Variant IV label-free fairness: the age FPR ratio is within 0.05 of static, and the higher-prevalence group gets at least 65% of alerts. 60%.
8. Variant V, static realized FPR: months 6 and 7 differ from months 4 and 5 by less than 0.5 points. 50%.
9. Variant V budget miss: largest is label-free, under budget by about 0.5 to 1 point. Smallest is static or delayed-label. 50%.
10. Variant V TPR: highest is static or delayed-label, because they sit closer to or above 5% FPR. 55%.
11. Variant V static age FPR ratio: changes by less than 0.05 after month 5. 50%.
12. Variant V label-free fairness: the age FPR ratio is within 0.05 of static, and the higher-prevalence group gets at least 65% of alerts. 55%.

## Additional predictions

A. Variant IV: every strategy loses TPR from months 4-5 to months 6-7, by more than any gap between strategies. 70%.
B. Variant V: every strategy loses TPR from months 4-5 to months 6-7, by more than any gap between strategies. 65%.
