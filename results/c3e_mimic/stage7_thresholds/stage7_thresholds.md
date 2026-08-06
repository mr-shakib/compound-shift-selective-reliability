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
| M1 | 0.713 | 0.520 | 0.405 | 0.988 | 0.766 |
| M2 | 0.611 | 0.586 | 0.692 | 0.994 | 0.648 |
| M3 | 0.617 | 0.575 | 0.553 | 0.986 | 0.686 |
| M4 | 0.633 | 0.436 | 0.584 | 0.964 | 0.798 |

## Selective policy

Confidence is |2p − 1| per pathology, minimised across the five, so a
study is only as trustworthy as its least certain finding. Coverage is
held fixed and error allowed to vary, so source and external sites are
compared at the same burden on the human reader.

| model | target coverage | abstention cutoff | realised coverage | selective Hamming | full-coverage Hamming |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1 | 80% | 0.1246 | 80.0% | 0.1087 | 0.1223 |
| M1 | 90% | 0.0596 | 90.0% | 0.1167 | 0.1223 |
| M1 | 70% | 0.1997 | 70.0% | 0.0996 | 0.1223 |
| M2 | 80% | 0.0807 | 80.0% | 0.1605 | 0.1764 |
| M2 | 90% | 0.0388 | 90.0% | 0.1682 | 0.1764 |
| M2 | 70% | 0.1321 | 70.0% | 0.1494 | 0.1764 |
| M3 | 80% | 0.0312 | 80.0% | 0.1122 | 0.1128 |
| M3 | 90% | 0.0141 | 90.0% | 0.1132 | 0.1128 |
| M3 | 70% | 0.0528 | 70.0% | 0.1090 | 0.1128 |
| M4 | 80% | 0.1197 | 80.0% | 0.0756 | 0.0819 |
| M4 | 90% | 0.0564 | 90.0% | 0.0787 | 0.0819 |
| M4 | 70% | 0.1839 | 70.0% | 0.0711 | 0.0819 |

**These thresholds are now frozen.** these thresholds transfer unchanged to the external site; revising them after inspecting external results would answer a different question than the one preregistered.

Selection numbers are development quantities. They are not confirmatory
results and must not be reported as such.
