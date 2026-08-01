# C3-E6 Stage 3A — Protocol Compliance Checklist

Overall Stage 3A status: **PASS**

## Declarations

- **STAGE 3A ONLY**
- **METADATA AND REPORT-CONTAINER AUDIT**
- **NO MEDICAL IMAGES OPENED**
- **NO DICOM DECODED**
- **NO REPORT TEXT PARSED OR EXPORTED**
- **NO NLP OR LABEL EXTRACTION**
- **NO CHEXBERT EXECUTION**
- **NO MODEL TRAINING OR INFERENCE**
- **NO THRESHOLD TUNING**
- **NO EXTERNAL DOWNLOADS**
- **NO PROTOCOL MODIFICATION**

## Prohibited-action attestations

| Prohibited action | Performed |
| --- | --- |
| image files opened (DICOM or JPG) | none |
| image directory accessed | no |
| image bytes read | no |
| image feature extraction | no |
| report NLP or tokenisation | no |
| CheXbert executed | no |
| BioClinicalBERT executed | no |
| RadGraph executed | no |
| labels created or extracted | no |
| model initialised, trained, or run for inference | no |
| threshold tuning or optimisation | no |
| AUROC computed | no |
| AUPRC computed | no |
| risk-coverage curves computed | no |
| calibration computed | no |
| selective prediction executed | no |
| cross-site experiments executed | no |
| external validation performed | no |
| model benchmarking performed | no |
| training performed | no |
| external downloads performed | no |
| additional data downloaded | no |
| frozen protocol documents modified | no |
| previous audit outputs modified | no |
| dataset splits or derived datasets built | no |
| leakage introduced | no |
| patient-level rows exported | no |
| identifiers written to Stage 3A artifacts | no |
| git commit, history change, or .gitignore edit | no |

## Scope of data access actually performed

- Read `data/mimic/metadata/SHA256SUMS.txt` as text (digest and filename columns).
- Read the three `cxr-*-list.csv.gz` metadata tables in full.
- Read the report archive central directory (member names, sizes, flags, CRC values).
- members decompressed in memory for CRC-32 and byte-decodability checks only; no tokenisation, parsing, sectioning, labelling, or export of report text.
- The image directory was never listed, opened, or read. Image filenames were
  handled only as strings originating from metadata and the checksum manifest.

## Artifact isolation

- All Stage 3A outputs are written to a new directory: `results/c3e_mimic/stage3a/`.
- No previously produced artifact was modified or overwritten.
- No frozen protocol document under `protocols/` was read for modification or altered.
- No commit was created and git history was not modified.

## Safe-output enforcement

- Every JSON payload was passed through the Stage 3A safe-payload validator,
  which rejects patient-, study-, image-, and report-level fields and values.
- Every emitted file was scanned for restricted row-level patterns and for
  absolute project paths before the run was allowed to succeed.

## Residual scope notes

- View position, study date/time, and image acquisition parameters live in mimic-cxr-2.0.0-metadata.csv.gz, which is absent from this download; any Stage 3B design that stratifies or filters on view cannot be validated yet.
- No official train/validate/test split file (mimic-cxr-2.0.0-split.csv.gz) is present, so split integrity and patient-disjointness remain unverified.
- No CheXpert-style auxiliary label file is present; the frozen primary label source (impression_fixed.json) has no counterpart in this download and remains unverified.
- Report section structure (Findings vs Impression) was deliberately not inspected, so the availability of the frozen pre-diagnostic text fields is not yet established.
- Provider role sparsity is a property of the source data, not a defect; if provider identity is used as a context feature, the missingness pattern must be modelled explicitly rather than imputed.
