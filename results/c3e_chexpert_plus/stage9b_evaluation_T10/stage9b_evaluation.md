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

Natural context states by study: **N1** 23,146, **N2** 123,905, **N3** 40,622

Interventions apply to the 23,146 N1 studies. Unlike the source
site, where every cohort study was N1 by construction, the natural-state
distribution is informative here.

## Selective Hamming error under the frozen policy

### Target coverage 90%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1895 | 0.1895 | 0.1895 | +0.0000 | +0.0000 |
| M2 | 0.2231 | 0.2610 | 0.2745 | +0.0378 | +0.0514 |
| M3 | 0.1590 | 0.1501 | 0.1785 | -0.0089 | +0.0194 |
| M4 | 0.1159 | 0.1207 | 0.1179 | +0.0048 | +0.0020 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 88.5% | 88.5% | 88.5% |
| M2 | 92.7% | 100.0% | 92.7% |
| M3 | 88.8% | 91.6% | 85.7% |
| M4 | 89.7% | 88.4% | 89.4% |

### Target coverage 80%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1792 | 0.1792 | 0.1792 | +0.0000 | +0.0000 |
| M2 | 0.2171 | 0.2610 | 0.2682 | +0.0439 | +0.0511 |
| M3 | 0.1516 | 0.1432 | 0.1718 | -0.0084 | +0.0202 |
| M4 | 0.1129 | 0.1157 | 0.1138 | +0.0028 | +0.0009 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 77.1% | 77.1% | 77.1% |
| M2 | 85.3% | 100.0% | 85.1% |
| M3 | 77.7% | 82.3% | 73.5% |
| M4 | 79.0% | 76.2% | 78.8% |

### Target coverage 70%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1676 | 0.1676 | 0.1676 | +0.0000 | +0.0000 |
| M2 | 0.2082 | 0.2610 | 0.2595 | +0.0527 | +0.0512 |
| M3 | 0.1412 | 0.1321 | 0.1578 | -0.0091 | +0.0166 |
| M4 | 0.1090 | 0.1083 | 0.1080 | -0.0007 | -0.0010 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 65.8% | 65.8% | 65.8% |
| M2 | 76.5% | 100.0% | 76.3% |
| M3 | 66.7% | 71.2% | 61.9% |
| M4 | 69.1% | 64.6% | 68.8% |

Thresholds and cutoffs are Stage 7 values applied unchanged; none was
selected or revised against external data.

Point estimates only. Intervals and the confirmatory decision belong to
the analysis stage.
