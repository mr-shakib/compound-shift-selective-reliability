# C3-E9b — External-Site Evaluation

Status: **PASS**  ·  protocol v0.4.2  ·  labels `findings`

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
| M1 | 0.0569 | 0.0569 | 0.0569 | +0.0000 | +0.0000 |
| M2 | 0.0874 | 0.1493 | 0.1083 | +0.0618 | +0.0209 |
| M3 | 0.0588 | 0.0569 | 0.0657 | -0.0019 | +0.0069 |
| M4 | 0.0408 | 0.0551 | 0.0444 | +0.0144 | +0.0036 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 87.9% | 87.9% | 87.9% |
| M2 | 91.5% | 100.0% | 91.4% |
| M3 | 90.7% | 93.4% | 89.0% |
| M4 | 90.2% | 88.6% | 89.6% |

### Target coverage 80%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.0540 | 0.0540 | 0.0540 | +0.0000 | +0.0000 |
| M2 | 0.0870 | 0.1493 | 0.1059 | +0.0622 | +0.0188 |
| M3 | 0.0568 | 0.0551 | 0.0640 | -0.0017 | +0.0072 |
| M4 | 0.0399 | 0.0538 | 0.0433 | +0.0139 | +0.0035 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 75.9% | 75.9% | 75.9% |
| M2 | 81.3% | 100.0% | 81.2% |
| M3 | 80.5% | 85.4% | 77.8% |
| M4 | 79.6% | 76.6% | 78.9% |

### Target coverage 70%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.0505 | 0.0505 | 0.0505 | +0.0000 | +0.0000 |
| M2 | 0.0861 | 0.1493 | 0.1028 | +0.0632 | +0.0168 |
| M3 | 0.0545 | 0.0531 | 0.0614 | -0.0014 | +0.0068 |
| M4 | 0.0391 | 0.0524 | 0.0425 | +0.0133 | +0.0034 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 63.6% | 63.6% | 63.6% |
| M2 | 71.9% | 100.0% | 71.8% |
| M3 | 71.0% | 76.7% | 68.0% |
| M4 | 69.8% | 65.6% | 69.0% |

Thresholds and cutoffs are Stage 7 values applied unchanged; none was
selected or revised against external data.

Point estimates only. Intervals and the confirmatory decision belong to
the analysis stage.
