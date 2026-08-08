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

10,358 images · 9,293 studies · 4,448 patients.

Interventions apply to the 9,293 N1 studies (10,358 images, 4,448 patients) whose context
passes the frozen informativeness rule. Removing context that was never
there would test nothing.

## Selective Hamming error by condition

Thresholds and abstention cutoffs are Stage 7 values, applied unchanged.

### Target coverage 90%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1293 | 0.1293 | 0.1293 | +0.0000 | +0.0000 |
| M2 | 0.3242 | 0.2291 | 0.3974 | -0.0951 | +0.0732 |
| M3 | 0.1845 | 0.1529 | 0.2107 | -0.0316 | +0.0262 |
| M4 | 0.1508 | 0.1037 | 0.1501 | -0.0470 | -0.0007 |

### Target coverage 80%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1212 | 0.1212 | 0.1212 | +0.0000 | +0.0000 |
| M2 | 0.3255 | 0.2291 | 0.4009 | -0.0965 | +0.0754 |
| M3 | 0.1892 | 0.1535 | 0.2142 | -0.0357 | +0.0250 |
| M4 | 0.1478 | 0.0992 | 0.1471 | -0.0486 | -0.0007 |

### Target coverage 70%

| model | C0 original | C1 no context | C2 misaligned | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1118 | 0.1118 | 0.1118 | +0.0000 | +0.0000 |
| M2 | 0.3325 | 0.2291 | 0.4118 | -0.1035 | +0.0793 |
| M3 | 0.1945 | 0.1536 | 0.2143 | -0.0409 | +0.0198 |
| M4 | 0.1429 | 0.0958 | 0.1431 | -0.0471 | +0.0002 |

## Invariants

- C2 studies retaining their own context: **10**
- M1 maximum prediction drift across conditions: **0.00e+00** (an image-only model must be invariant to a text intervention)
- No forbidden report section entered any payload

Point estimates only. Intervals and hypothesis tests belong to the
confirmatory analysis and are not computed here.
