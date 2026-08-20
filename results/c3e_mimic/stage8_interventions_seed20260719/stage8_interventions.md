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
| M1 | 0.1031 | 0.1031 | 0.1031 | +0.0000 | +0.0000 |
| M4 | 0.1206 | 0.1266 | 0.1284 | +0.0059 | +0.0078 |

### Target coverage 80%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.0953 | 0.0953 | 0.0953 | +0.0000 | +0.0000 |
| M4 | 0.1150 | 0.1166 | 0.1226 | +0.0016 | +0.0077 |

### Target coverage 70%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.0829 | 0.0829 | 0.0829 | +0.0000 | +0.0000 |
| M4 | 0.1071 | 0.1075 | 0.1139 | +0.0004 | +0.0068 |

## Invariants

- C2 studies retaining their own context: **6**
- M1 maximum prediction drift across conditions: **0.00e+00** (an image-only model must be invariant to a text intervention)
- No forbidden report section entered any payload

Point estimates only. Intervals and hypothesis tests belong to the
confirmatory analysis and are not computed here.
