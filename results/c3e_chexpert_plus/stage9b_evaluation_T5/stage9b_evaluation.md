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

Natural context states by study: **N1** 111,040, **N2** 36,011, **N3** 40,622

Interventions apply to the 111,040 N1 studies. Unlike the source
site, where every cohort study was N1 by construction, the natural-state
distribution is informative here.

## Selective Hamming error under the frozen policy

### Target coverage 90%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1913 | 0.1913 | 0.1913 | +0.0000 | +0.0000 |
| M2 | 0.2367 | 0.2604 | 0.2714 | +0.0237 | +0.0347 |
| M3 | 0.1611 | 0.1518 | 0.1708 | -0.0093 | +0.0097 |
| M4 | 0.1147 | 0.1240 | 0.1187 | +0.0093 | +0.0040 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 88.5% | 88.5% | 88.5% |
| M2 | 92.8% | 100.0% | 92.8% |
| M3 | 88.5% | 91.9% | 86.3% |
| M4 | 90.0% | 88.4% | 89.6% |

### Target coverage 80%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1807 | 0.1807 | 0.1807 | +0.0000 | +0.0000 |
| M2 | 0.2299 | 0.2604 | 0.2640 | +0.0305 | +0.0341 |
| M3 | 0.1525 | 0.1437 | 0.1631 | -0.0088 | +0.0106 |
| M4 | 0.1109 | 0.1194 | 0.1146 | +0.0085 | +0.0037 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 77.2% | 77.2% | 77.2% |
| M2 | 85.4% | 100.0% | 85.3% |
| M3 | 77.2% | 82.8% | 73.9% |
| M4 | 79.5% | 76.4% | 78.9% |

### Target coverage 70%

| model | C0 | C1 | C2 | C1 − C0 | C2 − C0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.1680 | 0.1680 | 0.1680 | +0.0000 | +0.0000 |
| M2 | 0.2202 | 0.2604 | 0.2562 | +0.0402 | +0.0360 |
| M3 | 0.1418 | 0.1324 | 0.1511 | -0.0094 | +0.0093 |
| M4 | 0.1062 | 0.1127 | 0.1099 | +0.0064 | +0.0037 |

| model | realised coverage C0 | C1 | C2 |
| --- | ---: | ---: | ---: |
| M1 | 65.7% | 65.7% | 65.7% |
| M2 | 76.8% | 100.0% | 76.8% |
| M3 | 66.5% | 71.9% | 62.8% |
| M4 | 69.7% | 65.5% | 68.9% |

Thresholds and cutoffs are Stage 7 values applied unchanged; none was
selected or revised against external data.

Point estimates only. Intervals and the confirmatory decision belong to
the analysis stage.
