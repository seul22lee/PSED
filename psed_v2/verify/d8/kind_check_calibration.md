# Kind-check and number-check calibration (P102, P103)

Kind check: 30 synthetic sentences, 42 cited ids (21 wrong kinds, 21 right); mismatch flag: TP 21, FP 0, FN 0, TN 21; precision 1.00, recall 1.00.
Battery value lines carrying a kind phrase, each cited by its own id (other ids and the paper's statement removed): 643 lines, 638 citations checked, 2 mismatches (stated -> record: cited -> stated: 2).

| sentence | id | kind | result |
|---|---|---|---|
| The value was measured by XPS [yim20:s10.p1#2]. | yim20:s10.p1#2 | right | passed |
| The value was computed by this knowledge base [yim20:s10.p1#2]. | yim20:s10.p1#2 | wrong | flagged |
| The value is stated in the paper [yli18:s8.p24#8]. | yli18:s8.p24#8 | right | passed |
| The value was read from Fig. 3 [yli18:s8.p24#8]. | yli18:s8.p24#8 | wrong | flagged |
| The value was read from Fig. 3 [yim20:fig5b#1]. | yim20:fig5b#1 | right | passed |
| The value was measured by XPS [yim20:fig5b#1]. | yim20:fig5b#1 | wrong | flagged |
| The value was computed by the authors [yim20:s13.p1#1]. | yim20:s13.p1#1 | right | passed |
| The value was computed by this knowledge base [yim20:s13.p1#1]. | yim20:s13.p1#1 | wrong | flagged |
| The value was computed by this knowledge base [yim20:fig7#d1_1]. | yim20:fig7#d1_1 | right | passed |
| The value was computed by the authors [yim20:fig7#d1_1]. | yim20:fig7#d1_1 | wrong | flagged |
| The value is a simulated value [yim20:fig10a#c1]. | yim20:fig10a#c1 | right | passed |
| The value was measured by XPS [yim20:fig10a#c1]. | yim20:fig10a#c1 | wrong | flagged |
| The value is a model input [yim20:s8.p1#5]. | yim20:s8.p1#5 | right | passed |
| The value was measured by XPS [yim20:s8.p1#5]. | yim20:s8.p1#5 | wrong | flagged |
| The value is cited from another work [yim20:s2.p10#2]. | yim20:s2.p10#2 | right | passed |
| The value was measured by XPS [yim20:s2.p10#2]. | yim20:s2.p10#2 | wrong | flagged |
| The value was assumed [yim20:s16.p7#2]. | yim20:s16.p7#2 | right | passed |
| The value was measured by XPS [yim20:s16.p7#2]. | yim20:s16.p7#2 | wrong | flagged |
| The first value is stated in the paper [yli18:s8.p24#15], while the second was measured by XPS [yim20:fig5b#2] | yli18:s8.p24#15 | right | passed |
| The first value is stated in the paper [yli18:s8.p24#15], while the second was measured by XPS [yim20:fig5b#2] | yim20:fig5b#2 | wrong | flagged |
| The first value was read from Fig. 3 [yim20:fig5b#3], while the second was computed by this knowledge base [yi | yim20:fig5b#3 | right | passed |
| The first value was read from Fig. 3 [yim20:fig5b#3], while the second was computed by this knowledge base [yi | yim20:s13.p1#3 | wrong | flagged |
| The first value was computed by the authors [yim20:fig10a#2], while the second was computed by the authors [yi | yim20:fig10a#2 | right | passed |
| The first value was computed by the authors [yim20:fig10a#2], while the second was computed by the authors [yi | yim20:fig7#d2_2 | wrong | flagged |
| The first value was computed by this knowledge base [yim20:fig7#d3_1], while the second was measured by XPS [y | yim20:fig7#d3_1 | right | passed |
| The first value was computed by this knowledge base [yim20:fig7#d3_1], while the second was measured by XPS [y | yim20:fig10a#c5 | wrong | flagged |
| The first value is a simulated value [yim20:fig10b#c1], while the second was measured by XPS [yim20:fig10.cap# | yim20:fig10b#c1 | right | passed |
| The first value is a simulated value [yim20:fig10b#c1], while the second was measured by XPS [yim20:fig10.cap# | yim20:fig10.cap#4 | wrong | flagged |
| The first value is a model input [yim20:fig10.cap#5], while the second was measured by XPS [yim20:tab2.r1c0#1] | yim20:fig10.cap#5 | right | passed |
| The first value is a model input [yim20:fig10.cap#5], while the second was measured by XPS [yim20:tab2.r1c0#1] | yim20:tab2.r1c0#1 | wrong | flagged |
| The first value is cited from another work [yim20:tab2.r1c2#1], while the second was measured by XPS [mat22:s5 | yim20:tab2.r1c2#1 | right | passed |
| The first value is cited from another work [yim20:tab2.r1c2#1], while the second was measured by XPS [mat22:s5 | mat22:s5.p9#3 | wrong | flagged |
| The first value was assumed [mat22:s5.p9#3], while the second was computed by this knowledge base [yim20:s16.p | mat22:s5.p9#3 | right | passed |
| The first value was assumed [mat22:s5.p9#3], while the second was computed by this knowledge base [yim20:s16.p | yim20:s16.p4#3 | wrong | flagged |
| The first value was measured by XPS [yim20:s16.p5#4], while the second was read from Fig. 3 [gao15:s6.p18#1]. | yim20:s16.p5#4 | right | passed |
| The first value was measured by XPS [yim20:s16.p5#4], while the second was read from Fig. 3 [gao15:s6.p18#1]. | gao15:s6.p18#1 | wrong | flagged |
| The first value is stated in the paper [gao15:s6.p18#3], while the second was measured by XPS [yim20:fig8b#2]. | gao15:s6.p18#3 | right | passed |
| The first value is stated in the paper [gao15:s6.p18#3], while the second was measured by XPS [yim20:fig8b#2]. | yim20:fig8b#2 | wrong | flagged |
| The first value was read from Fig. 3 [yim20:fig8b#3], while the second was computed by this knowledge base [yi | yim20:fig8b#3 | right | passed |
| The first value was read from Fig. 3 [yim20:fig8b#3], while the second was computed by this knowledge base [yi | yim20:fig10b#6 | wrong | flagged |
| The first value was computed by the authors [yim20:fig10c#2], while the second was computed by the authors [yi | yim20:fig10c#2 | right | passed |
| The first value was computed by the authors [yim20:fig10c#2], while the second was computed by the authors [yi | yim20:fig9a#d2_1 | wrong | flagged |

Number check, battery-only test (every battery line with numbers, cited by its own id as the given text):

| set | parser | lines | numbers | match | derived | match rate |
|---|---|---|---|---|---|---|
| A (as printed) | v5 | 2695 | 9977 | 9925 | 0 | 99.5 % |
| A (as printed) | v6 | 2695 | 9959 | 9907 | 0 | 99.5 % |
| B (exponents as superscripts) | v5 | 163 | 1280 | 940 | 0 | 73.4 % |
| B (exponents as superscripts) | v6 | 163 | 974 | 965 | 0 | 99.1 % |
