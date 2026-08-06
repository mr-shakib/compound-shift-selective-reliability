# C3-E6 Stage 6b — M3 Assembly and Stage 6 Audit

Status: **PASS**  ·  protocol v0.4.2

- **STAGE 6b ONLY**
- **M3 ASSEMBLED FROM TRAINED M1 AND M2, NOT TRAINED**
- **SCORED ON INTERNAL VALIDATION CARVED FROM MODEL TRAIN**
- **NO CALIBRATION-TIER READ**
- **NO PRESPECIFIED-EVAL-TIER READ**
- **NO PREDICTION THRESHOLD SELECTION**
- **NO EXTERNAL-SITE INFERENCE**
- **NO CROSS-SITE CLAIM**
- **DEVELOPMENT NUMBERS, NOT CONFIRMATORY RESULTS**
- **NO IDENTIFIERS EMITTED TO RESULTS**

## Internal validation set

7,919 images from 2,498 patients, carved patient-disjoint from the `model_train` tier.

These are development numbers used for model selection. They are not
confirmatory results and are not comparable to the prespecified evaluation.

## Scores

| model | role | val loss | val macro AUROC |
| --- | --- | ---: | ---: |
| M1 | image-only control | 0.3062 | **0.8774** |
| M2 | text-only / shortcut control | 0.4758 | **0.7629** |
| M3 | probability late fusion (untrained) | 0.3295 | **0.8763** |
| M4 | feature-concatenation fusion | 0.3034 | **0.8885** |

M3 holds 0 trainable parameters by construction; it averages M1 and M2 probabilities.

## Training curves

| model | epoch | train loss | val loss | val macro AUROC |
| --- | ---: | ---: | ---: | ---: |
| M1 | 1 | 0.3302 | 0.3108 | 0.8683 |
| M1 | 2 | 0.2958 | 0.3104 | 0.8772 |
| M1 | 3 | 0.2760 | 0.3062 | 0.8774 |
| M1 | 4 | 0.2512 | 0.3205 | 0.8642 |
| M1 | 5 | 0.2218 | 0.3440 | 0.8644 |
| M1 | 6 | 0.1833 | 0.3797 | 0.8501 |
| M2 | 1 | 0.5407 | 0.5603 | 0.5001 |
| M2 | 2 | 0.5416 | 0.5626 | 0.4999 |
| M2 | 3 | 0.5389 | 0.5590 | 0.5000 |
| M2 | 4 | 0.5382 | 0.5608 | 0.5000 |
| M2 | 5 | 0.2948 | 0.5618 | 0.7287 |
| M2 | 6 | 0.2486 | 0.6286 | 0.7300 |
| M4 | 1 | 0.3214 | 0.3017 | 0.8840 |
| M4 | 2 | 0.2824 | 0.3049 | 0.8881 |
| M4 | 3 | 0.2580 | 0.2809 | 0.8862 |
| M4 | 4 | 0.2293 | 0.3034 | 0.8885 |
| M4 | 5 | 0.1935 | 0.3272 | 0.8701 |
| M4 | 6 | 0.1568 | 0.3750 | 0.8739 |
| M4 | 7 | 0.1233 | 0.4128 | 0.8516 |

## Checkpoints

| model | selected epoch | selection AUROC | bytes | sha256 |
| --- | ---: | ---: | ---: | --- |
| M1 | 3 | 0.8774 | 28,450,961 | `d7e267d2d545f232…` |
| M2 | 3 | 0.7629 | 438,027,565 | `2481adc633dd4543…` |
| M4 | 4 | 0.8885 | 470,134,207 | `ebc5fabee6dc89e8…` |

Checkpoints are restricted data and live in the gitignored tree.
