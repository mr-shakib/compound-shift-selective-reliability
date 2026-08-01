# C3-E6 Stage 3B — Report Structure and Section Availability Audit

Status: **PASS**

- **STAGE 3B ONLY**
- **REPORT STRUCTURE AND SECTION STATISTICS**
- **NO MEDICAL IMAGES OPENED**
- **NO DICOM OR JPG DECODED**
- **NO REPORT TEXT EXPORTED**
- **NO LABEL EXTRACTION**
- **NO CHEXBERT EXECUTION**
- **NO MODEL TRAINING OR INFERENCE**
- **NO THRESHOLD SELECTION**
- **NO EVALUATION OR METRIC COMPUTATION**
- **NO EXTERNAL DOWNLOADS**
- **NO PROTOCOL MODIFICATION**

## Corpus

- Reports parsed: 227835
- Reports expected from `cxr-study-list`: 227835
- Count matches study list: True
- Reports with no header-shaped line at all: 59
- Reports with no recognised section: 66
- Leading banner distribution: {'FINAL REPORT': 226992, 'FINAL ADDENDUM': 843}

## Section coverage

| section | class | reports | coverage | median body tokens | empty bodies | repeated |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| addendum | post_diagnostic | 182 | 0.0799% | 24 | 3 | 2 |
| administrative | administrative | 158 | 0.0693% | 1 | 0 | 1 |
| comment | post_diagnostic | 196 | 0.0860% | 19 | 0 | 1 |
| comparison | pre_diagnostic | 163853 | 71.9174% | 2 | 73 | 46 |
| examination | pre_diagnostic | 102460 | 44.9711% | 3 | 24 | 152 |
| findings | label_source | 149738 | 65.7221% | 45 | 109 | 77 |
| findings_impression_combined | label_source | 134 | 0.0588% | 43 | 1 | 0 |
| history | pre_diagnostic | 57019 | 25.0264% | 6 | 6 | 19 |
| impression | label_source | 189444 | 83.1496% | 17 | 30 | 134 |
| indication | pre_diagnostic | 165862 | 72.7992% | 13 | 4 | 28 |
| notification | post_diagnostic | 5755 | 2.5260% | 24 | 26 | 0 |
| provisional_impression | post_diagnostic | 199 | 0.0873% | 17 | 0 | 37 |
| recommendation | post_diagnostic | 1810 | 0.7944% | 13 | 7 | 1 |
| technique | pre_diagnostic | 81365 | 35.7122% | 4 | 7 | 16 |
| wet_read | post_diagnostic | 17551 | 7.7034% | 33 | 1 | 0 |

## Frozen-contract availability

- Pre-diagnostic context present: 227288 (99.7599%)
- Impression label source present: 189577 (83.2080%)
- Findings label source present: 149871 (65.7805%)
- **Usable for primary analysis** (context + impression): 189326 (83.0979%)
- **Usable for sensitivity analysis** (context + findings): 149484 (65.6106%)

### Availability combinations

| combination | reports |
| --- | ---: |
| pre_diagnostic=0;impression=0;findings=0 | 15 |
| pre_diagnostic=0;impression=0;findings=1 | 215 |
| pre_diagnostic=0;impression=1;findings=0 | 79 |
| pre_diagnostic=0;impression=1;findings=1 | 172 |
| pre_diagnostic=1;impression=0;findings=0 | 11281 |
| pre_diagnostic=1;impression=0;findings=1 | 26681 |
| pre_diagnostic=1;impression=1;findings=0 | 66523 |
| pre_diagnostic=1;impression=1;findings=1 | 122803 |

## Section ordering

- Reports placing pre-diagnostic text after the first label section: 181 (0.0794%)
- Interpretation: a non-zero count means section order alone is not a safe extraction rule; extraction must be header-driven, not position-driven.

## Unrecognised headers

- Total occurrences: 14197
- Distinct masked labels: 499
- View-descriptor occurrences: 13571
- Occurrences suppressed below threshold (100): 2296
- labels below the threshold are counted but never printed, and digit runs are masked, so no rare free-text fragment can reach an artifact.

| masked label | occurrences | view descriptor |
| --- | ---: | --- |
| AP CHEST, # | 4369 | True |
| CHEST, TWO VIEWS | 1735 | True |
| PA AND LATERAL VIEWS OF THE CHEST | 913 | True |
| AP CHEST # | 801 | True |
| FRONTAL AND LATERAL CHEST RADIOGRAPHS | 603 | True |
| PA AND LATERAL CHEST RADIOGRAPHS | 528 | True |
| PORTABLE CHEST | 485 | True |
| PA AND LATERAL CHEST RADIOGRAPH | 393 | True |
| CHEST, PA AND LATERAL | 327 | True |
| TWO VIEWS OF THE CHEST | 321 | True |
| FRONTAL AND LATERAL VIEWS OF THE CHEST | 320 | True |
| PORTABLE AP CHEST RADIOGRAPH | 240 | True |
| FRONTAL CHEST RADIOGRAPH | 236 | True |
| CHEST | 207 | False |
| PORTABLE FRONTAL CHEST RADIOGRAPH | 173 | True |
| CHEST RADIOGRAPH | 137 | False |
| CHEST, AP | 113 | True |

## Anomalies

- 66 reports (0.0290%) expose no recognised section header; their narrative cannot be split into pre-diagnostic and diagnostic parts
- 181 reports place a pre-diagnostic section AFTER the first label-source section; a naive split-at-FINDINGS extractor would mis-assign that text
- 17551 reports carry a WET READ preliminary interpretation (7.7034%); this is post-diagnostic text and must be excluded from context_text
- 134 reports merge findings and impression into a single section, so the frozen primary/sensitivity label-source separation is not recoverable for them
- 6 reports have an indication section whose body is de-identification placeholders only, yielding empty effective context_text
- 13571 header-shaped lines are view descriptors in old-style reports rather than named sections

## Unresolved risks

- eligible_view is frozen to 'frontal', but view position is still unavailable: it lives in mimic-cxr-2.0.0-metadata.csv.gz, which remains absent. View filtering cannot be applied yet.
- No official split file is present, so patient-disjoint split construction remains unverified.
- Section boundaries are derived from a curated header vocabulary. Reports without recognised headers, and reports merging findings with impression, are not contract-recoverable and must be excluded or handled explicitly by an approved Stage 3C rule.
- COMPARISON bodies are treated as pre-diagnostic because prior-study references precede interpretation, but they can quote prior diagnostic conclusions; if COMPARISON is admitted into context_text this must be justified in a protocol amendment.
- No label was extracted and no CheXbert-equivalent was executed, so the MIMIC analogue of impression_fixed.json / findings_fixed.json still does not exist.
