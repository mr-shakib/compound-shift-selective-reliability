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

Interventions apply to the 14,766 N1 studies (16,456 images, 5,000 patients) whose context
passes the frozen informativeness rule. Removing context that was never
there would test nothing.

## Selective Hamming error by condition

Thresholds and abstention cutoffs are Stage 7 values, applied unchanged.

### Target coverage 90%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1145 | 0.1145 | 0.1145 | +0.0000 | +0.0000 |
| M2 | 0.1657 | 0.2411 | 0.2476 | +0.0754 | +0.0819 |
| M3 | 0.1108 | 0.0974 | 0.1440 | -0.0133 | +0.0332 |
| M4 | 0.0792 | 0.0767 | 0.0951 | -0.0024 | +0.0159 |

### Target coverage 80%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1084 | 0.1084 | 0.1084 | +0.0000 | +0.0000 |
| M2 | 0.1575 | 0.2411 | 0.2415 | +0.0836 | +0.0840 |
| M3 | 0.1102 | 0.0951 | 0.1426 | -0.0151 | +0.0324 |
| M4 | 0.0744 | 0.0720 | 0.0893 | -0.0024 | +0.0149 |

### Target coverage 70%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1000 | 0.1000 | 0.1000 | +0.0000 | +0.0000 |
| M2 | 0.1467 | 0.2411 | 0.2347 | +0.0944 | +0.0880 |
| M3 | 0.1068 | 0.0915 | 0.1414 | -0.0154 | +0.0346 |
| M4 | 0.0688 | 0.0677 | 0.0855 | -0.0010 | +0.0168 |

## Invariants

- C2 studies retaining their own context: **6**
- M1 maximum prediction drift across conditions: **0.00e+00** (an image-only model must be invariant to a text intervention)
- No forbidden report section entered any payload

Point estimates only. Intervals and hypothesis tests belong to the
confirmatory analysis and are not computed here.
