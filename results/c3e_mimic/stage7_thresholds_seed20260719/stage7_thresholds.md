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

10,264 images · 9,233 studies · 3,000 patients.

This tier was read for the first time in this stage. Selection uses it
alone; the prespecified-eval tier remains sealed.

## Per-pathology classification thresholds

Selected by balanced accuracy on study-level mean probabilities.

| model | Cardiomegaly | Edema | Consolidation | Atelectasis | Pleural Effusion |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 0.679 | 0.703 | 0.508 | 0.985 | 0.627 |
| M4 | 0.689 | 0.685 | 0.607 | 0.995 | 0.697 |

## Selective policy

Confidence is |2p − 1| per pathology, minimised across the five, so a
study is only as trustworthy as its least certain finding. Coverage is
held fixed and error allowed to vary, so source and external sites are
compared at the same burden on the human reader.

| model | target coverage | abstention cutoff | realised coverage | selective Hamming | full-coverage Hamming |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 80% | 0.1263 | 80.0% | 0.0983 | 0.1122 |
| M1 | 90% | 0.0581 | 90.0% | 0.1063 | 0.1122 |
| M1 | 70% | 0.2077 | 70.0% | 0.0896 | 0.1122 |
| M4 | 80% | 0.0838 | 80.0% | 0.1101 | 0.1233 |
| M4 | 90% | 0.0406 | 90.0% | 0.1173 | 0.1233 |
| M4 | 70% | 0.1371 | 70.0% | 0.1036 | 0.1233 |

**These thresholds are now frozen.** these thresholds transfer unchanged to the external site; revising them after inspecting external results would answer a different question than the one preregistered.

Selection numbers are development quantities. They are not confirmatory
results and must not be reported as such.
