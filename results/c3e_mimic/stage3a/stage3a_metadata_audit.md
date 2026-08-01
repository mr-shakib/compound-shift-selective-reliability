# C3-E6 Stage 3A — MIMIC Metadata and Report Intake Audit

Status: **PASS**

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

## Check summary

- Checks executed: 73
- PASS: 70  WARN: 3  FAIL: 0

## 1. Checksum verification

- `cxr-record-list.csv.gz`: PASS (14871705 bytes)
- `cxr-study-list.csv.gz`: PASS (2343957 bytes)
- `cxr-provider-list.csv.gz`: PASS (1843629 bytes)
- `mimic-cxr-reports.zip`: PASS (141942511 bytes)

- Manifest entries: 604950
- Manifest entries by extension: {'dcm': 377110, 'gz': 3, 'txt': 227836, 'zip': 1}
- Note: SHA256SUMS.txt is the full MIMIC-CXR manifest and also lists DICOM filenames and digests. Image digests were used for name-level reconciliation only; no image bytes were read.

## 2. Schema audit

### `cxr-record-list`

- Rows: 377110, columns: 4
- Columns: ['subject_id', 'study_id', 'dicom_id', 'path']
- Unexpected columns: none
- Missing columns: none
- Null cells: 0; duplicate rows: 0
- Primary key: ['dicom_id'] (valid: True)
- Candidate keys: [['dicom_id'], ['path']]
- Foreign keys: [{'columns': ['subject_id', 'study_id'], 'references': 'cxr-study-list'}]

### `cxr-study-list`

- Rows: 227835, columns: 3
- Columns: ['subject_id', 'study_id', 'path']
- Unexpected columns: none
- Missing columns: none
- Null cells: 0; duplicate rows: 0
- Primary key: ['study_id'] (valid: True)
- Candidate keys: [['study_id'], ['path'], ['subject_id', 'study_id']]
- Foreign keys: none

### `cxr-provider-list`

- Rows: 227835, columns: 4
- Columns: ['study_id', 'ordering_provider_id', 'attending_provider_id', 'resident_provider_id']
- Unexpected columns: none
- Missing columns: none
- Null cells: 145148; duplicate rows: 0
- Primary key: ['study_id'] (valid: True)
- Candidate keys: [['study_id']]
- Foreign keys: [{'columns': ['study_id'], 'references': 'cxr-study-list'}]

## 3. Hierarchy validation

- Patients: 65379
- Studies: 227835
- Records: 377110
- Orphan records (no parent study): 0
- Studies with no child record: 0
- Study identifiers mapped to >1 patient: 0
- Duplicate record identifiers: 0
- Duplicate study identifiers: 0
- Broken references: 0
- Path/identifier agreement: all checks pass

## 4. Provider audit

- Rows: 227835
- Studies covered: 227835
- Distinct providers (any role): 2893
- Duplicate study rows: 0
- Rows referencing unknown study: 0
- Studies without a provider row: 0
- Rows with all roles null: 0

- `ordering_provider_id`: coverage 99.8429%, 2755 distinct, 358 null
- `attending_provider_id`: coverage 100.0000%, 55 distinct, 0 null
- `resident_provider_id`: coverage 36.4496%, 115 distinct, 144790 null

## 5. Study audit

- Rows: 227835
- Distinct studies: 227835
- Distinct patients: 65379
- Duplicate studies: 0
- Duplicate (patient, study) pairs: 0
- Duplicate report paths: 0
- Missing identifiers: 0

## 6. Record audit

- Rows: 377110
- Distinct record identifiers: 377110
- Distinct studies: 227835
- Distinct patients: 65379
- Duplicate rows: 0
- Duplicate record identifiers: 0
- Missing identifiers: 0
- DICOM references not ending in .dcm: 0
- `view_position` column present: False
- View-position audit status: NOT_AUDITABLE_IN_THIS_DOWNLOAD

DICOM references were validated as filename strings only. No DICOM file was opened.

## 7. Report archive audit

- Archive entries: 293234
- Report members: 227835
- Directory members: 65399
- Layout: files/<2-char patient bucket>/<patient dir>/<study>.txt
- Filename convention: files/pXX/pNNNNNNNN/sNNNNNNNN.txt
- Patient identifier encoding: directory name, 'p' prefix + 8-digit subject_id; bucket = first 2 digits
- Study identifier encoding: file stem, 's' prefix + 8-digit study_id
- Members matching convention: 227835
- Non-.txt members: 0
- Duplicate member names: 0
- Reports missing vs study-list: 0
- Reports unexpected vs study-list: 0
- CRC-32 mismatches: 0
- Read errors: 0
- Zero-length members: 0
- Members undecodable as UTF-8: 0
- Members pure ASCII: 227831
- Members valid UTF-8 but non-ASCII: 4
- Non-ASCII member names: 0
- Empty patient directories: 9
- Patient directories absent from metadata: 9

Content handling: members decompressed in memory for CRC-32 and byte-decodability checks only; no tokenisation, parsing, sectioning, labelling, or export of report text.

## 8. Cross-table integrity

- PASS — cxr-record-list -> cxr-study-list on (patient, study) (many-to-one); unmatched: 0
- PASS — cxr-provider-list -> cxr-study-list on study (one-to-one); unmatched: 0
- PASS — cxr-study-list -> cxr-provider-list on study (one-to-one); unmatched: 0
- PASS — cxr-study-list -> report archive on path (one-to-one); unmatched: 0
- PASS — report archive -> cxr-study-list on path (one-to-one); unmatched: 0
- PASS — cxr-study-list -> SHA256SUMS .txt entries (one-to-one); unmatched: 0
- PASS — SHA256SUMS .txt entries -> cxr-study-list (one-to-one); unmatched: 0
- PASS — cxr-record-list -> SHA256SUMS .dcm entries (one-to-one); unmatched: 0
- PASS — SHA256SUMS .dcm entries -> cxr-record-list (one-to-one); unmatched: 0
- PASS — report archive -> SHA256SUMS .txt entries (one-to-one); unmatched: 0

- Three-way agreement (study-list = archive members = manifest .txt): True
- Record-list agrees with manifest .dcm entries: True

## Anomalies

- 9 patient directories in the report archive contain no report members and correspond to no row in any metadata table (packaging residue, inert)
- 4 report members contain valid UTF-8 non-ASCII bytes; all members decode cleanly, but Stage 3B text handling must not assume pure ASCII
- cxr-record-list carries no view_position column, so the requested view-position audit could not be executed from this download
- resident_provider_id is populated for only 36.45% of studies
- ordering_provider_id is null for 358 studies (0.1571% of rows)

## Unresolved risks

- View position, study date/time, and image acquisition parameters live in mimic-cxr-2.0.0-metadata.csv.gz, which is absent from this download; any Stage 3B design that stratifies or filters on view cannot be validated yet.
- No official train/validate/test split file (mimic-cxr-2.0.0-split.csv.gz) is present, so split integrity and patient-disjointness remain unverified.
- No CheXpert-style auxiliary label file is present; the frozen primary label source (impression_fixed.json) has no counterpart in this download and remains unverified.
- Report section structure (Findings vs Impression) was deliberately not inspected, so the availability of the frozen pre-diagnostic text fields is not yet established.
- Provider role sparsity is a property of the source data, not a defect; if provider identity is used as a context feature, the missingness pattern must be modelled explicitly rather than imputed.

## Blocking failures

- None
