# C3-E6 Stage 8 — Context Interventions

Status: **PASS**  ·  protocol v0.4.2  ·  tier `prespecified_eval`

- **STAGE 8 ONLY**
- **SOURCE-SITE CONFIRMATORY TIER**
- **THRESHOLDS CONSUMED FROZEN FROM STAGE 7**
- **NO THRESHOLD SELECTED OR REVISED HERE**
- **NO MODEL TRAINING**
- **NO EXTERNAL-SITE INFERENCE**
- **NO CROSS-SITE CLAIM**
- **POINT ESTIMATES ONLY, NO INTERVALS OR TESTS**
- **NO IDENTIFIERS EMITTED TO RESULTS**

## Cohort

16,456 images · 14,766 studies · 5,000 patients.

Interventions apply to the 13,600 N1 studies (15,156 images, 4,632 patients) whose context
passes the frozen informativeness rule. Removing context that was never
there would test nothing.

## Selective Hamming error by condition

Thresholds and abstention cutoffs are Stage 7 values, applied unchanged.

### Target coverage 90%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1176 | 0.1176 | 0.1176 | +0.0000 | +0.0000 |
| M2 | 0.1724 | 0.2502 | 0.2556 | +0.0777 | +0.0832 |
| M3 | 0.1151 | 0.1001 | 0.1509 | -0.0150 | +0.0358 |
| M4 | 0.0825 | 0.0796 | 0.0996 | -0.0029 | +0.0170 |

### Target coverage 80%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1112 | 0.1112 | 0.1112 | +0.0000 | +0.0000 |
| M2 | 0.1638 | 0.2502 | 0.2494 | +0.0864 | +0.0857 |
| M3 | 0.1144 | 0.0974 | 0.1491 | -0.0169 | +0.0348 |
| M4 | 0.0779 | 0.0743 | 0.0947 | -0.0036 | +0.0168 |

### Target coverage 70%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1026 | 0.1026 | 0.1026 | +0.0000 | +0.0000 |
| M2 | 0.1522 | 0.2502 | 0.2431 | +0.0980 | +0.0910 |
| M3 | 0.1103 | 0.0933 | 0.1456 | -0.0171 | +0.0352 |
| M4 | 0.0716 | 0.0702 | 0.0911 | -0.0014 | +0.0195 |

## Invariants

- C2 studies retaining their own context: **1**
- M1 maximum prediction drift across conditions: **0.00e+00** (an image-only model must be invariant to a text intervention)
- No forbidden report section entered any payload

Point estimates only. Intervals and hypothesis tests belong to the
confirmatory analysis and are not computed here.
