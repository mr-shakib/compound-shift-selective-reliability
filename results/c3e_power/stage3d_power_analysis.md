# C3-E6 Stage 3D — Prespecified Power Analysis

Status: **PASS**

- **STAGE 3D ONLY**
- **DESIGN-STAGE POWER ANALYSIS**
- **NO OBSERVED EFFECT USED**
- **NO MEDICAL IMAGES OPENED**
- **NO LABEL EXTRACTION**
- **NO CHEXBERT EXECUTION**
- **NO MODEL TRAINING OR INFERENCE**
- **NO EVALUATION ON REAL OUTCOMES**
- **NO EXTERNAL DOWNLOADS**

## Method

- Decision rule: interval excludes zero AND estimate >= materiality (materiality 0.02)
- Interval: 95_percent_percentile; resampling unit: patient
- Cluster adjustment: design effect with unequal-cluster-size adjustment m_adj = sum(m^2)/sum(m)
- normal approximation for the grid, validated against the frozen bootstrap
- Base rates and effect sizes are **swept over a declared grid, never fitted**. No
  observed effect, label, or model output enters this analysis.

## Cohort structure (Stage 3C cohort, Stage 3E tiers)

| tier | patients | studies | mean studies/patient | max |
| --- | ---: | ---: | ---: | ---: |
| model_train | 49959 | 146253 | 2.9275 | 99 |
| threshold_calibration | 3000 | 9233 | 3.0777 | 102 |
| prespecified_eval | 5000 | 14766 | 2.9532 | 76 |
| official_validate | 448 | 1391 | 3.1049 | 91 |
| official_test | 282 | 1929 | 6.8404 | 64 |

External site: 64725 patients / 187711 studies (counts only, from the frozen CheXpert Plus audit; no external result inspected).

## H1 power at the frozen materiality threshold (coverage 0.80)

Primary tier is the prespecified partition; the official test split is shown alongside
as the secondary comparison it now serves as.

| tier | ICC | base risk | SE | power at effect 0.02 | MDE at 80% power |
| --- | ---: | ---: | ---: | ---: | ---: |
| prespecified_eval | 0.05 | 0.05 | 0.0024 | 50.0% | 0.022 |
| prespecified_eval | 0.05 | 0.1 | 0.0033 | 50.0% | 0.023 |
| prespecified_eval | 0.05 | 0.2 | 0.0044 | 50.0% | 0.024 |
| prespecified_eval | 0.05 | 0.3 | 0.0051 | 50.0% | 0.024 |
| prespecified_eval | 0.15 | 0.05 | 0.0030 | 50.0% | 0.022 |
| prespecified_eval | 0.15 | 0.1 | 0.0041 | 50.0% | 0.023 |
| prespecified_eval | 0.15 | 0.2 | 0.0054 | 50.0% | 0.025 |
| prespecified_eval | 0.15 | 0.3 | 0.0062 | 50.0% | 0.025 |
| prespecified_eval | 0.3 | 0.05 | 0.0036 | 50.0% | 0.023 |
| prespecified_eval | 0.3 | 0.1 | 0.0050 | 50.0% | 0.024 |
| prespecified_eval | 0.3 | 0.2 | 0.0067 | 50.0% | 0.026 |
| prespecified_eval | 0.3 | 0.3 | 0.0076 | 50.0% | 0.026 |
| official_test | 0.05 | 0.05 | 0.0071 | 50.0% | 0.026 |
| official_test | 0.05 | 0.1 | 0.0098 | 50.0% | 0.028 |
| official_test | 0.05 | 0.2 | 0.0131 | 33.4% | 0.037 |
| official_test | 0.05 | 0.3 | 0.0150 | 26.7% | 0.042 |
| official_test | 0.15 | 0.05 | 0.0095 | 50.0% | 0.028 |
| official_test | 0.15 | 0.1 | 0.0130 | 33.5% | 0.036 |
| official_test | 0.15 | 0.2 | 0.0174 | 20.9% | 0.049 |
| official_test | 0.15 | 0.3 | 0.0199 | 17.0% | 0.056 |
| official_test | 0.3 | 0.05 | 0.0122 | 37.5% | 0.034 |
| official_test | 0.3 | 0.1 | 0.0168 | 22.2% | 0.047 |
| official_test | 0.3 | 0.2 | 0.0223 | 14.3% | 0.063 |
| official_test | 0.3 | 0.3 | 0.0256 | 11.9% | 0.072 |

## Bootstrap validation of the approximation

| coverage | ICC | base risk | effect | empirical power | analytic power | gap |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.8 | 0.05 | 0.1 | 0.02 | 0.485 | 0.500 | 0.015 |
| 0.8 | 0.15 | 0.1 | 0.05 | 1.000 | 1.000 | 0.000 |
| 0.8 | 0.15 | 0.2 | 0.1 | 1.000 | 1.000 | 0.000 |
| 0.8 | 0.3 | 0.2 | 0.05 | 1.000 | 1.000 | 0.000 |

## Key findings

- On the prespecified evaluation partition (5000 patients), the H1 minimum detectable effect at 80% power ranges from 0.022 to 0.026, i.e. 1.1x-1.3x the materiality threshold. On the official test split (282 patients) the same range is 0.026-0.072, or 1.3x-3.6x materiality. The partition cuts the worst-case MDE by a factor of 2.7, which is what makes H1 a viable confirmatory test rather than an underpowered one. Note the MDE can never fall below materiality itself: when the materiality constraint binds, MDE = materiality + 0.84*SE > materiality by construction.
- At the frozen materiality threshold of 0.02, H1 power on the prespecified partition ranges from 50.0% to 50.0% across the assumption grid.
- STRUCTURAL CEILING: the decision rule requires the point estimate itself to reach the materiality threshold. When the true effect equals materiality exactly, the estimate exceeds it in only half of all repetitions, so power is capped at 50% NO MATTER HOW LARGE THE SAMPLE. Verified to hold at implied n of order 1e9. The 50% cells in the grid below are therefore the rule's ceiling, not a MIMIC cohort limitation. It follows that materiality must be read as the smallest effect worth acting on, and the study must be powered against a larger design effect - the MDE column - rather than against the materiality threshold itself.
- The minimum detectable effect at 80% power for H1 ranges from 0.022 to 0.026 absolute selective risk, i.e. 1.1x to 1.3x the materiality threshold the protocol declares material.
- H2 is better placed because the within-site context contrast is paired: at high pairing correlation the interaction standard error falls substantially, so the compound-shift hypothesis is the more salvageable of the two confirmatory tests.
- Normal-approximation power agreed with the frozen patient-level percentile bootstrap to within 0.015 across 4 validation cells, so the grid above is not an artefact of the approximation.

## Options (no option chosen here)

1. ADOPTED in protocol v0.3.0: re-partition MIMIC with a larger, patient-disjoint evaluation partition carved from train, retaining the official splits as secondary confirmation. Chosen because it fixes power without redefining what counts as a material effect.
2. ADOPTED in protocol v0.3.0: clarify that materiality is the smallest effect worth acting on, not the design effect, and power the study against the MDE instead. This removes the 50% ceiling from the design without changing the decision rule itself.
3. RETAINED as a fallback: report any hypothesis whose MDE still exceeds the achievable range as estimation with an interval rather than as a powered decision.
4. REJECTED: raising the materiality threshold to the measured MDE. This would fit the definition of a material effect to the design, which is the move a reviewer is most likely to read as motivated.
5. NOT NEEDED: the primary loss is already `five_label_hamming_error`, so the primary estimand does not pay the Holm multiplicity penalty; only per-pathology secondaries do.
6. REJECTED: swapping site roles so the larger cohort carries the confirmatory test. This contradicts `datasets.external.role: locked_external_evaluation_only`.

Selecting among these is a protocol decision. Whichever is chosen must be recorded
**before** any label, model, or metric exists, otherwise it becomes a post-hoc change
under `governance.post_target_inspection_changes_label`.
