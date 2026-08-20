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

Interventions apply to the 8,381 N1 studies (9,378 images, 3,005 patients) whose context
passes the frozen informativeness rule. Removing context that was never
there would test nothing.

## Selective Hamming error by condition

Thresholds and abstention cutoffs are Stage 7 values, applied unchanged.

### Target coverage 90%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1311 | 0.1311 | 0.1311 | +0.0000 | +0.0000 |
| M2 | 0.2072 | 0.2942 | 0.3118 | +0.0871 | +0.1046 |
| M3 | 0.1328 | 0.1144 | 0.1750 | -0.0183 | +0.0422 |
| M4 | 0.0964 | 0.0942 | 0.1121 | -0.0022 | +0.0157 |

### Target coverage 80%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1233 | 0.1233 | 0.1233 | +0.0000 | +0.0000 |
| M2 | 0.1968 | 0.2942 | 0.3067 | +0.0974 | +0.1098 |
| M3 | 0.1295 | 0.1110 | 0.1716 | -0.0185 | +0.0421 |
| M4 | 0.0898 | 0.0868 | 0.1067 | -0.0029 | +0.0170 |

### Target coverage 70%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1143 | 0.1143 | 0.1143 | +0.0000 | +0.0000 |
| M2 | 0.1841 | 0.2942 | 0.2970 | +0.1101 | +0.1129 |
| M3 | 0.1222 | 0.1045 | 0.1701 | -0.0177 | +0.0478 |
| M4 | 0.0830 | 0.0818 | 0.1002 | -0.0012 | +0.0172 |

## Invariants

- C2 studies retaining their own context: **0**
- M1 maximum prediction drift across conditions: **0.00e+00** (an image-only model must be invariant to a text intervention)
- No forbidden report section entered any payload

Point estimates only. Intervals and hypothesis tests belong to the
confirmatory analysis and are not computed here.
