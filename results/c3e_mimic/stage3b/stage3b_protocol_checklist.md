# C3-E6 Stage 3B — Protocol Compliance Checklist

Overall Stage 3B status: **PASS**

## Declarations

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

## Prohibited-action attestations

| Prohibited action | Performed |
| --- | --- |
| image files opened (DICOM or JPG) | none |
| image directory accessed | no |
| image feature extraction | no |
| CheXbert executed | no |
| BioClinicalBERT executed | no |
| RadGraph executed | no |
| labels created or extracted from report text | no |
| model initialised, trained, or run for inference | no |
| threshold selection or tuning | no |
| AUROC / AUPRC / calibration / risk-coverage computed | no |
| evaluation or metric computation on real data | no |
| selective prediction executed | no |
| cross-site experiment executed | no |
| dataset or split construction | no |
| report text written to any artifact | no |
| section content written to any artifact | no |
| patient-level or study-level rows exported | no |
| identifiers written to Stage 3B artifacts | no |
| external downloads | no |
| frozen protocol documents modified | no |
| previous audit outputs modified | no |
| git commit, history change, or .gitignore edit | no |

## Authorised scope actually exercised

- Parsed all report members of `mimic-cxr-reports.zip` for section structure.
- Measured section presence, repetition, ordering, body size, and de-identification density.
- Read `cxr-study-list.csv.gz` to confirm the parsed report count.
- Report text was held in memory only for measurement and discarded immediately.

## Text-handling attestation

- No section body, sentence, phrase, or token from any report was written to an artifact.
- Section names come from a curated, hard-coded vocabulary in the audit module.
- Unrecognised header labels are digit-masked and suppressed below a frequency
  threshold of 100 occurrences.
- All JSON payloads passed the safe-payload validator, and every emitted file was
  scanned for restricted row-level patterns and absolute project paths.

## Artifact isolation

- All Stage 3B outputs are written to a new directory: `results/c3e_mimic/stage3b/`.
- Stage 3A artifacts under `results/c3e_mimic/stage3a/` were not read for modification
  or altered, and no frozen protocol document was changed.
- No commit was created and git history was not modified.

## Residual scope notes

- eligible_view is frozen to 'frontal', but view position is still unavailable: it lives in mimic-cxr-2.0.0-metadata.csv.gz, which remains absent. View filtering cannot be applied yet.
- No official split file is present, so patient-disjoint split construction remains unverified.
- Section boundaries are derived from a curated header vocabulary. Reports without recognised headers, and reports merging findings with impression, are not contract-recoverable and must be excluded or handled explicitly by an approved Stage 3C rule.
- COMPARISON bodies are treated as pre-diagnostic because prior-study references precede interpretation, but they can quote prior diagnostic conclusions; if COMPARISON is admitted into context_text this must be justified in a protocol amendment.
- No label was extracted and no CheXbert-equivalent was executed, so the MIMIC analogue of impression_fixed.json / findings_fixed.json still does not exist.
