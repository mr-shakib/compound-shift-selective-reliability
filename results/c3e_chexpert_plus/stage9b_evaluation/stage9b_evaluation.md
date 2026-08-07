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

191,070 images · 187,673 studies · 64,709 patients (1 excluded as corrupt at source).

Natural context states by study: **N1** 132,923, **N2** 14,129, **N3** 40,622

Interventions apply to the 132,923 N1 studies. Unlike the source
site, where every cohort study was N1 by construction, the natural-state
distribution is informative here.

## Selective Hamming error under the frozen policy

### Target coverage 90%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1927 | 0.1927 | 0.1927 | +0.0000 | +0.0000 |
| M2 | 0.2435 | 0.2605 | 0.2761 | +0.0170 | +0.0327 |
| M3 | 0.1656 | 0.1525 | 0.1750 | -0.0131 | +0.0094 |
| M4 | 0.1166 | 0.1246 | 0.1185 | +0.0080 | +0.0019 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 88.4% | 88.4% | 88.4% |
| M2 | 92.8% | 100.0% | 92.7% |
| M3 | 88.6% | 91.9% | 86.8% |
| M4 | 90.0% | 88.4% | 89.4% |

### Target coverage 80%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1818 | 0.1818 | 0.1818 | +0.0000 | +0.0000 |
| M2 | 0.2338 | 0.2605 | 0.2667 | +0.0267 | +0.0329 |
| M3 | 0.1570 | 0.1444 | 0.1676 | -0.0126 | +0.0105 |
| M4 | 0.1128 | 0.1200 | 0.1140 | +0.0072 | +0.0012 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 77.2% | 77.2% | 77.2% |
| M2 | 84.7% | 100.0% | 84.6% |
| M3 | 77.4% | 82.8% | 74.6% |
| M4 | 79.5% | 76.4% | 78.8% |

### Target coverage 70%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1690 | 0.1690 | 0.1690 | +0.0000 | +0.0000 |
| M2 | 0.2236 | 0.2605 | 0.2575 | +0.0369 | +0.0340 |
| M3 | 0.1462 | 0.1328 | 0.1562 | -0.0134 | +0.0100 |
| M4 | 0.1079 | 0.1135 | 0.1086 | +0.0056 | +0.0007 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 65.7% | 65.7% | 65.7% |
| M2 | 75.9% | 100.0% | 75.7% |
| M3 | 66.6% | 71.9% | 63.5% |
| M4 | 69.6% | 65.5% | 68.8% |

Thresholds and cutoffs are Stage 7 values applied unchanged; none was
selected or revised against external data.

Point estimates only. Intervals and the confirmatory decision belong to
the analysis stage.
