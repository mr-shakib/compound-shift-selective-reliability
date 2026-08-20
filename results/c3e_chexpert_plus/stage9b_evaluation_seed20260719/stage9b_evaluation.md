# C3-E9b — External-Site Evaluation

Status: **PASS**  ·  protocol v0.4.2  ·  labels `impression`

- **STAGE 9b ONLY**
- **EXTERNAL-SITE EVALUATION**
- **THRESHOLDS CONSUMED FROZEN FROM STAGE 7**
- **NO THRESHOLD SELECTED OR REVISED HERE**
- **NO EXTERNAL-SITE TUNING**
- **NO MODEL TRAINING**
- **INFORMATIVENESS RULE TRANSFERRED WITHOUT REFITTING**
- **POINT ESTIMATES ONLY, NO INTERVALS OR TESTS**
- **NO IDENTIFIERS EMITTED TO RESULTS**

## Cohort

191,069 images · 187,672 studies · 64,709 patients (2 excluded as corrupt at source).

Natural context states by study: **N1** 132,922, **N2** 14,129, **N3** 40,622

Interventions apply to the 132,922 N1 studies. Unlike the source
site, where every cohort study was N1 by construction, the natural-state
distribution is informative here.

## Selective Hamming error under the frozen policy

### Target coverage 90%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1619 | 0.1619 | 0.1619 | +0.0000 | +0.0000 |
| M4 | 0.1494 | 0.1617 | 0.1509 | +0.0123 | +0.0015 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 88.4% | 88.4% | 88.4% |
| M4 | 88.4% | 88.5% | 88.0% |

### Target coverage 80%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1464 | 0.1464 | 0.1464 | +0.0000 | +0.0000 |
| M4 | 0.1396 | 0.1501 | 0.1411 | +0.0105 | +0.0015 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 76.5% | 76.5% | 76.5% |
| M4 | 77.4% | 77.8% | 76.7% |

### Target coverage 70%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1270 | 0.1270 | 0.1270 | +0.0000 | +0.0000 |
| M4 | 0.1267 | 0.1343 | 0.1285 | +0.0076 | +0.0018 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 64.3% | 64.3% | 64.3% |
| M4 | 65.6% | 66.3% | 64.8% |

Thresholds and cutoffs are Stage 7 values applied unchanged; none was
selected or revised against external data.

Point estimates only. Intervals and the confirmatory decision belong to
the analysis stage.
