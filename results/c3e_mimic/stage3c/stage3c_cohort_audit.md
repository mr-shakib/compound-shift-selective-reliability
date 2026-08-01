# C3-E6 Stage 3C — Source-Site Cohort Construction Audit

Status: **PASS**

- **STAGE 3C ONLY**
- **COHORT COUNTING AND ELIGIBILITY AUDIT**
- **NO MEDICAL IMAGES OPENED**
- **NO DICOM OR JPG DECODED**
- **NO REPORT TEXT EXPORTED**
- **NO LABEL EXTRACTION**
- **NO CHEXBERT EXECUTION**
- **NO MODEL TRAINING OR INFERENCE**
- **NO PREDICTION THRESHOLD SELECTION**
- **NO EVALUATION OR METRIC COMPUTATION**
- **NO DATASET FILE WRITTEN**
- **NO EXTERNAL DOWNLOADS**

## Applied policy

- Eligible view: frontal (PA, AP) (frozen)
- Permitted context sections: ['indication', 'history'] (approved mapping)
- Informativeness threshold: T = 3 primary, [5, 10] sensitivity
- Primary label section: impression; sensitivity: findings
- Policy source: `docs/C3E6_SOURCE_TEXT_MAPPING_AND_INFORMATIVENESS_RULE.md (approved)`

## Input integrity

- image metadata rows: 377110
- split rows: 377110
- record rows: 377110
- metadata dicom set matches record list: True
- split dicom set matches record list: True
- metadata duplicate dicom: 0
- split duplicate dicom: 0
- official checksum manifest available: False
- metadata identifiers agree: True
- split identifiers agree: True

## Split integrity

- Studies spanning splits: 0
- Patients spanning splits: 0
- Frozen preflight check `no_patient_overlap_across_source_splits`: **PASS**
- Split image counts: {'train': 368960, 'test': 5159, 'validate': 2991}

## View distribution

| view position | images | fraction | frontal |
| --- | ---: | ---: | --- |
| AP | 147173 | 39.0265% | True |
| PA | 96161 | 25.4995% | True |
| LATERAL | 82853 | 21.9705% | False |
| LL | 35133 | 9.3164% | False |
| <missing> | 15769 | 4.1815% | False |
| PA LLD | 4 | 0.0011% | False |
| LAO | 3 | 0.0008% | False |
| RAO | 3 | 0.0008% | False |
| AP AXIAL | 2 | 0.0005% | False |
| AP LLD | 2 | 0.0005% | False |
| XTABLE LATERAL | 2 | 0.0005% | False |
| AP RLD | 2 | 0.0005% | False |
| SWIMMERS | 1 | 0.0003% | False |
| PA RLD | 1 | 0.0003% | False |
| LPO | 1 | 0.0003% | False |

Frontal images: 243334. Images with no view label: 15769.

## Exclusion waterfall

| step | rule | before | removed | after | remaining |
| --- | --- | ---: | ---: | ---: | ---: |
| all_studies | every study in cxr-study-list | 227835 | 0 | 227835 | 100.0000% |
| recognised_structure | exclude reports with no recognised section header (approved exclusion rule) | 227835 | 66 | 227769 | 99.9710% |
| separable_label_sections | exclude reports merging findings and impression (approved exclusion rule) | 227769 | 133 | 227636 | 99.9127% |
| frontal_view_available | frozen eligible_view=frontal: study must have at least one PA/AP image | 227636 | 9688 | 217948 | 95.6605% |
| official_split_assigned | frozen official_splits_required=true | 217948 | 0 | 217948 | 95.6605% |
| context_informative_T3 | approved informativeness rule: N1 requires >= 3 effective tokens across indication+history | 217948 | 15001 | 202947 | 89.0763% |
| primary_label_source_present | study must carry an impression section to receive a primary label | 202947 | 29375 | 173572 | 76.1832% |

## Confirmatory cohort

- Studies: 173572
- Patients: 58689
- Frontal images: 193282

| split | studies | patients | frontal images | with findings label | studies @T5 | studies @T10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 170252 | 57959 | 189543 | 108622 | 156915 | 95186 |
| validate | 1391 | 448 | 1584 | 844 | 1291 | 801 |
| test | 1929 | 282 | 2155 | 1256 | 1732 | 998 |

## Unresolved risks

- The official test split yields 1929 studies from 282 patients. The frozen statistical_cluster_unit is patient and failure_criteria require a CI excluding zero at a minimum absolute risk increase of 0.02; with 282 clusters this is a materially power-limited confirmatory test.
- The validate split yields 1391 studies from 448 patients, which constrains calibration and any coverage-stratified diagnostic performed off the training split.
- The MIMIC-CXR-JPG SHA256SUMS manifest was not downloaded, so the two new files could not be checksum-verified against the official source. They were instead cross-validated against the checksum-verified cxr-record-list; identifier sets and per-row identifiers agree exactly.
- 15769 images carry no ViewPosition and are therefore treated as non-frontal. This is a conservative reading of the frozen eligible_view rule; studies whose only images lack a view label are excluded rather than assumed frontal.
