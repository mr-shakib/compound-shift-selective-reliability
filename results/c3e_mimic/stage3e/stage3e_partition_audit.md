# C3-E6 Stage 3E — Prespecified Patient-Disjoint Evaluation Partition

Status: **PASS**

- **STAGE 3E ONLY**
- **DESIGN-STAGE PARTITION CONSTRUCTION**
- **PARTITION DEPENDS ONLY ON PATIENT IDENTIFIERS AND A FROZEN SEED**
- **NO LABEL, OUTCOME, OR MODEL OUTPUT USED**
- **NO MEDICAL IMAGES OPENED**
- **NO CHEXBERT EXECUTION**
- **NO MODEL TRAINING OR INFERENCE**
- **NO IDENTIFIERS IN SAFE OUTPUTS**

## Partition policy

- Unit: patient; seed: 20260718 (frozen)
- Carved from: `train` split of the Stage 3C cohort
- Depends on: patient identifiers and frozen seed only
- Official splits: secondary confirmation

## Tiers

| tier | role | patients | studies | frontal images | est. GB |
| --- | --- | ---: | ---: | ---: | ---: |
| model_train | model fitting | 49959 | 146253 | 162823 | 240.1 |
| threshold_calibration | frozen threshold selection | 3000 | 9233 | 10264 | 15.14 |
| prespecified_eval | primary confirmatory evaluation | 5000 | 14766 | 16456 | 24.27 |
| official_validate | secondary confirmation (official split) | 448 | 1391 | 1584 | 2.34 |
| official_test | secondary confirmation (official split) | 282 | 1929 | 2155 | 3.18 |

All tiers patient-disjoint: **True**

## Image download budget options

Fixed tiers (eval, calibration, official validate/test) are always required. Only the
training tier is variable.

| train patient budget | train patients | train studies | train images | total images | est. total GB |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5000 | 5000 | 14635 | 16326 | 46785 | 68.99 |
| 10000 | 10000 | 29164 | 32481 | 62940 | 92.81 |
| 20000 | 20000 | 58289 | 64928 | 95387 | 140.66 |
| 40000 | 40000 | 117015 | 130161 | 160620 | 236.85 |
| all | 49959 | 146253 | 162823 | 193282 | 285.02 |

Size estimate assumes 1.51 MB per image — **verify against a sample before committing**.

## Download manifests

path manifests contain patient and study identifiers and are written to the gitignored restricted-data tree, never to results/.

| tier | path | images |
| --- | --- | ---: |
| model_train | `data/mimic/download_manifests/model_train_frontal_jpg_paths.txt` | 162823 |
| threshold_calibration | `data/mimic/download_manifests/threshold_calibration_frontal_jpg_paths.txt` | 10264 |
| prespecified_eval | `data/mimic/download_manifests/prespecified_eval_frontal_jpg_paths.txt` | 16456 |
| official_validate | `data/mimic/download_manifests/official_validate_frontal_jpg_paths.txt` | 1584 |
| official_test | `data/mimic/download_manifests/official_test_frontal_jpg_paths.txt` | 2155 |

## Key findings

- The prespecified evaluation partition carries 5000 patients and 14766 studies, against 282 patients and 1929 studies in the official test split.
- Standard errors scale as 1/sqrt(patients), so the partition shrinks the confirmatory standard error by approximately 4.2x relative to the official test split.
- Assignment used only patient identifiers and the frozen seed. No label, outcome, image, or model output entered the partitioning, so this is a design construction rather than a data-dependent selection.
- All 5 tiers are patient-disjoint.
- Official validate and test splits are untouched and retained for secondary confirmation, so comparability with published MIMIC baselines is preserved as a reported secondary result.

## Unresolved risks

- Using a non-official evaluation partition amends `official_splits_required: true`. The official splits are retained as secondary confirmation, but the primary confirmatory estimate will not be directly comparable to published official-split baselines.
- The image-size estimate of 1.51 MB per image is derived from the published release size divided by image count. Verify against a small sample before committing to a download budget.
- A reduced training budget yields weaker models. The study measures whether selective reliability transports, not peak accuracy, so this is a stated limitation rather than a defect - but it must be prespecified, not chosen after seeing results.
- Partition sizes were chosen for statistical adequacy and download tractability before any outcome existed. They must not be revised after any label or model output is generated.
