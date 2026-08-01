# C3-E6 Stage 3B-2 — Context Substantiveness Threshold Sweep

Status: **PASS**

- **STAGE 3B-2 ONLY**
- **CONTEXT AVAILABILITY MEASUREMENT**
- **NO MEDICAL IMAGES OPENED**
- **NO REPORT TEXT EXPORTED**
- **NO LABEL EXTRACTION**
- **NO CHEXBERT EXECUTION**
- **NO MODEL TRAINING OR INFERENCE**
- **NO PREDICTION THRESHOLD SELECTION**
- **NO EVALUATION OR METRIC COMPUTATION**
- **NO EXTERNAL DOWNLOADS**
- **NO PROTOCOL MODIFICATION**

## Purpose

The frozen context registry (C3E6-CONTEXT-001 natural_context_states N1/N2/N3) admits only N1 studies into
the confirmatory C0/C1/C2 interventions. The N1/N2 boundary therefore fixes the
confirmatory sample size. This sweep prices each candidate boundary.

- Reports parsed: 227835
- Threshold definition: effective tokens = whitespace tokens containing at least one alphanumeric character, counted after de-identification placeholder runs are removed.

## State rule

- N3 absent: effective tokens == 0 across the permitted set
- N2 low information: 0 < effective tokens < threshold
- N1 informative: effective tokens >= threshold

## Candidate permitted-context sets

| candidate set | sections | N3 absent | context present | median tokens | note |
| --- | --- | ---: | ---: | ---: | --- |
| indication_only | indication | 61984 (27.21%) | 165851 (72.79%) | 8 | single-section baseline |
| history_only | history | 170830 (74.98%) | 57005 (25.02%) | 0 | single-section baseline |
| indication_history | indication|history | 5096 (2.24%) | 222739 (97.76%) | 10 | two-section set consistent with the registry's 'neither permitted section' wording |
| indication_history_examination | indication|history|examination | 4858 (2.13%) | 222977 (97.87%) | 12 | adds examination type |
| indication_history_comparison | indication|history|comparison | 1715 (0.75%) | 226120 (99.25%) | 12 | adds prior-study reference; comparison may quote prior conclusions |
| all_pre_diagnostic | indication|history|examination|technique|comparison | 1124 (0.49%) | 226711 (99.51%) | 16 | widest pre-diagnostic set; upper bound on availability |

## Threshold curve

N1 is the confirmatory cohort. `N1 + impression` is the cohort that also carries a
primary label source.

| candidate set | threshold | N1 | N1 % | N2 | N3 | N1 + impression | N1 + findings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| indication_only | 1 | 165851 | 72.79% | 0 | 61984 | 144139 | 99067 |
| indication_only | 2 | 164523 | 72.21% | 1328 | 61984 | 142968 | 98124 |
| indication_only | 3 | 162527 | 71.34% | 3324 | 61984 | 141408 | 96560 |
| indication_only | 4 | 159130 | 69.84% | 6721 | 61984 | 139148 | 93658 |
| indication_only | 5 | 153478 | 67.36% | 12373 | 61984 | 134946 | 88462 |
| indication_only | 6 | 145854 | 64.02% | 19997 | 61984 | 128870 | 81421 |
| indication_only | 8 | 124489 | 54.64% | 41362 | 61984 | 110828 | 62974 |
| indication_only | 10 | 100681 | 44.19% | 65170 | 61984 | 89042 | 45057 |
| indication_only | 12 | 80206 | 35.20% | 85645 | 61984 | 69632 | 31855 |
| indication_only | 15 | 56909 | 24.98% | 108942 | 61984 | 47130 | 18887 |
| indication_only | 20 | 33817 | 14.84% | 132034 | 61984 | 24639 | 8014 |
| indication_only | 25 | 22831 | 10.02% | 143020 | 61984 | 13885 | 3656 |
| indication_only | 30 | 16966 | 7.45% | 148885 | 61984 | 8235 | 1962 |
| history_only | 1 | 57005 | 25.02% | 0 | 170830 | 43817 | 46041 |
| history_only | 2 | 53955 | 23.68% | 3050 | 170830 | 41575 | 43065 |
| history_only | 3 | 49563 | 21.75% | 7442 | 170830 | 38741 | 38845 |
| history_only | 4 | 44145 | 19.38% | 12860 | 170830 | 35021 | 33730 |
| history_only | 5 | 39020 | 17.13% | 17985 | 170830 | 31158 | 29243 |
| history_only | 6 | 33217 | 14.58% | 23788 | 170830 | 26909 | 24217 |
| history_only | 8 | 22728 | 9.98% | 34277 | 170830 | 18749 | 15574 |
| history_only | 10 | 14549 | 6.39% | 42456 | 170830 | 12150 | 9422 |
| history_only | 12 | 9084 | 3.99% | 47921 | 170830 | 7542 | 5558 |
| history_only | 15 | 4729 | 2.08% | 52276 | 170830 | 3777 | 2489 |
| history_only | 20 | 2196 | 0.96% | 54809 | 170830 | 1508 | 664 |
| history_only | 25 | 1566 | 0.69% | 55439 | 170830 | 928 | 217 |
| history_only | 30 | 1365 | 0.60% | 55640 | 170830 | 759 | 83 |
| indication_history | 1 | 222739 | 97.76% | 0 | 5096 | 187847 | 145006 |
| indication_history | 2 | 218365 | 95.84% | 4374 | 5096 | 184438 | 141091 |
| indication_history | 3 | 212022 | 93.06% | 10717 | 5096 | 180087 | 135343 |
| indication_history | 4 | 203219 | 89.20% | 19520 | 5096 | 174119 | 127337 |
| indication_history | 5 | 192479 | 84.48% | 30260 | 5096 | 166087 | 117690 |
| indication_history | 6 | 179072 | 78.60% | 43667 | 5096 | 155780 | 105640 |
| indication_history | 8 | 147245 | 64.63% | 75494 | 5096 | 129603 | 78575 |
| indication_history | 10 | 115258 | 50.59% | 107481 | 5096 | 101217 | 54505 |
| indication_history | 12 | 89315 | 39.20% | 133424 | 5096 | 77198 | 37437 |
| indication_history | 15 | 61657 | 27.06% | 161082 | 5096 | 50925 | 21394 |
| indication_history | 20 | 36027 | 15.81% | 186712 | 5096 | 26161 | 8689 |
| indication_history | 25 | 24400 | 10.71% | 198339 | 5096 | 14816 | 3875 |
| indication_history | 30 | 18333 | 8.05% | 204406 | 5096 | 8996 | 2047 |
| indication_history_examination | 1 | 222977 | 97.87% | 0 | 4858 | 188069 | 145227 |
| indication_history_examination | 2 | 219337 | 96.27% | 3640 | 4858 | 185326 | 141989 |
| indication_history_examination | 3 | 213873 | 93.87% | 9104 | 4858 | 181784 | 137058 |
| indication_history_examination | 4 | 206087 | 90.45% | 16890 | 4858 | 176737 | 130014 |
| indication_history_examination | 5 | 197361 | 86.62% | 25616 | 4858 | 170620 | 122333 |
| indication_history_examination | 6 | 187015 | 82.08% | 35962 | 4858 | 163197 | 113320 |
| indication_history_examination | 8 | 163738 | 71.87% | 59239 | 4858 | 145330 | 93125 |
| indication_history_examination | 10 | 139104 | 61.05% | 83873 | 4858 | 124042 | 72153 |
| indication_history_examination | 12 | 115040 | 50.49% | 107937 | 4858 | 101954 | 53330 |
| indication_history_examination | 15 | 82175 | 36.07% | 140802 | 4858 | 70768 | 31446 |
| indication_history_examination | 20 | 47566 | 20.88% | 175411 | 4858 | 37391 | 13079 |
| indication_history_examination | 25 | 29969 | 13.15% | 193008 | 4858 | 20254 | 5681 |
| indication_history_examination | 30 | 21271 | 9.34% | 201706 | 4858 | 11858 | 2828 |
| indication_history_comparison | 1 | 226120 | 99.25% | 0 | 1715 | 188735 | 148262 |
| indication_history_comparison | 2 | 222187 | 97.52% | 3933 | 1715 | 186839 | 144522 |
| indication_history_comparison | 3 | 217273 | 95.36% | 8847 | 1715 | 183987 | 139921 |
| indication_history_comparison | 4 | 210749 | 92.50% | 15371 | 1715 | 180003 | 133903 |
| indication_history_comparison | 5 | 203218 | 89.20% | 22902 | 1715 | 174870 | 127185 |
| indication_history_comparison | 6 | 193129 | 84.77% | 32991 | 1715 | 167953 | 118177 |
| indication_history_comparison | 8 | 168215 | 73.83% | 57905 | 1715 | 148616 | 97113 |
| indication_history_comparison | 10 | 141433 | 62.08% | 84687 | 1715 | 125210 | 76778 |
| indication_history_comparison | 12 | 115904 | 50.87% | 110216 | 1715 | 101709 | 59073 |
| indication_history_comparison | 15 | 83935 | 36.84% | 142185 | 1715 | 71580 | 38345 |
| indication_history_comparison | 20 | 49383 | 21.67% | 176737 | 1715 | 38333 | 17669 |
| indication_history_comparison | 25 | 31465 | 13.81% | 194655 | 1715 | 20856 | 7847 |
| indication_history_comparison | 30 | 22425 | 9.84% | 203695 | 1715 | 12128 | 3695 |
| all_pre_diagnostic | 1 | 226711 | 99.51% | 0 | 1124 | 189136 | 148794 |
| all_pre_diagnostic | 2 | 224036 | 98.33% | 2675 | 1124 | 188449 | 146258 |
| all_pre_diagnostic | 3 | 221101 | 97.04% | 5610 | 1124 | 187487 | 143586 |
| all_pre_diagnostic | 4 | 217281 | 95.37% | 9430 | 1124 | 186082 | 140209 |
| all_pre_diagnostic | 5 | 212638 | 93.33% | 14073 | 1124 | 183715 | 136294 |
| all_pre_diagnostic | 6 | 206473 | 90.62% | 20238 | 1124 | 180497 | 131126 |
| all_pre_diagnostic | 8 | 192333 | 84.42% | 34378 | 1124 | 171583 | 119418 |
| all_pre_diagnostic | 10 | 177246 | 77.80% | 49465 | 1124 | 159530 | 107192 |
| all_pre_diagnostic | 12 | 160755 | 70.56% | 65956 | 1124 | 145009 | 94797 |
| all_pre_diagnostic | 15 | 131339 | 57.65% | 95372 | 1124 | 117663 | 74391 |
| all_pre_diagnostic | 20 | 81870 | 35.93% | 144841 | 1124 | 70110 | 41039 |
| all_pre_diagnostic | 25 | 48967 | 21.49% | 177744 | 1124 | 38008 | 20029 |
| all_pre_diagnostic | 30 | 30807 | 13.52% | 195904 | 1124 | 20330 | 9125 |

## Key findings

- Under the two-section permitted set, raising the substantiveness threshold from 1 to 5 effective tokens moves 30260 studies from N1 to N2 (97.76% -> 84.48% of the corpus).
- At a threshold of 10 effective tokens the confirmatory N1 cohort with an impression label source is 101217 studies (44.43%).
- Every populated context-length bin admits C2 different-patient pairing at corpus level: each has at least two distinct patients and no patient holds half the bin.

## Unresolved risks

- C2 pairing must hold within institution AND split. No official split file is present, so bin feasibility is verified at corpus level only and may fail inside individual splits.
- The N1/N2 threshold is not set by this audit. It is a protocol decision; this sweep supplies the cohort cost of each candidate value.
- Effective token count is a proxy for the registry's 'boilerplate, vague, or clinically insufficient' wording. It detects emptiness and brevity, not vagueness.
- eligible_view is frozen to frontal and view position remains unavailable, so every cohort figure here is an upper bound.
- Admitting comparison into the permitted set raises availability but risks importing prior diagnostic conclusions; the measured gain is reported so the tradeoff can be priced.
