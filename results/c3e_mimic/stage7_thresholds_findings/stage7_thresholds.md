# C3-E6 Stage 7 — Threshold Selection

Status: **PASS**  ·  protocol v0.4.2

- **STAGE 7 ONLY**
- **THRESHOLD SELECTION ON THE CALIBRATION TIER**
- **NO MODEL TRAINING**
- **NO PRESPECIFIED-EVAL-TIER READ**
- **NO EXTERNAL-SITE INFERENCE**
- **NO CROSS-SITE CLAIM**
- **THRESHOLDS FROZEN FOR TRANSFER**
- **SELECTION NUMBERS ARE NOT CONFIRMATORY RESULTS**
- **NO IDENTIFIERS EMITTED TO RESULTS**

## Calibration tier

6,381 images · 5,733 studies · 2,669 patients.

This tier was read for the first time in this stage. Selection uses it
alone; the prespecified-eval tier remains sealed.

## Per-pathology classification thresholds

Selected by balanced accuracy on study-level mean probabilities.

| model | Cardiomegaly | Edema | Consolidation | Atelectasis | Pleural Effusion |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.787 | 0.458 | 0.296 | 0.980 | 0.764 |
| M2 | 0.932 | 0.783 | 0.519 | 0.966 | 0.944 |
| M3 | 0.694 | 0.656 | 0.438 | 0.988 | 0.691 |
| M4 | 0.881 | 0.530 | 0.232 | 0.956 | 0.948 |

## Selective policy

Confidence is |2p − 1| per pathology, minimised across the five, so a
study is only as trustworthy as its least certain finding. Coverage is
held fixed and error allowed to vary, so source and external sites are
compared at the same burden on the human reader.

| model | target coverage | abstention cutoff | realised coverage | selective Hamming | full-coverage Hamming |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 80% | 0.1321 | 80.0% | 0.1150 | 0.1304 |
| M1 | 90% | 0.0626 | 90.0% | 0.1250 | 0.1304 |
| M1 | 70% | 0.2143 | 70.0% | 0.1051 | 0.1304 |
| M2 | 80% | 0.1004 | 80.0% | 0.3262 | 0.3158 |
| M2 | 90% | 0.0464 | 90.0% | 0.3223 | 0.3158 |
| M2 | 70% | 0.1577 | 70.0% | 0.3315 | 0.3158 |
| M3 | 80% | 0.0261 | 80.0% | 0.1855 | 0.1786 |
| M3 | 90% | 0.0114 | 90.0% | 0.1804 | 0.1786 |
| M3 | 70% | 0.0431 | 70.0% | 0.1902 | 0.1786 |
| M4 | 80% | 0.1188 | 80.0% | 0.1455 | 0.1523 |
| M4 | 90% | 0.0551 | 90.0% | 0.1493 | 0.1523 |
| M4 | 70% | 0.1829 | 70.0% | 0.1428 | 0.1523 |

**These thresholds are now frozen.** these thresholds transfer unchanged to the external site; revising them after inspecting external results would answer a different question than the one preregistered.

Selection numbers are development quantities. They are not confirmatory
results and must not be reported as such.
